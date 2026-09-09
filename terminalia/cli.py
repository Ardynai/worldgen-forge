"""Terminalia CLI — python -m terminalia <command>."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from .schema import World, WorldSpec, Terrain, Region, HistoryEntry
from .terrain import build_terrain


def cmd_generate(args: argparse.Namespace) -> None:
    world_dir = args.out or f"worlds/{args.name}"
    os.makedirs(world_dir, exist_ok=True)
    out = os.path.join(world_dir, "out")

    # 1. spec (agent normally writes this; CLI takes a minimal one)
    spec = WorldSpec(prompt=args.prompt, seed=args.seed,
                     size_hectares=args.size)
    world = World(spec=spec)

    # 2. terrain — default island program; agent can author richer ones
    ops = [
        {"op": "voronoi", "n": 4, "key": "region"},
        {"op": "radial_mask", "key": "center", "cx": 512, "cy": 512,
         "radius": 380},
        {"op": "fbm"},
        {"op": "mountains", "mask": "region0", "height_m": 180.0},
        {"op": "raise", "mask": "center", "height_m": 30.0},
        {"op": "river", "start": [100, 200], "end": [900, 800], "width": 10},
        {"op": "coast", "sea_level_m": 8.0},
        {"op": "normalize", "min_m": 0.0, "max_m": 220.0},
    ]
    grid = build_terrain(ops, size=args.resolution,
                         meters_per_pixel=args.mpp, seed=args.seed)
    hm_path = grid.save_heightmap(os.path.join(out, "terrain", "hm.png"))

    import numpy as np
    regions = []
    region_names = ["highlands", "lowlands", "coast", "wilds"]
    rng = np.random.default_rng(args.seed + 1)
    pts = rng.random((len(region_names), 2)) * args.resolution
    ys, xs = np.mgrid[0:args.resolution, 0:args.resolution]
    d = np.stack([((xs - px) ** 2 + (ys - py) ** 2) for px, py in pts])
    labels = d.argmin(axis=0)
    for i, rname in enumerate(region_names):
        m = (labels == i).astype(np.float32)
        p = os.path.join(out, "terrain", f"mask_{rname}.png")
        grid.save_mask(m, p)
        regions.append(Region(name=rname, mask=p, biome=rname))

    world.terrain = Terrain(
        heightmap=hm_path, regions=regions, operators=[o["op"] for o in ops],
        meters_per_pixel=args.mpp, min_height_m=0.0, max_height_m=220.0)
    world.history.append(HistoryEntry(
        stage="terrain", at=datetime.now(timezone.utc).isoformat(),
        notes=f"{len(ops)} operators, {args.resolution}px"))

    world_path = os.path.join(world_dir, "world.json")
    world.save(world_path)
    print(f"world scaffolded: {world_path}")
    print(f"  heightmap: {hm_path}")
    print("next stages (layout/assets/place) run via the agent skills")


def cmd_validate(args: argparse.Namespace) -> None:
    w = World.load(args.world)
    print(f"OK: {args.world} — {len(w.layout.objects)} objects, "
          f"{len(w.assets)} assets, {len(w.history)} history entries")


def cmd_export_web(args: argparse.Namespace) -> None:
    from .web_export import SplatExportError, export_splat_web_bundle
    try:
        world = World.load(args.world)
        output = export_splat_web_bundle(os.path.dirname(os.path.abspath(args.world)), world.model_dump())
    except SplatExportError as error:
        print(error.code, file=sys.stderr)
        raise SystemExit(1) from error
    except OSError:
        print("SPLAT_WORLD_UNAVAILABLE", file=sys.stderr)
        raise SystemExit(1)
    except ValueError:
        print("SPLAT_WORLD_INVALID", file=sys.stderr)
        raise SystemExit(1)
    print(output)


def main() -> None:
    ap = argparse.ArgumentParser(prog="terminalia")
    sub = ap.add_subparsers(required=True)

    g = sub.add_parser("generate")
    g.add_argument("--prompt", required=True)
    g.add_argument("--name", default=None)
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--size", type=float, default=100.0, help="hectares")
    g.add_argument("--resolution", type=int, default=1024)
    g.add_argument("--mpp", type=float, default=2.0, help="meters per pixel")
    g.add_argument("--out", default=None)
    g.set_defaults(func=cmd_generate)

    v = sub.add_parser("validate")
    v.add_argument("world")
    v.set_defaults(func=cmd_validate)

    export = sub.add_parser("export-web", help="Export the world's validated splat as a data-only web bundle")
    export.add_argument("world")
    export.set_defaults(func=cmd_export_web)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

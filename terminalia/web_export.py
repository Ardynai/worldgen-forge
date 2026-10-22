"""Bounded data-only splat export. No viewer code, network, or generation stage."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct

from pydantic import ValidationError

from .schema import World

MAX_SPLATS = 500_000
RECORD_BYTES = 32


class SplatExportError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _inside(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.root or path.is_absolute() or ":" in relative or "\\" in relative or ".." in path.parts:
        raise SplatExportError("SPLAT_PATH_INVALID")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise SplatExportError("SPLAT_PATH_OUTSIDE_WORLD")
    return resolved


def _bounds(data: bytes) -> dict:
    if not data or len(data) % RECORD_BYTES:
        raise SplatExportError("SPLAT_RECORDS_INVALID")
    minimum = [math.inf] * 3
    maximum = [-math.inf] * 3
    for record in struct.iter_unpack("<6f8B", data):
        if not all(math.isfinite(value) for value in record[:6]):
            raise SplatExportError("SPLAT_NUMBER_INVALID")
        if any(abs(value) > 10_000 for value in record[:3]):
            raise SplatExportError("SPLAT_POSITION_OUT_OF_RANGE")
        if any(value <= 0 or value > 1000 for value in record[3:6]):
            raise SplatExportError("SPLAT_SCALE_INVALID")
        if all(value == 128 for value in record[10:14]):
            raise SplatExportError("SPLAT_ROTATION_INVALID")
        for axis, value in enumerate(record[:3]):
            minimum[axis] = min(minimum[axis], value)
            maximum[axis] = max(maximum[axis], value)
    return {"min": minimum, "max": maximum}


def export_splat_web_bundle(world_dir: str, world: dict) -> str:
    """Export world.json's splat descriptor to export/web; never overwrite a bundle."""
    try:
        model = World.model_validate(world)
    except ValidationError as error:
        raise SplatExportError("SPLAT_WORLD_INVALID") from error
    if model.splat is None:
        raise SplatExportError("SPLAT_SOURCE_REQUIRED")
    if abs(model.spec.seed) > 9_007_199_254_740_991:
        raise SplatExportError("SPLAT_SEED_OUT_OF_RANGE")
    root = Path(world_dir).resolve()
    source = _inside(root, model.splat.file)
    if source.suffix.lower() != ".splat":
        raise SplatExportError("SPLAT_FORMAT_UNSUPPORTED")
    try:
        with source.open("rb") as stream:
            data = stream.read(MAX_SPLATS * RECORD_BYTES + 1)
    except OSError as error:
        raise SplatExportError("SPLAT_SOURCE_UNAVAILABLE") from error
    if len(data) > MAX_SPLATS * RECORD_BYTES:
        raise SplatExportError("SPLAT_SIZE_LIMIT")
    digest = hashlib.sha256(data).hexdigest()
    if digest != model.splat.sha256:
        raise SplatExportError("SPLAT_SOURCE_CHANGED")
    bounds = _bounds(data)
    manifest = {
        "format": "multiverse.splat.web",
        "version": 1,
        "title": model.spec.prompt[:120],
        "seed": model.spec.seed,
        "units": "meters",
        "upAxis": model.splat.up_axis,
        "asset": {
            "file": "scene.splat",
            "sha256": digest,
            "bytes": len(data),
            "pointCount": len(data) // RECORD_BYTES,
            "bounds": bounds,
            "license": model.splat.license,
            "attribution": model.splat.attribution,
        },
    }
    parent = _inside(root, "export")
    output = _inside(root, "export/web")
    try:
        parent.mkdir(exist_ok=True)
        output.mkdir()  # Exclusive creation; retain any previous/partial export for inspection.
    except FileExistsError as error:
        raise SplatExportError("SPLAT_EXPORT_EXISTS") from error
    except OSError as error:
        raise SplatExportError("SPLAT_EXPORT_UNAVAILABLE") from error
    try:
        with (output / "scene.splat").open("xb") as stream:
            stream.write(data)
        # Write the manifest last; consumers must verify its length and hash before rendering.
        with (output / "manifest.json").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
    except OSError as error:
        raise SplatExportError("SPLAT_EXPORT_WRITE_FAILED") from error
    return str(output)

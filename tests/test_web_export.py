import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

import pytest

from terminalia.schema import World
from terminalia.web_export import SplatExportError, export_splat_web_bundle


def record(position=(1, 2, 3), scale=(1, 1, 1), rotation=(255, 128, 128, 128)):
    return struct.pack("<6f8B", *position, *scale, 255, 0, 0, 255, *rotation)


def source(root, data=None):
    root.mkdir(exist_ok=True)
    data = record() if data is None else data
    (root / "input.splat").write_bytes(data)
    return {"spec": {"prompt": "Test scene", "seed": 42}, "splat": {
        "file": "input.splat", "sha256": hashlib.sha256(data).hexdigest(),
        "license": "UNLICENSED", "attribution": "Synthetic test author", "up_axis": "Y",
    }}


def test_deterministic_bundle_and_world_roundtrip(tmp_path):
    bundles = []
    data = record() + record((-2, 5, 0))
    for name in ("first", "second"):
        root = tmp_path / name
        world = source(root, data)
        World.model_validate(world).save(str(root / "world.json"))
        loaded = World.load(str(root / "world.json")).model_dump()
        output = Path(export_splat_web_bundle(str(root), loaded))
        assert sorted(p.name for p in output.iterdir()) == ["manifest.json", "scene.splat"]
        assert (root / "input.splat").read_bytes() == data
        assert (output / "scene.splat").read_bytes() == data
        bundles.append((output / "manifest.json").read_bytes())
    assert bundles[0] == bundles[1]
    manifest = json.loads(bundles[0])
    assert manifest["format"] == "multiverse.splat.web"
    assert manifest["asset"]["bounds"] == {"min": [-2, 2, 0], "max": [1, 5, 3]}
    assert manifest["asset"]["pointCount"] == 2
    assert manifest["asset"]["bytes"] == 64
    assert manifest["asset"]["sha256"] == hashlib.sha256(data).hexdigest()
    assert b"input.splat" not in bundles[0]
    assert b"history" not in bundles[0]
    assert str(tmp_path).encode() not in bundles[0]


@pytest.mark.parametrize("data,code", [
    (b"", "SPLAT_RECORDS_INVALID"),
    (record()[:-1], "SPLAT_RECORDS_INVALID"),
    (record((float("nan"), 0, 0)), "SPLAT_NUMBER_INVALID"),
    (record(scale=(float("inf"), 1, 1)), "SPLAT_NUMBER_INVALID"),
    (record((10001, 0, 0)), "SPLAT_POSITION_OUT_OF_RANGE"),
    (record(scale=(0, 1, 1)), "SPLAT_SCALE_INVALID"),
    (record(scale=(1001, 1, 1)), "SPLAT_SCALE_INVALID"),
    (record(rotation=(128, 128, 128, 128)), "SPLAT_ROTATION_INVALID"),
    (b"x" * 16_000_001, "SPLAT_SIZE_LIMIT"),
], ids=["empty", "truncated", "nan", "infinite", "position", "zero-scale", "large-scale", "rotation", "oversized"])
def test_invalid_binary_fails_before_output(tmp_path, data, code):
    world = source(tmp_path, data)
    with pytest.raises(SplatExportError, match=f"^{code}$"):
        export_splat_web_bundle(str(tmp_path), world)
    assert not (tmp_path / "export").exists()


@pytest.mark.parametrize("path", ["../outside.splat", "/outside.splat", "C:/outside.splat", "a\\b.splat"])
def test_rejects_nonlocal_paths(tmp_path, path):
    world = source(tmp_path)
    world["splat"]["file"] = path
    with pytest.raises(SplatExportError, match="^SPLAT_PATH_INVALID$"):
        export_splat_web_bundle(str(tmp_path), world)


def test_missing_changed_and_unsupported_sources(tmp_path):
    world = source(tmp_path)
    (tmp_path / "input.splat").write_bytes(record((2, 3, 4)))
    with pytest.raises(SplatExportError, match="^SPLAT_SOURCE_CHANGED$"):
        export_splat_web_bundle(str(tmp_path), world)
    world["splat"]["file"] = "missing.splat"
    with pytest.raises(SplatExportError, match="^SPLAT_SOURCE_UNAVAILABLE$"):
        export_splat_web_bundle(str(tmp_path), world)
    world["splat"]["file"] = "scene.ply"
    with pytest.raises(SplatExportError, match="^SPLAT_FORMAT_UNSUPPORTED$"):
        export_splat_web_bundle(str(tmp_path), world)


def test_missing_descriptor_and_unknown_fields(tmp_path):
    world = source(tmp_path)
    world["splat"]["url"] = "https://example.invalid/scene.splat"
    with pytest.raises(SplatExportError, match="^SPLAT_WORLD_INVALID$"):
        export_splat_web_bundle(str(tmp_path), world)
    world.pop("splat")
    with pytest.raises(SplatExportError, match="^SPLAT_SOURCE_REQUIRED$"):
        export_splat_web_bundle(str(tmp_path), world)


def test_existing_bundle_is_preserved(tmp_path):
    world = source(tmp_path)
    output = Path(export_splat_web_bundle(str(tmp_path), world))
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(SplatExportError, match="^SPLAT_EXPORT_EXISTS$"):
        export_splat_web_bundle(str(tmp_path), world)
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


def test_write_failure_leaves_no_manifest(tmp_path, monkeypatch):
    world = source(tmp_path)
    original = Path.open
    def fail_scene(path, mode="r", *args, **kwargs):
        if path.name == "scene.splat" and mode == "xb":
            raise OSError("Injected disk failure")
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail_scene)
    with pytest.raises(SplatExportError, match="^SPLAT_EXPORT_WRITE_FAILED$"):
        export_splat_web_bundle(str(tmp_path), world)
    assert (tmp_path / "export/web").is_dir()
    assert not (tmp_path / "export/web/manifest.json").exists()


def test_cli_success_and_named_failures(tmp_path):
    world = source(tmp_path)
    path = tmp_path / "world.json"
    path.write_text(json.dumps(world), encoding="utf-8")
    def run():
        return subprocess.run([sys.executable, "-m", "terminalia", "export-web", str(path)],
                              capture_output=True, text=True, timeout=15)
    result = run()
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).joinpath("manifest.json").is_file()
    result = run()
    assert result.returncode == 1
    assert result.stderr.strip() == "SPLAT_EXPORT_EXISTS"
    path.write_text("{", encoding="utf-8")
    assert run().stderr.strip() == "SPLAT_WORLD_INVALID"
    path.unlink()
    assert run().stderr.strip() == "SPLAT_WORLD_UNAVAILABLE"

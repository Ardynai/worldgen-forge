import hashlib
import json
import shutil
import subprocess

import pytest

from custom_nodes.terminalia_fixanything import TerminaliaFixAnything
from custom_nodes.terminalia_fixanything.constants import FIX_ANYTHING_WEIGHTS as NODE_WEIGHTS
from terminalia.backends import Backend, GPU_PROFILES
from terminalia.refine import FIX_ANYTHING_WEIGHTS, _output_artifacts, can_run_fix_anything


pytestmark = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="mock smoke test requires ffmpeg and ffprobe",
)


def _sample_video(path):
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
        "testsrc2=size=96x64:rate=8:duration=1", "-frames:v", "8",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-threads", "1", str(path),
    ], check=True)


def _frame_hashes(path, directory):
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
        "-vsync", "0", str(directory / "%03d.png"),
    ], check=True)
    return [hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob("*.png"))]


def test_mock_node_transforms_video_deterministically_and_matches_history_contract(tmp_path, monkeypatch):
    source = tmp_path / "input.mp4"
    output_root = tmp_path / "output"
    first_frames = tmp_path / "first"
    second_frames = tmp_path / "second"
    first_frames.mkdir()
    second_frames.mkdir()
    _sample_video(source)
    monkeypatch.setenv("TERMINALIA_COMFY_OUTPUT", str(output_root))
    monkeypatch.setenv("TERMINALIA_FIXANYTHING_MOCK", "1")
    inputs = {
        "artifacts": [{"uri": source.as_uri(), "kind": "video"}],
        "seed": 41,
        "base_weights": FIX_ANYTHING_WEIGHTS["base"],
        "lora_weights": FIX_ANYTHING_WEIGHTS["lora"],
        "clean_frame_indices": [0, 7],
    }

    first = TerminaliaFixAnything().execute(**inputs)
    entry = first["ui"]["videos"][0]
    output = output_root / entry["subfolder"] / entry["filename"]
    assert output.is_file()
    first_bytes = output.read_bytes()
    first_hashes = _frame_hashes(output, first_frames)

    second = TerminaliaFixAnything().execute(**inputs)
    assert output.read_bytes() == first_bytes
    assert _frame_hashes(output, second_frames) == first_hashes
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=nb_read_frames", "-of", "json", str(output),
    ], check=True, capture_output=True, text=True)
    assert int(json.loads(probe.stdout)["streams"][0]["nb_read_frames"]) == 8

    backend = Backend("local-comfy", "https://compute.example")
    artifacts = _output_artifacts(backend, {"fix_anything": second["ui"]})
    assert artifacts[0].kind == "video"
    assert "subfolder=terminalia" in artifacts[0].uri


def test_node_weights_and_refine_gating_remain_in_sync():
    assert NODE_WEIGHTS == FIX_ANYTHING_WEIGHTS
    assert not can_run_fix_anything(
        Backend("local-comfy", "http://localhost"), GPU_PROFILES["rtx-4090-24gb"])
    assert can_run_fix_anything(
        Backend("local-comfy", "http://localhost"), GPU_PROFILES["rtx-5090-32gb"])
    assert can_run_fix_anything(
        Backend("comfy-cloud", "https://cloud.comfy.org"), GPU_PROFILES["rtx-3060-12gb"])

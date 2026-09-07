"""Offline proof that fixture execution cannot be mistaken for working models."""
import builtins
import hashlib
import json

import pytest

from custom_nodes.terminalia_reconstruct.nodes import (
    NODE_DISPLAY_NAME_MAPPINGS as RECONSTRUCT_NAMES,
    TerminaliaReconstructInstances, reconstruct_instances,
)
from custom_nodes.terminalia_segment.nodes import (
    NODE_DISPLAY_NAME_MAPPINGS as SEGMENT_NAMES,
    TerminaliaSegmentVideo, segment_video,
)
from terminalia import safety
from terminalia.backends import GPU_PROFILES
from terminalia.ingest import UnsafeVideoError, ingest_video
from terminalia.reconstruction import BackendImplementationMissing
from terminalia.schema import ModelRef


def inputs(tmp_path):
    return dict(video_path="unused.mp4", source_sha256="a" * 64, seed=42,
                output_dir=str(tmp_path), sam2_revision="sam-revision")


def reconstruct(tmp_path, tracks="not even parsed in real mode"):
    return reconstruct_instances(
        **inputs(tmp_path), tracks=tracks, mesh_preset="test", mesh_steps=[1],
        trellis2_model="unused", trellis2_revision="trellis-revision",
        foundationpose_version="foundationpose-version")


@pytest.mark.parametrize("configured", [False, True])
@pytest.mark.parametrize("stage", ["segment", "reconstruct"])
def test_real_nodes_fail_typed_before_imports_keys_or_effects(tmp_path, monkeypatch,
                                                           configured, stage):
    monkeypatch.delenv("TERMINALIA_RECONSTRUCT_MOCK", raising=False)
    for key in ("NGC_API_KEY", "FOUNDATIONPOSE_NGC_DIR"):
        if configured:
            monkeypatch.setenv(key, "synthetic-not-a-credential")
        else:
            monkeypatch.delenv(key, raising=False)
    original_import = builtins.__import__

    def no_model_import(name, *args, **kwargs):
        assert name.split(".")[0] not in {"torch", "trimesh", "sam2", "huggingface_hub"}
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_model_import)
    with pytest.raises(BackendImplementationMissing) as error:
        if stage == "segment":
            segment_video(**inputs(tmp_path), sam2_model="unused")
        else:
            reconstruct(tmp_path)
    assert isinstance(error.value, NotImplementedError)
    assert error.value.code == "backend_implementation_missing"
    assert "mock-only" in str(error.value)
    assert "cannot enable it" in str(error.value)
    assert error.value.stage
    assert not list(tmp_path.iterdir())


def test_discovery_and_deterministic_mock_output_are_honest(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMINALIA_RECONSTRUCT_MOCK", "1")
    tracks = segment_video(**inputs(tmp_path), sam2_model="unused")
    assert tracks["execution_mode"] == "mock"
    first = reconstruct(tmp_path, tracks)
    first_meshes = [path.read_bytes() for path in sorted(tmp_path.rglob("*.glb"))]
    assert first_meshes and all(data[:4] == b"glTF" for data in first_meshes)
    assert reconstruct(tmp_path, tracks) == first
    assert [path.read_bytes() for path in sorted(tmp_path.rglob("*.glb"))] == first_meshes
    assert first["execution_mode"] == "mock"
    assert first["models"] == [{"name": "Terminalia reconstruction mock", "version": "1",
                                "license": "test-only; no model executed"}]
    assert ModelRef.model_validate(first["models"][0]).model_dump() == first["models"][0]
    for node in (TerminaliaSegmentVideo, TerminaliaReconstructInstances):
        assert "not implemented" in node.DESCRIPTION
    assert all("mock only" in name for name in [*SEGMENT_NAMES.values(), *RECONSTRUCT_NAMES.values()])


@pytest.mark.parametrize("case", ["safe", "unsafe", "hash-mismatch", "decode-error"])
def test_all_safety_mock_results_have_nonreal_provenance(tmp_path, monkeypatch, case):
    path = tmp_path / "source.mp4"
    path.write_bytes(b"fixture")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setenv("TERMINALIA_SAFETY_MOCK", "1")
    monkeypatch.setenv("TERMINALIA_SAFETY_MOCK_RESULT", case)
    monkeypatch.setattr(safety, "_frames", lambda _: [] if case == "decode-error" else [b"frame"])
    monkeypatch.setattr(safety, "_post", lambda *args: pytest.fail("mock called provider"))
    verdict = safety.check_video(path, "0" * 64 if case == "hash-mismatch" else digest)
    assert verdict.safe is (case == "safe")
    assert verdict.model["name"] == "Terminalia safety mock"
    assert safety.has_real_provenance(verdict.model) is False
    assert json.loads(json.dumps(verdict.model_dump()))["model"] == verdict.model


class ResultBackend:
    def __init__(self, *results):
        self.results = iter(results)
        self.jobs = []

    def submit(self, workflow, client_id):
        self.jobs.append(workflow)
        return str(len(self.jobs))

    def wait(self, prompt_id):
        return {"terminalia_result": next(self.results)}


def test_safe_mock_cannot_open_ingestion_gate(tmp_path, monkeypatch):
    path = tmp_path / "source.mp4"
    path.write_bytes(b"fixture")
    monkeypatch.setenv("TERMINALIA_SAFETY_MOCK", "1")
    monkeypatch.setenv("TERMINALIA_SAFETY_MOCK_RESULT", "safe")
    monkeypatch.setattr(safety, "_frames", lambda _: [b"frame"])
    verdict = safety.check_video(path, hashlib.sha256(path.read_bytes()).hexdigest())
    backend = ResultBackend(verdict.model_dump())
    with pytest.raises(UnsafeVideoError, match="provenance"):
        ingest_video(dict(video_path=str(path), consent_note="test consent"), backend,
                     GPU_PROFILES["rtx-3060-12gb"])
    assert len(backend.jobs) == 1


def test_mock_scene_cannot_produce_ingested_world(tmp_path, monkeypatch):
    path = tmp_path / "source.mp4"
    path.write_bytes(b"fixture")
    monkeypatch.setenv("TERMINALIA_SAFETY_MOCK", "1")
    monkeypatch.setenv("TERMINALIA_RECONSTRUCT_MOCK", "1")
    tracks = segment_video(**inputs(tmp_path), sam2_model="unused")
    backend = ResultBackend({"safe": True, "model": safety._model_for("openai")},
                            reconstruct(tmp_path, tracks))
    with pytest.raises(BackendImplementationMissing, match="mock output"):
        ingest_video(dict(video_path=str(path), consent_note="test consent"), backend,
                     GPU_PROFILES["rtx-3060-12gb"])
    assert len(backend.jobs) == 2
    assert not (tmp_path / "world.json").exists()

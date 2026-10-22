"""Video-ingestion orchestration tests with the model boundary stubbed."""
import hashlib
from pathlib import Path

import pytest

from terminalia.backends import GPU_PROFILES
from terminalia.export import export_glb_bundle
from terminalia.ingest import UnsafeVideoError, ingest_video
from terminalia.schema import World


@pytest.fixture(autouse=True)
def _explicit_test_safety(monkeypatch):
    monkeypatch.setenv("TERMINALIA_SAFETY_MOCK", "1")


class StubBackend:
    name = "stub"

    def __init__(self, safe=True):
        self.safe = safe
        self.workflows = []

    def submit(self, workflow, client_id="terminalia"):
        self.workflows.append(workflow)
        return str(len(self.workflows))

    def wait(self, prompt_id):
        workflow = self.workflows[int(prompt_id) - 1]
        if workflow.get("terminalia_task") == "video_content_safety":
            return {"terminalia_result": {
                "safe": self.safe,
                "model": {"name": "omni-moderation-latest", "version": "latest",
                          "license": "OpenAI Services Agreement and Usage Policies"},
            }}
        return {"terminalia_result": {
            "models": [
                {"name": "stub-segment", "version": "1.0", "license": "test-only"},
                {"name": "stub-mesh-pose", "version": "1.0", "license": "test-only"},
            ],
            "instances": [{
                "id": "chair-1", "mesh": "meshes/chair.glb", "tris": 12,
                "poses": [{"frame": 0, "translation": [1, 2, 3],
                           "rotation_xyzw": [0, 0, 0, 1]}],
                "physics": {"mass_kg": 4.5},
            }],
        }}


def _request(tmp_path):
    video = tmp_path / "sample.mp4"
    video.write_bytes(b"synthetic-video-fixture")
    return video, {
        "video_path": str(video), "output_dir": str(tmp_path), "seed": 7,
        "consent_note": "Uploader confirms consent to process this recording.",
    }


def test_video_ingestion_builds_world_and_exports(tmp_path):
    video, request = _request(tmp_path)
    backend = StubBackend()
    data = ingest_video(request, backend, GPU_PROFILES["rtx-3060-12gb"])
    world = World.model_validate(data)

    assert len(world.assets) == 1
    assert len(world.layout.objects) == 1
    assert world.layout.objects[0].poses[0].translation == (1, 2, 3)
    assert world.video_provenance.source_sha256 == hashlib.sha256(video.read_bytes()).hexdigest()
    assert [model.version for model in world.video_provenance.models] == ["latest", "1.0", "1.0"]
    assert world.video_provenance.consent_note.startswith("Uploader confirms")
    assert backend.workflows[0]["terminalia_task"] == "video_content_safety"
    assert [node["class_type"] for node in backend.workflows[1].values()] == [
        "TerminaliaSegmentVideo", "TerminaliaReconstructInstances"]

    mesh = tmp_path / "meshes" / "chair.glb"
    mesh.parent.mkdir()
    mesh.write_bytes(b"glTF")
    world.save(str(tmp_path / "world.json"))
    export_dir = export_glb_bundle(str(tmp_path), data)
    assert (tmp_path / "world.json").is_file()
    assert (tmp_path / "export" / "gltf" / "chair-1.glb").is_file()
    assert Path(export_dir) == tmp_path / "export" / "gltf"


def test_video_ingestion_fails_closed(tmp_path):
    _, request = _request(tmp_path)
    backend = StubBackend(safe=False)

    with pytest.raises(UnsafeVideoError):
        ingest_video(request, backend, GPU_PROFILES["rtx-3060-12gb"])

    assert len(backend.workflows) == 1
    assert not (tmp_path / "world.json").exists()

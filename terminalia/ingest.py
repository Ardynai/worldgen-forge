"""Fail-closed monocular-video ingestion into the world.json contract."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .backends import Backend, GpuProfile
from .reconstruction import BackendImplementationMissing, build_reconstruction_workflow
from .safety import configured_backend, has_real_provenance
from .schema import (
    AssetEntry, InstancePose, ModelRef, Physics, PlacedObject, VideoProvenance,
    World, WorldSpec,
)


class UnsafeVideoError(ValueError):
    """The safety gate rejected a video."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _result(outputs: dict) -> dict:
    """Read the small JSON result contract from a backend adapter."""
    if isinstance(outputs.get("terminalia_result"), dict):
        return outputs["terminalia_result"]
    for output in outputs.values():
        if isinstance(output, dict) and isinstance(output.get("terminalia_result"), dict):
            return output["terminalia_result"]
    raise RuntimeError("backend returned no terminalia_result")


def _run(backend: Backend, workflow: dict, client_id: str) -> dict:
    return _result(backend.wait(backend.submit(workflow, client_id=client_id)))


def ingest_video(request: dict, backend: Backend, profile: GpuProfile) -> dict:
    """Ingest one video. Returns validated, JSON-shaped World data; never saves.

    Backend adapters own frame decoding and model execution. They must return a
    ``terminalia_result`` mapping. Safety is a separate first job so a rejected
    input cannot reach scene reconstruction.
    """
    configured_backend()  # reject-all until a real provider (or explicit test mock) exists
    path = Path(request["video_path"])
    if not path.is_file():
        raise ValueError("video_path must be an existing file")
    consent = str(request.get("consent_note", "")).strip()
    if not consent:
        raise ValueError("consent_note is required for user-provided video")
    seed = int(request.get("seed", 42))
    source_hash = _sha256(path)
    job_id = source_hash[:16]

    safety = _run(backend, {
        "terminalia_task": "video_content_safety",
        "video_path": str(path),
        "source_sha256": source_hash,
        "seed": seed,
        "sampling": "deterministic-uniform-frames",
        "fail_closed": True,
    }, f"terminalia-safety-{job_id}")
    if safety.get("safe") is not True:
        raise UnsafeVideoError("video rejected by content-safety gate")
    try:
        if not has_real_provenance(safety["model"]):
            raise ValueError("unrecognized safety model")
        safety_model = ModelRef.model_validate(safety["model"])
    except Exception as exc:
        raise UnsafeVideoError("safety verdict omitted valid model provenance") from exc

    scene_request = {
        "video_path": str(path),
        "source_sha256": source_hash,
        "seed": seed,
        "gpu_profile": profile.name,
        "mesh_preset": profile.mesh_preset,
        "output_dir": request.get("output_dir"),
    }
    scene = _run(backend, build_reconstruction_workflow(scene_request, profile),
                 f"terminalia-ingest-{job_id}")
    if scene.get("execution_mode") == "mock":
        raise BackendImplementationMissing("scene reconstruction returned mock output")
    instances = scene.get("instances")
    if not isinstance(instances, list) or not instances:
        raise RuntimeError("scene reconstruction returned no instances")

    assets: dict[str, AssetEntry] = {}
    objects: list[PlacedObject] = []
    for raw in instances:
        instance_id = str(raw["id"])
        mesh = Path(raw["mesh"])
        if mesh.is_absolute() or ".." in mesh.parts:
            raise RuntimeError("backend mesh paths must be relative and contained")
        poses = [InstancePose.model_validate(pose) for pose in raw.get("poses", [])]
        if not poses:
            raise RuntimeError(f"instance {instance_id} has no poses")
        first = poses[0]
        physics = Physics.model_validate(raw["physics"]) if raw.get("physics") else None
        assets[instance_id] = AssetEntry(
            glb=mesh.as_posix(), tris=int(raw.get("tris", 0)),
            source_preset=profile.mesh_preset,
            bbox_size=raw.get("bbox_size"),
        )
        objects.append(PlacedObject(
            id=instance_id, asset=instance_id,
            pos_xy=(first.translation[0], first.translation[2]),
            z_offset=first.translation[1], poses=poses, physics=physics,
        ))

    try:
        models = [safety_model, *[ModelRef.model_validate(m) for m in scene["models"]]]
    except Exception as exc:
        raise RuntimeError("scene reconstruction omitted valid model provenance") from exc
    world = World(
        spec=WorldSpec(prompt=request.get("prompt", "world ingested from video"), seed=seed),
        assets=assets,
        layout={"objects": objects},
        video_provenance=VideoProvenance(
            source_sha256=source_hash, consent_note=consent, models=models),
    )
    return world.model_dump(mode="json")

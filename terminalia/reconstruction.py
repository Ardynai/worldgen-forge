"""Backend workflow for video segmentation, meshing, and pose tracking."""
from __future__ import annotations

import os

from .backends import GpuProfile

SAM2_MODEL = "facebook/sam2-hiera-large-hf"
SAM2_REVISION = "214d515"
TRELLIS2_MODEL = "microsoft/TRELLIS.2-4B"
TRELLIS2_REVISION = "af44b45f2e35a493886929c6d786e563ec68364d"
FOUNDATIONPOSE_NGC_VERSION = "1.0"
FOUNDATIONPOSE_ACTION = (
    "Founder action required: accept the NVIDIA Open Model License and set "
    "NGC_API_KEY, or download FoundationPose from NVIDIA NGC and set "
    "FOUNDATIONPOSE_NGC_DIR."
)


class FounderActionRequired(RuntimeError):
    """A founder must accept terms or provision a gated model artifact."""


class BackendImplementationMissing(NotImplementedError):
    """The bundled reconstruction node has no real model execution path."""

    code = "backend_implementation_missing"

    def __init__(self, stage: str):
        self.stage = stage
        super().__init__(
            f"{self.code}: {stage} is mock-only; real model execution is not "
            "implemented. Credentials, model weights, and GPU dependencies "
            "cannot enable it. Mock output is only an orchestration fixture.")


def foundationpose_adapter(environ: dict[str, str] | None = None) -> dict:
    """Resolve the commercial NGC FoundationPose artifact without leaking keys."""
    env = os.environ if environ is None else environ
    directory = env.get("FOUNDATIONPOSE_NGC_DIR")
    if directory:
        return {"source": "local-ngc", "path": directory,
                "version": FOUNDATIONPOSE_NGC_VERSION}
    if env.get("NGC_API_KEY"):
        return {"source": "ngc", "version": FOUNDATIONPOSE_NGC_VERSION}
    raise FounderActionRequired(FOUNDATIONPOSE_ACTION)


def build_reconstruction_workflow(request: dict, profile: GpuProfile) -> dict:
    """Build the two-package backend graph; model execution stays on the backend."""
    common = {
        "video_path": request["video_path"],
        "source_sha256": request["source_sha256"],
        "seed": int(request.get("seed", 42)),
        "output_dir": request.get("output_dir") or "output",
    }
    return {
        "segment": {
            "class_type": "TerminaliaSegmentVideo",
            "inputs": {**common, "sam2_model": SAM2_MODEL,
                       "sam2_revision": SAM2_REVISION},
        },
        "reconstruct": {
            "class_type": "TerminaliaReconstructInstances",
            "inputs": {
                **common,
                "tracks": ["segment", 0],
                "mesh_preset": profile.mesh_preset,
                "mesh_steps": list(profile.mesh_steps),
                "trellis2_model": TRELLIS2_MODEL,
                "sam2_revision": SAM2_REVISION,
                "trellis2_revision": TRELLIS2_REVISION,
                "foundationpose_version": FOUNDATIONPOSE_NGC_VERSION,
            },
        },
    }

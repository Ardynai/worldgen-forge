"""SAM 2 video segmentation and instance tracking runtime node."""
from __future__ import annotations

import hashlib
import json
import os

from terminalia.reconstruction import BackendImplementationMissing


def segment_video(video_path: str, source_sha256: str, seed: int,
                  output_dir: str, sam2_model: str, sam2_revision: str) -> dict:
    """Return synthetic tracks only; the bundled real SAM 2 path is unimplemented."""
    if os.environ.get("TERMINALIA_RECONSTRUCT_MOCK") == "1":
        digest = hashlib.sha256(f"{source_sha256}:{seed}".encode()).digest()
        return {"execution_mode": "mock", "instances": [
            {"id": f"instance-{index + 1}", "bboxes": [
                {"frame": frame, "xywh": [8 + index * 24 + frame, 10 + index * 8,
                                             20 + digest[index] % 8, 18 + digest[index + 2] % 8],
                 "mask": f"masks/instance-{index + 1}/{frame:06d}.png"}
                for frame in range(2)]}
            for index in range(2)]}
    raise BackendImplementationMissing("SAM 2 segmentation")


class TerminaliaSegmentVideo:
    DESCRIPTION = str(BackendImplementationMissing("SAM 2 segmentation"))
    RETURN_TYPES = ("TERMINALIA_TRACKS",)
    FUNCTION = "run"
    CATEGORY = "Terminalia/Reconstruction"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "video_path": ("STRING",), "source_sha256": ("STRING",),
            "seed": ("INT",), "output_dir": ("STRING",),
            "sam2_model": ("STRING",), "sam2_revision": ("STRING",),
        }}

    def run(self, **inputs):
        return (json.dumps(segment_video(**inputs), sort_keys=True),)


NODE_CLASS_MAPPINGS = {"TerminaliaSegmentVideo": TerminaliaSegmentVideo}
NODE_DISPLAY_NAME_MAPPINGS = {"TerminaliaSegmentVideo": "Terminalia Segmentation (mock only)"}

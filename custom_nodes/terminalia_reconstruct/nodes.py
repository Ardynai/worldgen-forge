"""Per-instance reconstruction runtime node."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct

from terminalia.reconstruction import BackendImplementationMissing


def _mock_glb(path: Path, marker: bytes) -> str:
    """Write a deterministic, valid GLB containing one triangle."""
    positions = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
    indices = struct.pack("<3H", 0, 1, 2)
    binary = positions + indices + b"\0\0"
    document = {"asset": {"version": "2.0", "generator": "Terminalia mock"},
                "buffers": [{"byteLength": len(binary)}],
                "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36,
                                 "target": 34962},
                                {"buffer": 0, "byteOffset": 36, "byteLength": 6,
                                 "target": 34963}],
                "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3,
                               "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 0]},
                              {"bufferView": 1, "componentType": 5123, "count": 3,
                               "type": "SCALAR"}],
                "meshes": [{"name": marker.hex()[:16],
                            "primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
                "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}], "scene": 0}
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    payload += b" " * (-len(payload) % 4)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(payload) + 8 + len(binary))
                     + struct.pack("<I4s", len(payload), b"JSON") + payload
                     + struct.pack("<I4s", len(binary), b"BIN\0") + binary)
    return path.as_posix()


def reconstruct_instances(tracks: str | dict, video_path: str, source_sha256: str,
                          seed: int, output_dir: str, mesh_preset: str,
                          mesh_steps: list[int], sam2_revision: str, trellis2_model: str,
                          trellis2_revision: str,
                          foundationpose_version: str) -> dict:
    if os.environ.get("TERMINALIA_RECONSTRUCT_MOCK") != "1":
        raise BackendImplementationMissing("TRELLIS.2/FoundationPose reconstruction")
    tracks = json.loads(tracks) if isinstance(tracks, str) else tracks
    instances = []
    for index, track in enumerate(tracks["instances"]):
        marker = hashlib.sha256(f"{source_sha256}:{seed}:{index}".encode()).digest()
        relative = Path("meshes") / f"{track['id']}.glb"
        _mock_glb(Path(output_dir) / relative, marker)
        instances.append({"id": track["id"], "mesh": relative.as_posix(), "tris": 1,
                          "bbox_size": [1.0 + index, 1.0, 1.0],
                          "poses": [{"frame": box["frame"],
                                     "translation": [index * 2.0, 0.0, frame * 0.1],
                                     "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}
                                    for frame, box in enumerate(track["bboxes"])]})
    return {"execution_mode": "mock", "instances": instances, "models": [
        {"name": "Terminalia reconstruction mock", "version": "1",
         "license": "test-only; no model executed"},
    ]}


class TerminaliaReconstructInstances:
    DESCRIPTION = str(BackendImplementationMissing("TRELLIS.2/FoundationPose reconstruction"))
    RETURN_TYPES = ("TERMINALIA_RESULT",)
    RETURN_NAMES = ("terminalia_result",)
    OUTPUT_NODE = True
    FUNCTION = "run"
    CATEGORY = "Terminalia/Reconstruction"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "tracks": ("TERMINALIA_TRACKS",), "video_path": ("STRING",),
            "source_sha256": ("STRING",), "seed": ("INT",),
            "output_dir": ("STRING",), "mesh_preset": ("STRING",),
            "mesh_steps": ("INT", {"forceInput": True}),
            "sam2_revision": ("STRING",), "trellis2_revision": ("STRING",),
            "trellis2_model": ("STRING",),
            "foundationpose_version": ("STRING",),
        }}

    def run(self, **inputs):
        result = reconstruct_instances(**inputs)
        return {"ui": {"terminalia_result": result}, "result": (json.dumps(result),)}


NODE_CLASS_MAPPINGS = {"TerminaliaReconstructInstances": TerminaliaReconstructInstances}
NODE_DISPLAY_NAME_MAPPINGS = {
    "TerminaliaReconstructInstances": "Terminalia Reconstruction (mock only)"}

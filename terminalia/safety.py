"""Real, fail-closed frame moderation for user-provided video."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


FOUNDER_ACTION = (
    "No real video safety backend is configured. Founder action required: "
    "accept the provider terms and set OPENAI_API_KEY, or deploy Nemotron "
    "Content Safety and set NVIDIA_API_KEY or NEMOTRON_SAFETY_DIR."
)
FRAME_COUNT = 8
REAL_MODELS = {
    ("omni-moderation-latest", "OpenAI Services Agreement and Usage Policies"),
    ("nvidia/nemotron-3.5-content-safety",
     "OpenMDW-1.1, Gemma Terms of Use, and Gemma Prohibited Use Policy"),
}


@dataclass(frozen=True)
class SafetyVerdict:
    safe: bool
    model: dict[str, str]
    frame_count: int
    categories: list[str]
    raw_ref: str

    def model_dump(self) -> dict:
        return asdict(self)


def configured_backend() -> str:
    if os.environ.get("TERMINALIA_SAFETY_MOCK") == "1":
        return "mock"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("NVIDIA_API_KEY") or os.environ.get("NEMOTRON_SAFETY_DIR"):
        return "nemotron"
    raise RuntimeError(FOUNDER_ACTION)


def has_real_provenance(model: object) -> bool:
    return (isinstance(model, dict) and isinstance(model.get("version"), str)
            and bool(model["version"])
            and (model.get("name"), model.get("license")) in REAL_MODELS)


def sample_frame_indices(total: int, count: int = FRAME_COUNT) -> list[int]:
    """Return deterministic, uniformly spaced frame indices including endpoints."""
    if total <= 0:
        return []
    size = min(total, count)
    return [i * (total - 1) // max(size - 1, 1) for i in range(size)]


def _frames(path: Path) -> list[bytes]:
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise RuntimeError("video safety requires OpenCV (pip install opencv-python)") from exc
    video = cv2.VideoCapture(str(path))
    try:
        indices = sample_frame_indices(int(video.get(cv2.CAP_PROP_FRAME_COUNT)))
        encoded: list[bytes] = []
        for index in indices:
            video.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = video.read()
            ok_jpeg, jpeg = cv2.imencode(".jpg", frame) if ok else (False, None)
            if not ok_jpeg:
                return []
            encoded.append(jpeg.tobytes())
        return encoded
    finally:
        video.release()


def _post(url: str, payload: dict, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(
        url, json.dumps(payload).encode(),
        {"Content-Type": "application/json", **headers}, method="POST")
    last: Exception | None = None
    for _ in range(3):  # initial attempt plus two bounded retries
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                value = json.loads(response.read())
                if not isinstance(value, dict):
                    raise ValueError("non-object safety response")
                return value
        except Exception as exc:
            last = exc
    raise RuntimeError("content-safety service failed after two retries") from last


def _data_url(frame: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(frame).decode("ascii")


def _sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _openai(frames: list[bytes]) -> SafetyVerdict:
    model = {"name": "omni-moderation-latest", "version": "latest",
             "license": "OpenAI Services Agreement and Usage Policies"}
    categories: set[str] = set()
    refs: list[str] = []
    safe = True
    for frame in frames:
        raw = _post("https://api.openai.com/v1/moderations", {
            "model": model["name"],
            "input": [{"type": "image_url", "image_url": {"url": _data_url(frame)}}],
        }, {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
        refs.append(str(raw.get("id", "")))
        results = raw.get("results")
        if not isinstance(results, list) or len(results) != 1:
            safe = False
            continue
        result = results[0]
        if not isinstance(result, dict) or not isinstance(result.get("flagged"), bool):
            safe = False
            continue
        safe &= not result["flagged"]
        flags = result.get("categories", {})
        if isinstance(flags, dict):
            categories.update(k for k, v in flags.items() if v is True)
    return SafetyVerdict(safe, model, len(frames), sorted(categories), ",".join(filter(None, refs)))


def _nemotron(frames: list[bytes]) -> SafetyVerdict:
    model = {"name": "nvidia/nemotron-3.5-content-safety", "version": "3.5",
             "license": "OpenMDW-1.1, Gemma Terms of Use, and Gemma Prohibited Use Policy"}
    base = os.environ.get("NEMOTRON_SAFETY_DIR", "https://integrate.api.nvidia.com")
    if Path(base).is_dir():
        base = os.environ.get("NEMOTRON_SAFETY_URL", "http://127.0.0.1:8000")
    headers = ({"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}"}
               if os.environ.get("NVIDIA_API_KEY") else {})
    categories: set[str] = set()
    refs: list[str] = []
    safe = True
    for frame in frames:
        raw = _post(base.rstrip("/") + "/v1/chat/completions", {
            "model": model["name"], "temperature": 0, "max_tokens": 128,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Classify this image for content safety."},
                {"type": "image_url", "image_url": {"url": _data_url(frame)}},
            ]}], "chat_template_kwargs": {"request_categories": True},
        }, headers)
        refs.append(str(raw.get("id", "")))
        try:
            text = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            safe = False
            continue
        match = re.search(r"User Safety:\s*(safe|unsafe)\b", str(text), re.I)
        if not match:
            safe = False
            continue
        safe &= match.group(1).lower() == "safe"
        category_match = re.search(r"Safety Categories:\s*(.+)", str(text), re.I)
        if category_match:
            categories.update(x.strip() for x in category_match.group(1).split(",") if x.strip())
    return SafetyVerdict(safe, model, len(frames), sorted(categories), ",".join(filter(None, refs)))


def check_video(video_path: str | Path, source_sha256: str) -> SafetyVerdict:
    """Moderate uniformly sampled frames; uncertainty can never produce safe."""
    backend = configured_backend()
    path = Path(video_path)
    try:
        actual_hash = _sha256(path)
    except OSError:
        actual_hash = ""
    if actual_hash != source_sha256:
        return SafetyVerdict(False, _model_for(backend), 0, ["source-hash-mismatch"], "")
    frames = _frames(path)
    if not frames:
        return SafetyVerdict(False, _model_for(backend), 0, ["decode-error"], "")
    if backend == "mock":
        raw = os.environ.get("TERMINALIA_SAFETY_MOCK_RESULT", "unsafe")
        return SafetyVerdict(raw == "safe", _model_for("mock"), len(frames),
                             [] if raw == "safe" else ["mock-unsafe"], source_sha256[:16])
    try:
        return _openai(frames) if backend == "openai" else _nemotron(frames)
    except Exception:
        if backend == "nemotron":
            raise
        return SafetyVerdict(False, _model_for(backend), len(frames), ["service-error"], "")


def _model_for(backend: str) -> dict[str, str]:
    if backend == "mock":
        return {"name": "Terminalia safety mock", "version": "1",
                "license": "test-only; no moderation model executed"}
    if backend == "openai":
        return {"name": "omni-moderation-latest", "version": "latest",
                "license": "OpenAI Services Agreement and Usage Policies"}
    return {"name": "nvidia/nemotron-3.5-content-safety", "version": "3.5",
            "license": "OpenMDW-1.1, Gemma Terms of Use, and Gemma Prohibited Use Policy"}

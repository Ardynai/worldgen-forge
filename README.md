# Worldgen Forge

Repository: [Ardynai/worldgen-forge](https://github.com/Ardynai/worldgen-forge).
Formerly `Ardynai/terminalia`, this is the **world-generation engine**, separate
from Terminalia, the public Multiverse platform. See [the naming decision](docs/naming-collision.plan.md).
The Python distribution, `terminalia` imports/CLI and generated engine identifiers
remain unchanged for compatibility; the repository rename requires no code migration.

<p align="center">
  <strong>Agentic 3D open-world generation at scale — on any GPU, or none at all.</strong>
</p>

---

## What is this?

Worldgen Forge turns one text prompt into an **explorable, engine-ready 3D world**:

```
"volcanic island with a ruined temple and pirate cove"
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ SPEC      prompt → structured world plan             │
│ TERRAIN   procedural heightfields, agent-authored    │
│ LAYOUT    flat-area site selection + composition     │
│ ASSETS    TRELLIS.2-4B image → PBR meshes            │
│ PLACE     contact-ratio search (no floating props)   │
│ REFINE    BlenderMCP render-inspect-refine loop      │
│ EXPORT    UE 5.8 · Unity · Godot · glTF · flythrough │
└──────────────────────────────────────────────────────┘
```

Inspired by Tencent's WorldClaw paper (arXiv 2608.05248) — but built entirely
from open models and swappable compute backends. No Tencent code required.

## Highlights

- **Any hardware** — RTX 3060 12GB to DGX Spark 128GB, plus Comfy Cloud credits
  and RunPod serverless for no-GPU users. Quality presets scale automatically
  via named `GpuProfile`s.
- **Deterministic worlds** — same seed, same world. Every stage re-runs cleanly.
- **`world.json` as truth** — one pydantic schema carries the whole state;
  every stage reads and writes it.
- **Agent-native** — each stage is a plain function with JSON-shaped I/O; agent
  skill definitions included.
- **Engine-ready output** — Unreal Python import macro, Unity editor script,
  Godot scene, generic glTF manifest.

## Quick start

```bash
pip install -e .
export COMFY_CLOUD_API_KEY=...   # or run local ComfyUI — auto-detected
python -m terminalia generate \
    --prompt "volcanic island with a ruined temple and pirate cove" \
    --name my-first-world --seed 42
```

Then export wherever:

```python
from terminalia.export import write_ue_import_script
write_ue_import_script("worlds/my-first-world", world)
```

Full walkthrough: [docs/ONBOARDING.md](docs/ONBOARDING.md)

## Compute backends

| Backend | Auth | Cost | Notes |
|---|---|---|---|
| Local ComfyUI | none | free | auto-detected; any port |
| Comfy Cloud | API key | credits | works from a laptop with no GPU |
| RunPod serverless | API key | $/sec | burst rendering, cold starts |
| Custom HTTP | varies | varies | any ComfyUI-compatible URL |

Hardware tiers: 12GB (512 preset) → 24GB (1024 cascade) → 32GB+ (1536 cascade,
full decode) → 128GB (max steps, bf16 video). See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Documentation

| Doc | Contents |
|---|---|
| [docs/ONBOARDING.md](docs/ONBOARDING.md) | first world in 10 minutes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | repo map + data flows |
| [docs/how-it-works/](docs/how-it-works/) | per-stage deep dives |
| [docs/skills.md](docs/skills.md) | agent skill contracts |
| [docs/v0.2.md](docs/v0.2.md) | engine exports + video stage |
| [docs/roadmap.md](docs/roadmap.md) | where this is going |
| [DECISIONS.md](DECISIONS.md) | standing decisions |
| [CONTRIBUTING.md](CONTRIBUTING.md) | ground rules |

## Status & honesty

`v0.2` — terrain engine, placement search, asset bindings, layout selection,
engine exporters, backend-routed Wan2.1/LTX-2 flythrough execution, the commercial-model
video reconstruction adapter, and the optional FixAnything refinement adapter are
implemented and stub-backend tested. The Blender refine loop and real
Wan/FixAnything/LTX/reconstruction model execution are not end-to-end tested in-repo.
The video-ingestion safety gate is wired to real OpenAI and NVIDIA multimodal
moderation paths and rejects every video until one is explicitly configured.
The README will always say exactly this much.

## License

MIT for Terminalia code. Generated content inherits upstream model licenses
(TRELLIS.2 is MIT; verify alternatives before commercial use).

## Security

See [SECURITY.md](SECURITY.md) — workflow JSON and Blender MCP are code-execution
surfaces; read before exposing anything beyond localhost.

## Platform support

| Platform | Status | Notes |
|---|---|---|
| Windows + NVIDIA | ✅ primary dev target | everything local |
| Linux + NVIDIA | ✅ fully supported | ComfyUI local, same presets |
| **Apple Silicon (M-series Mac)** | ✅ works via MPS | terrain/placement/export are pure Python — run anywhere. Generation stages route to a remote backend (Comfy Cloud/RunPod) or a LAN ComfyUI box; local MPS generation possible for some models but not TRELLIS.2 CUDA paths |
| Any OS, no GPU | ✅ via cloud backends | terrain/placement/export are CPU-only; GPU stages route to cloud/rental |

The pipeline is deliberately split: **terrain, layout, placement, and all
exports are pure Python + numpy** and run on anything. Only the generative
stages (concept images, meshes, video) need GPU acceleration — and those are
backend-routed, so a MacBook user gets the full pipeline by pointing at
Comfy Cloud or a rental box.

## Consistency & editing stack (all installed)

| Capability | Tool | Status |
|---|---|---|
| Face swap onto any render | ReActor (15 nodes) + CodeFormer restore | ✅ |
| Identity-consistent generation | InstantID (+ insightface, onnxruntime) | ✅ |
| Clean alpha cutouts | BiRefNet / RMBG matting | ✅ |
| 4× upscaling | 4x-UltraSharp, 4x_NMKD-Siax | ✅ |
| Style/character LoRA training | ai-toolkit (GUI at :8670, CLI configs in `config/examples/`) | ✅ |
| Video → frames | VHS_LoadVideo → SaveImage | ✅ verified |
| Video scene reconstruction | SAM 2 → TRELLIS.2 → FoundationPose (NGC) | ✅ adapter + mock; runtime models required |

LoRA workflow: train a world-style or character LoRA in ai-toolkit
(`ui` GUI or `config/examples/train_lora_chroma_24gb.yaml` as template) →
drop the `.safetensors` into `models/loras/` → load via `LoraLoaderModelOnly`
in any Terminalia asset workflow. Deterministic seeds + pinned LoRAs =
consistent style across every generation.

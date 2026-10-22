# Roadmap

Honest status markers: ✅ shipped · 🔨 in progress · 🧭 planned · 💡 idea

## v0.1 — Terrain + placement engine ✅
- [x] Scene schema (`world.json`, pydantic)
- [x] Procedural terrain operator engine (fbm/ridged/voronoi/mountains/rivers/
      coasts/terraces)
- [x] Heightmap + region-mask export
- [x] Contact-ratio placement search with slope limits
- [x] Collision pass
- [x] ComfyUI asset bindings (SDXL concept → TRELLIS.2 GLB)
- [x] CLI (generate / validate)

## v0.2 — Engines, video, consistency ✅
- [x] UE 5.x Python import macro
- [x] Unity editor script + manifest
- [x] Godot 4 scene writer
- [x] Generic glTF bundle + manifest
- [x] Camera keyframe sampler + flythrough specs (Wan 2.2 / LTX-2)
- [x] Character lock (Qwen-Image-Edit multi-view sheets)
- [x] Face swap spec (ReActor + CodeFormer)
- [x] Layout stage: flat-area scoring, region-masked site selection
- [x] Repo integrations registry (17 tools mapped to pipeline roles)

## v0.3 — Compute backends 🔨 (this release)
- [x] Backend abstraction (local / Comfy Cloud / RunPod / custom)
- [x] GpuProfile tiers (12GB → 128GB) with automatic preset scaling
- [x] `resolve()` one-call setup with auto-detection
- [ ] RunPod serverless end-to-end test on a real endpoint
- [ ] Comfy Cloud paid-tier submission test
- [ ] Cost estimator per world (images × meshes × video-seconds per backend)

## v0.4 — Agent integration 🧭
- [ ] Hermes skills from docs/skills.md as installable skill pack
- [ ] BlenderMCP refine loop automation (import → render → critique → fix)
- [ ] Vision-based acceptance criteria for refine iterations
- [ ] Layout composition images via Qwen-Image-Edit-GGUF / Flux Kontext

## v0.5 — Video & characters 🧭
- [ ] Wan 2.2 I2V/FLF2V flythrough execution end-to-end
- [ ] LTX-2 joint audio+video cutscenes
- [ ] Character sheet pipeline → canonical face bank → ReActor application
- [ ] Audio2Face-3D NPC facial animation bridge
- [ ] omnivoice/magenta narration+score packaging

## v0.6 — Scale & capture 🧭
- [ ] Multi-region streaming worlds (adjacent tiles, shared borders)
- [ ] Asset LOD baking via Blender decimation
- [ ] WorldMirror 2.0 splat side-channel → SuperSplat edit → re-import
- [ ] Splat→mesh conversion (SuGaR-class) — biggest known gap

## 💡 Ideas parking lot
- Prompt → N candidate worlds → agent ranks and picks
- Biome-aware UE landscape material/splatmap generation
- Community world-template format (share seeds + op programs, not meshes)
- DGX Spark multi-model residency: terrain+asset+video models hot simultaneously
- Terminalia Server: thin web UI over the pipeline for non-technical creators

## v0.7 — parked plans (2026-08-31 final pass) 🧭
Josh is parking active build. Every remaining item is committed as a plan doc
**co-located in the folder that will do the work**; nothing is forgotten. Index:

| Plan | Area | Starts when |
|---|---|---|
| [`terminalia/integrations/fabric-sidecar.plan.md`](../terminalia/integrations/fabric-sidecar.plan.md) | fabric integration (HTTP-only, fail-closed, no private imports) | transport-d URL+token provisioned |
| [`terminalia/schema-evolution.plan.md`](../terminalia/schema-evolution.plan.md) | world.json evolution per stage | fires with each stage PR |
| [`docs/how-it-works/refine-blender-loop.plan.md`](how-it-works/refine-blender-loop.plan.md) | BlenderMCP place→refine→re-render loop | real-weights E2E unblocked |
| [`docs/how-it-works/backends-compute.plan.md`](how-it-works/backends-compute.plan.md) | real Comfy Cloud / RunPod E2E, more GpuProfiles, cost estimator | credits/keys |
| [`docs/how-it-works/flythrough.ltx2-commercial.plan.md`](how-it-works/flythrough.ltx2-commercial.plan.md) | LTX-2 license path (attestation → paid CUA at $10M ARR) | ARR trigger |
| [`tests/real-weights-e2e.plan.md`](../tests/real-weights-e2e.plan.md) | real-weights E2E (fix_anything + safety) | founder actions |
| [`docs/founder-activation-runbook.plan.md`](founder-activation-runbook.plan.md) | exact steps to flip gated models | Josh's decision |
| [`docs/tool-integration-build-tickets.plan.md`](tool-integration-build-tickets.plan.md) | splat gallery · img2threejs-look · Gemini STT · OVOW/code-world-model/Block3D slots · DiffusionOPSD v2 track | per-ticket triggers |
| [`docs/naming-collision.plan.md`](naming-collision.plan.md) | repository renamed to `worldgen-forge`; runtime identifiers preserved | D9, 2026-09-08 |

Open PRs awaiting merge (Planner corroboration at each SHA): #4 fix_anything
node (`13806d5`) · #5 flythrough (`587d9f7`) · #6 scene reconstruction
(`7efe7a3`) · #7 real safety gate (`a75d168`). Child-safety posture until a
real moderation backend + key exists: the gate stays HARD fail-closed (reject
all video) — by design.

## v0.7 — Agent control layer 🧭
- [ ] **Terminalia MCP Server** — expose the whole pipeline as MCP tools
      (generate_world, add_asset, place_object, export_ue/unity/godot,
      render_flythrough) so any agent (Hermes, Claude, Cursor, OpenClaw) can
      drive world generation conversationally without touching Python
- [ ] Unity control bridge (research in progress: editor MCP plugin vs
      batchmode CLI vs generated C# — see docs/how-it-works/unity.md when done)
- [ ] OpenCut integration when upstream ships Editor API / headless mode
- [ ] Claw3D bridge: live world preview via its WebSocket API

## 💡 Ideas parking lot
- Prompt → N candidate worlds → agent ranks and picks
- Biome-aware UE landscape material/splatmap generation
- Community world-template format (share seeds + op programs, not meshes)
- DGX Spark multi-model residency: terrain+asset+video models hot simultaneously
- Terminalia Server: thin web UI over the pipeline for non-technical creators
- Unity Package (unitypackage) export format for one-click asset import

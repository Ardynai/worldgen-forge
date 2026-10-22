# Decisions

Standing decisions so they are not relitigated. Newest last.

## D1 — world.json as the only state
Every stage reads and writes one pydantic-validated file. No hidden state, no
side-channel databases. Re-running a stage = delete its section and re-run.
(2026-08-22)

## D2 — Deterministic stages
Same seed + same operator program = byte-identical heightmap and placement.
Ambient randomness (wall clock, unseeded RNG) is banned inside stage code.
(2026-08-22)

## D3 — Backends are swappable abstractions
Local ComfyUI, Comfy Cloud, RunPod, and custom HTTP endpoints all implement the
same submit/wait/fetch interface (`terminalia.backends.Backend`). Stage code
never knows which is active. Rationale: Josh's RTX 6000 / DGX Spark plans plus
users without GPUs. (2026-08-22)

## D4 — TRELLIS.2 over Hunyuan3D for assets
MIT license vs community restrictions; equal-or-better quality in 2026
roundups; already integrated in ComfyUI via Trellis2-GGUF with proven API wire
format. (2026-08-22)

## D5 — GpuProfile scaling instead of hardcoded 4090 presets
Quality presets attach to named VRAM tiers; remote backends clamp to their own
advertised hardware when queryable. Rationale: multi-hardware future (4090 now,
RTX 6000 + DGX Spark planned) and cloud users. (2026-08-22)

## D6 — Agent-authored operator programs for terrain
Terrain is composed from a small op catalog executed deterministically rather
than a single monolithic generator — mirrors WorldClaw's key trick, keeps
terrain auditable and editable by both agents and humans. (2026-08-22)

## D7 — Refinement artifacts and provenance belong in world.json
Optional runtime refinement records typed render inputs, outputs, decisions,
backend/profile selection, seed, and pinned model revisions in `World.refine`.
This keeps skipped passes auditable and prevents render paths or model versions
from becoming side-channel state. The schema contract moves from 0.1 to 0.2.
(2026-08-30)

## D8 — Flythrough execution and provenance belong in world.json
VIDEO submits profile-filled ComfyUI templates through the swappable backend
contract. The selected engine, pinned model and license, seed, backend/profile,
and returned video artifacts are recorded in `World.video_provenance`; LTX-2 is
fail-closed behind its revenue attestation. The schema contract moves from 0.2
to 0.3. (2026-08-31)

## D9 — Worldgen Forge is the repository name; runtime names stay compatible

The founder's Batch 6 instruction authorizes renaming the engine repository to
stop its collision with Terminalia, the Multiverse public brand. Selected
`Ardynai/worldgen-forge`: its name describes the generation pipeline without
reopening the platform brand. Preserve the repository ID, history, open PRs,
Python distribution/import/CLI names, world schema and generated engine/custom
node identifiers. This is repository metadata and documentation only; a future
package migration would be a separate explicit compatibility task. See
[the recorded naming decision](docs/naming-collision.plan.md). (2026-09-08)

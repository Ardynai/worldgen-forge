# Lab standards adopted

Which locus-evolution-lab standards this repo follows, read at lab commit `e3d6f84` (`private/standards/`) on 2026-10-19. Each standard keeps the only copy of its rules; below is its adoption checklist, ticked with the path that satisfies it, or marked n/a with the reason.

## Planner Operating Doctrine — adopted

- [x] `docs/runbooks/pr-merge-gate.md` — CI green at the exact head; builder may merge its own green PR; planner corroborates.

## CI Doctrine — adopted (first CI)

- [x] `.github/workflows/ci.yml`: `tests` (compile + `pytest` over the stub-backend suite), `workflow-doctrine`, and the `ci-green` aggregator.
- [ ] Branch protection requires only **CI green** — founder action (free on a public repository).
- [x] `permissions: contents: read`; no `secrets.*` (public repository; nothing in CI needs one); no `pull_request_target`.
- [x] Both actions pinned to commit SHAs; `pytest` pinned to `9.1.1`; `scripts/ci/check-workflow-doctrine.mjs` enforces the pins.
- [x] End-state checks: n/a — no deploy or publish job.

## Cost Gate — not adopted

No hosted spend: public repository (free runners); cloud backends are the operator's own and never run in CI.

## Scanner Logs — n/a

No secret or PII scanner. `terminalia/safety.py` is a content-safety gate on generated worlds, not a scanner that reports findings.

## Data Deletion & Retention — not instanced here

Terminalia runs on the operator's machine. Video ingestion keeps the source hash and an uploader consent note (`world.video_provenance`); uploaded videos can show people. Instance the standard before any hosted or multi-user ingestion.

## Remote

The founder's local checkout had no `origin`; it now points at `Ardynai/worldgen-forge` (GitHub redirects `Ardynai/terminalia` there). The older `github-fallback` remote names the same repository.

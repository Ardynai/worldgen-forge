# PR merge gate

The merge gate for Terminalia. Adopted 2026-10-19 from the Planner Operating Doctrine and CI Doctrine in locus-evolution-lab `private/standards/` (lab `e3d6f84`; a private repository, so the paths are given as text). Adoption record: [`docs/governance/locus-adoption.md`](../governance/locus-adoption.md).

## The gate

A PR merges only when **CI green** (`ci-green` in `.github/workflows/ci.yml`) succeeded at the PR's **exact head SHA**. It needs `tests` (compile, then `pytest` over the stub-backend suite — no GPU, model weights, network or secrets) and `workflow-doctrine` (actions pinned to commit SHAs, read-only permissions, no stored secrets, the aggregator itself), runs even when one fails, and is red unless each succeeded. A skipped, cancelled or unstartable check is red: stop and report.

Before opening a PR, run the suite locally from the repo root: `python -m pytest -q tests` (`python tests/test_smoke.py` alone still works). Real-weights and Blender paths are not exercised in CI; say in the PR when a change depends on them.

## Who merges

The builder may merge its own PR once **CI green** passed at the exact head. No automated reviewer is part of the gate. The planner corroborates at the exact merge SHA before the next batch builds on it.

## Cost

No hosted spend. The repository is public, so standard GitHub-hosted runners cost nothing; optional cloud backends (`COMFY_CLOUD_API_KEY`, `RUNPOD_API_KEY`) are the operator's own accounts and never run in CI. The lab's cost gate is not adopted.

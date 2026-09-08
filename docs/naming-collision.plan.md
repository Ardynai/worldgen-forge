# DECISION — Worldgen Forge repository identity

**Status:** decided 2026-09-08 under the founder's Batch 6 rename instruction.
**Repository:** `Ardynai/worldgen-forge` (formerly `Ardynai/terminalia`).
The descriptive name identifies the world-generation engine and leaves Terminalia
as the Multiverse public brand. See D9 in [DECISIONS.md](../DECISIONS.md).

The GitHub repository identity, history and pull requests are preserved. Python
package/distribution/CLI names, `world.json`, custom-node names and engine export
identifiers are compatibility contracts and remain `terminalia`/`Terminalia` where
already defined. No model, dependency, license, credential, deployment or runtime
behavior changes. Existing local worktree directories need no move.

For an existing clone, update the relevant remote URL to
`https://github.com/Ardynai/worldgen-forge.git`. The shared local canonical
repository's `github-fallback` remote is updated as part of this rename. Other
clones and external notes may still contain the historical URL; no private vault,
memory or Notion record is edited by this task. Historical PR evidence keeps its
original provenance. Old-name redirects were checked at the rename; callers
should still adopt the new URL rather than depend on redirects indefinitely.

## Historical analysis — 2026-08-31, superseded by the decision above

The options below preserve the original reasoning, not an open decision or build
queue. The old proposal to rename imports together with the repository is not
part of the accepted scope.

## The collision
Two things currently carry the name:
1. **This repo** — `Ardynai/terminalia`, the world-gen ENGINE (public, MIT,
   Python, the pipeline described in README.md).
2. **"Terminalia" as the public rebrand of multiverse** — the trading-stack /
   platform product (per Notion + multiverse project records).

Search, links, and branding will collide: `github.com/Ardynai/terminalia` ranks
for both meanings; docs, conversations, and package names become ambiguous.

## Options
**A. Rename the engine repo** (e.g. `Ardynai/<new-engine-name>`; candidates
keep the tree theme: `arboreum`, `silvae`, `xylomata`). 
- Pros: engine is young (20 commits, 3 merged PRs, external links minimal);
  rename cost is one-time and low. Multiverse rebrand naming is presumably
  further committed (marketing/public-facing).
- Cons: breaks the growing external reference set (Hermes memory, session
  history, vault notes all say "terminalia repo = engine").

**B. Rebrand multiverse in place** (pick a different public name; leave the
engine as terminalia).
- Pros: zero cost here; engine keeps the name every doc/skill/vault note
  already uses.
- Cons: multiverse rebrand work happens elsewhere and may already be invested.

**C. Disambiguate with qualifiers** (engine = "Terminalia Engine", rebrand =
"Terminalia Platform"), keep both names.
- Pros: zero migration cost either side.
- Cons: weakest fix — the collision persists in search/URLs; docs must
  disambiguate forever.

## Recommendation
 lean **A** (rename the engine) IF the multiverse rebrand is significantly more
invested; else **B**. Decision inputs Josh should weigh: external inbound links
to each, how far the rebrand has propagated, trademark/trust concerns on the
public-product side. Do NOT let this block the parked build plans — they are
written name-neutrally and survive either outcome.

## What a rename entails (if A)
- GitHub rename (redirects old URLs), update `pyproject.toml` name + imports
  via one mechanical PR, README/AGENT/ONBOARDING sweep, vault + Hermes memory
  update (repo paths), Notion repo records.

## Recorded outcome

The Batch 6 instruction explicitly authorized renaming this repository and left
the name to engineering judgment. Option A was selected as `worldgen-forge`;
option B would disturb the already established Multiverse brand, and option C
would keep the URL collision. This resolves the repository naming item only,
not any separate founder landing or licensing question.

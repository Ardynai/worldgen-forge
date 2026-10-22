# Video ingestion

**The bundled reconstruction pipeline is mock-only.** Real SAM 2 segmentation
and TRELLIS.2/FoundationPose execution are not implemented. Provisioning model
keys, weights, or GPU dependencies cannot make these nodes work. The generic
backend transport and ingestion orchestration exist; that is not evidence of
a working video-to-world model pipeline.

## Owns

The optional `VIDEO INGEST` path turns a consented monocular video into the
assets and layout records consumed by PLACE and EXPORT. Validated `world.json`
remains the only pipeline state.

## Implemented orchestration and planned model execution

`terminalia.ingest.ingest_video(request, backend, profile)` hashes the source,
requires a consent note, and runs the fail-closed content-safety job before it
submits reconstruction. The reconstruction graph connects two custom packages:

1. `terminalia_segment` is intended to produce SAM 2 instance masks and tracks.
2. `terminalia_reconstruct` is intended to produce TRELLIS.2 meshes and
   FoundationPose 6DoF tracks using each mesh as a CAD reference.

Both bundled nodes expose a `mock only` display name and a description of the
missing implementation. Without `TERMINALIA_RECONSTRUCT_MOCK=1`, they raise
`terminalia.reconstruction.BackendImplementationMissing` (a
`NotImplementedError`) with `code="backend_implementation_missing"` and the
failing `stage`, before checking credentials, importing GPU libraries, or
writing artifacts. This is an engineering dependency, not a founder key task.

The backend returns relative GLB paths, triangle counts, bounds, pose tracks,
and optional physics. Ingestion validates the contract and maps the first pose
to PLACE-compatible coordinates without discarding the full track.

## Models, licenses, and runtime setup

| Model | License recorded in provenance | Runtime source |
|---|---|---|
| SAM 2 | Apache-2.0 | Hugging Face revision pinned in `reconstruction.py` |
| TRELLIS.2-4B | MIT | Hugging Face revision pinned in `reconstruction.py` |
| FoundationPose (NVIDIA NGC) | NVIDIA Open Model License | `NGC_API_KEY` or `FOUNDATIONPOSE_NGC_DIR` |

These are planned model identities, not execution provenance. No weights are
committed. `foundationpose_adapter()` remains a separate artifact-configuration
helper; satisfying its terms/key checks does not implement either node.

For dependency-free orchestration tests, set
`TERMINALIA_RECONSTRUCT_MOCK=1`. Mock execution writes deterministic simple
GLBs and fixed pose tracks from the source hash and seed. Its results carry
`execution_mode="mock"` and identify `Terminalia reconstruction mock`, with
`test-only; no model executed` provenance, rather than listing real models.
Ingestion rejects mock scene results instead of producing a completed world.
The node fixtures can still be tested directly; they do not establish real
segmentation, reconstruction, pose quality, or commercial model availability.

SAM 3 is deliberately not implemented: its custom Meta license requires legal
review before it can replace Apache-2.0 SAM 2. Hi3DGen weights are not wired
because no clearly licensed official checkpoint was identified.

## Determinism and provenance

Raw source bytes are SHA-256 hashed. The caller's seed, hash, backend profile,
model names, versions, licenses, and uploader consent note are recorded or sent
with each job. The stage uses no clock or ambient randomness.

The preceding safety-model implementation STOP is resolved by the real,
fail-closed dual provider gate described in [safety-gate.md](safety-gate.md).

## License and implementation STOPs

- SAM 3 is released under Meta's custom SAM License, which has no blanket
  noncommercial restriction but requires product/legal compliance review.
- Hi3DGen source is MIT, but an official pretrained checkpoint with a clearly
  documented weights license was not identified. No Hi3DGen weights are wired.
- The NVlabs FoundationPose repository license restricts it to noncommercial
  use. It is not wired. NVIDIA's separate commercial NGC artifact requires
  accepting and reviewing NVIDIA terms before an adapter can be added.
- NVIDIA Nemotron 3.5 Content Safety is wired as the local multimodal adapter,
  but remains disabled until its OpenMDW/Gemma/NIM terms are accepted and the
  deployment environment is configured. No weights are shipped here.

Official references: [SAM 3](https://github.com/facebookresearch/sam3),
[Hi3DGen](https://github.com/bytedance/Hi3DGen),
[FoundationPose license](https://github.com/NVlabs/FoundationPose/blob/main/LICENSE),
[NVIDIA FoundationPose](https://catalog.ngc.nvidia.com/orgs/nvidia/tao/models/foundationpose/),
and [Nemotron 3.5 Content Safety](https://build.nvidia.com/nvidia/nemotron-3.5-content-safety/modelcard).

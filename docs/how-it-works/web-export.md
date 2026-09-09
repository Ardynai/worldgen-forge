# Data-only splat web export

`python -m terminalia export-web worlds/example/world.json` exports the optional
`world.json.splat` descriptor to a new `export/web` directory beside world.json.
It creates `scene.splat` and `manifest.json`, without generating content, fetching
URLs, bundling a viewer, publishing, or changing the source world. The existing
Python package and CLI name remain `terminalia` for compatibility.

The descriptor has `file` (forward-slash path relative to the world directory),
`sha256` (64 lowercase hexadecimal characters), `license`, `attribution`, and
`up_axis` (`Y` or `Z`, default `Y`). Unknown descriptor fields fail validation.
License and attribution are author assertions, not license review or publication
consent. Only a local `.splat` file matching the declared SHA-256 is accepted.

## Version 1 wire contract

The manifest identifies `format: multiverse.splat.web`, `version: 1`, a title
from the first 120 prompt characters, the world seed, `units: meters`, and
`upAxis`. Its `asset` contains `file: scene.splat`, SHA-256, byte count, point
count, position-center `bounds.min`/`bounds.max`, license and attribution.
Bounds exclude Gaussian scale extents. No axis or coordinate conversion occurs.
No source paths, history, credentials, URLs or executable scripts are exported.
The title can contain user content: export is an explicit local action, not
automatic disclosure to a service. Consumers must render metadata as text.

Records are 32 bytes: six little-endian float32 values (XYZ position, XYZ scale),
four uint8 RGBA values, and four uint8 packed quaternion values. Positions and
scales must be finite; positions are limited to +/-10,000 meters and scales to
(0, 1,000] meters. An all-128 packed quaternion is rejected as zero rotation
norm. The exporter accepts 1–500,000 records, at most 16,000,000 bytes. This is a
bounded interchange profile, not acceptance of every splat representation.

Consumers must reject unknown versions, verify byte count, SHA-256, record count
and binary constraints before rendering, and honor the declared up axis. This
export does not establish that a browser has enough GPU memory for a scene.

## Failure and lifecycle behavior

Missing descriptor/file: `SPLAT_SOURCE_REQUIRED` / `SPLAT_SOURCE_UNAVAILABLE`.
Invalid world or unreadable CLI input: `SPLAT_WORLD_INVALID` /
`SPLAT_WORLD_UNAVAILABLE`. Path traversal, absolute/drive/backslash paths and
resolved escapes fail as `SPLAT_PATH_INVALID` / `SPLAT_PATH_OUTSIDE_WORLD`.
This is local path validation, not a sandbox against a concurrent filesystem
attacker. Unsupported format, oversized data or changed hash fail as
`SPLAT_FORMAT_UNSUPPORTED`, `SPLAT_SIZE_LIMIT`, `SPLAT_SOURCE_CHANGED`.
Malformed records, nonfinite numbers, position/scale/rotation violations have
`SPLAT_RECORDS_INVALID`, `SPLAT_NUMBER_INVALID`, `SPLAT_POSITION_OUT_OF_RANGE`,
`SPLAT_SCALE_INVALID`, `SPLAT_ROTATION_INVALID` respectively.

The output directory and both files are exclusively created. Existing output
fails `SPLAT_EXPORT_EXISTS`; creation/write failures use
`SPLAT_EXPORT_UNAVAILABLE` / `SPLAT_EXPORT_WRITE_FAILED`. The manifest is written
last. A partial export is retained for inspection; this is not a crash-atomic
transaction. Consumers cannot treat presence of a manifest alone as completion.
Repeated exports to different fresh directories produce byte-identical bundles
for identical input. Existing bundles are never overwritten or deleted.

Multiverse upload authorization, curation, DataRightsService erasure, gallery
publication and browser rendering remain separate engineering work. No service
receives data through this command. Local/downloaded copies cannot be remotely
erased; users control their local files. Publishing must establish ownership and
erasure obligations before adding a gallery entry.

## Local proof

`python -m pytest tests/test_web_export.py` exercises authored binary records,
real temporary files, deterministic output, schema roundtrip, corrupt/oversized
inputs, missing/changed sources, path rejection, preservation and CLI failures.
These are filesystem/CLI checks, not browser, GPU, vendor, Postgres or Redis
integration coverage.

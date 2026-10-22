# Video content-safety gate

Video ingestion is a child-safety trust boundary. Before reconstruction sees a
user video, Terminalia samples eight deterministic, uniformly spaced frames and
requires every frame to receive an explicit safe verdict from a real moderation
model. Only opaque provider response IDs are retained; frames and provider
responses are not copied into `world.json`.

| Condition | Result |
|---|---|
| Every frame explicitly safe, with model provenance | proceed |
| Any frame unsafe | reject |
| Ambiguous, malformed, or empty response | reject |
| Decode, timeout, model-load, or service error | reject |
| No configured real model | reject every video |

## Providers

The default is OpenAI `omni-moderation-latest` over the Moderations REST API.
It accepts frame images and is governed by the OpenAI Services Agreement and
Usage Policies. Set `OPENAI_API_KEY` only in the environment where the ComfyUI
node runs.

The local/air-gapped path is NVIDIA `nemotron-3.5-content-safety`, the current
multimodal successor to the text-only Llama 3.1 Nemotron guard. Run its NIM and
set `NVIDIA_API_KEY`, or set `NEMOTRON_SAFETY_DIR` for an accepted local model
deployment (and optionally `NEMOTRON_SAFETY_URL`; default
`http://127.0.0.1:8000`). Its weights are governed by OpenMDW 1.1, Gemma Terms
of Use, and the Gemma Prohibited Use Policy; the NIM container has additional
NVIDIA software/product terms. No weights are redistributed.

The `TerminaliaContentSafety` custom node belongs in the ComfyUI installation
behind the selected `Backend`. Provider keys remain environment-only on that
machine. Calls use a 30-second timeout and at most two retries. Any exhausted
request becomes an unsafe verdict.

## Mock policy and founder actions

`TERMINALIA_SAFETY_MOCK=1` is test-only and must never be present in production.
Without that explicit value, the node cannot enter mock mode.

Every mock verdict, including safe, decode-error, and source-hash-mismatch
results, identifies `Terminalia safety mock` with `test-only; no moderation
model executed` provenance. It never names OpenAI or NVIDIA. Consequently
`has_real_provenance()` returns false and ingestion rejects even a safe mock
verdict before submitting reconstruction. This corrects the previous mock
path's misleading OpenAI identity.

The model-name/license check recognizes the configured provider vocabulary;
it is not cryptographic proof that a remote backend ran that provider. Eight
sampled frames also do not establish safety of every frame in a whole video.
Real reconstruction remains unimplemented in the bundled nodes; see
[video-ingestion.md](video-ingestion.md).

Before enabling video ingestion, Josh must:

1. Accept OpenAI's applicable agreement/policies and install `OPENAI_API_KEY`
   on each hosted safety-node runtime.
2. Decide whether to deploy the NVIDIA NIM fallback; if yes, accept OpenMDW,
   Gemma, and NVIDIA NIM terms, then install `NVIDIA_API_KEY` and the local NIM,
   or configure `NEMOTRON_SAFETY_DIR`/`NEMOTRON_SAFETY_URL`.
3. Attest that `TERMINALIA_SAFETY_MOCK` is absent from every production runtime.
4. Install OpenCV alongside the node and verify a known-safe and known-unsafe
   operational canary before accepting user video.

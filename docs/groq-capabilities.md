# Groq API Capabilities — Verified Facts

> All facts below were fetched live from the cited URLs. **Access date: 2026-10-24.**
> Re-verify before relying on these for a live training session — provider docs and pricing change.
> Numbers that could not be confirmed from a primary Groq source are explicitly marked **Unverified**.

## 1. Models (https://console.groq.com/docs/models, accessed 2026-10-24)

| Model ID | Context window | Max output tokens | Status |
|---|---|---|---|
| `openai/gpt-oss-20b` | 131,072 | 65,536 | Production |
| `openai/gpt-oss-120b` | 131,072 | 65,536 | Production |
| `openai/gpt-oss-safeguard-20b` | 131,072 | 65,536 | Preview (not for production) |
| `llama-3.1-8b-instant` | 131,072 | 131,072 | Production |
| `llama-3.3-70b-versatile` | 131,072 | 32,768 | Production |
| `qwen/qwen3.8-27b` | 131,072 | 16,384 | Preview |

**Project default model:** `openai/gpt-oss-20b` (131,072 context window, 65,536 max output, reasoning-capable, structured-outputs strict mode supported). Configurable everywhere via `config/*.toml`; never hardcoded in lab logic (per spec Section 4).

## 2. Structured Outputs (https://console.groq.com/docs/structured-outputs, accessed 2026-10-24)

- **JSON Object Mode** (`response_format: {"type": "json_object"}`): guarantees syntactically valid JSON only, not schema compliance. Works on all chat models. The prompt must describe the desired shape.
- **JSON Schema mode** (`response_format: {"type": "json_schema", "json_schema": {...}}`):
  - **Strict** (`strict: true`): constrained decoding; Groq's docs state it "never errors or produces invalid JSON" and guarantees full schema adherence (i.e., JSON-syntax + schema-structure validity — **not** semantic/business-logic correctness, which Lab 08 measures separately).
  - **Best-effort** (`strict: false`, default): valid JSON that generally follows the schema but can return malformed output or HTTP 400; retry logic recommended.
- **Models supporting strict mode:** `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `meta-models/muse-spark-open`. `openai/gpt-oss-20b` (our default model) supports it.
- **Schema constraints for strict mode** (binding for Lab 08's schema design):
  - Every property must appear in `required`. Optional fields are modeled as a union with `null` (`"type": ["string", "null"]`) and must still be listed in `required`.
  - Every object must set `additionalProperties: false`.
  - Supported types: string, number, boolean, integer, object, array, enum, `anyOf`.
  - `$defs` / `$ref` supported, including root and recursive refs.
  - **Unsupported:** streaming and tool-use cannot be combined with Structured Outputs.
  - Groq's own docs do not state a nesting-depth limit or give an exhaustive unsupported-keyword list ("a subset" of JSON Schema). Lab 08's schema is deliberately kept shallow (≤2 levels of nesting) and avoids any keyword not explicitly confirmed above (no `pattern`, `minLength`, `format`, conditional schemas, etc.) — see `docs/decisions.md`.

## 3. Reasoning (https://console.groq.com/docs/reasoning, accessed 2026-10-24)

- `reasoning_effort` accepted values and support:

  | Value | Supported on `gpt-oss-20b`/`gpt-oss-120b`? |
  |---|---|
  | `low` | Yes |
  | `medium` | Yes |
  | `high` | Yes |
  | `none` / `default` / `xhigh` | No (these are for Qwen3.8/Muse Spark Open only) |

- **Reasoning visibility for GPT-OSS models:** no `reasoning_format` parameter (that's for non-GPT-OSS models). Instead GPT-OSS models expose `include_reasoning` (default `true`); set `include_reasoning=false` to exclude reasoning text from the response. The project's Groq client adapter sets `include_reasoning=false` by default and, if a response ever contains a `reasoning` field anyway (e.g. parameter not honored by a given snapshot), discards it before persistence and records that it was discarded — see Section 8 "Groq Client Adapter" of the spec and Lab 07's rules.
- `include_reasoning` and `reasoning_format` are mutually exclusive — never send both.
- **Reasoning tokens in usage:** Groq's reasoning doc page does not state whether `completion_tokens_details.reasoning_tokens` is populated for GPT-OSS models. **Unverified** — the client adapter reads `completion_tokens_details.reasoning_tokens` defensively (via `getattr`, defaulting to `None`, never `0`) and the project treats it as present only if actually returned by a live call. No live call has been made in M0–M2 (no API key in this environment), so this remains unverified until an instructor runs a live smoke test (see `docs/live-smoke.md`).

## 4. Rate Limits (https://console.groq.com/docs/rate-limits, accessed 2026-10-24)

- Limit families: RPM, RPD, TPM, TPD (plus ASH/ASD for audio models; some accounts have separate ITPM/OTPM). Limits are per-organization; whichever threshold is hit first applies. Cached tokens do not count toward TPM/TPD.
- Example limit shown on the docs page for the base Developer plan: `openai/gpt-oss-120b` → 30 RPM / 1,000 RPD / 8,000 TPM / 200,000 TPD. The page states these are illustrative and the account's own limits page is authoritative — **this project does not hardcode a specific account's numeric limits**; `config/*.toml` exposes `rate_limit.requests_per_minute` / `rate_limit.tokens_per_minute` as operator-set values with no shipped default claiming to be "the" Groq limit.
- **Headers returned on every response:** `x-ratelimit-limit-requests`, `x-ratelimit-remaining-requests`, `x-ratelimit-reset-requests` (RPD family); `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-tokens`, `x-ratelimit-reset-tokens` (TPM family). The docs page does not show separate headers for RPM/TPD.
- **On HTTP 429:** a `retry-after` header (seconds) is included only on 429 responses; the client should wait at least that long before retrying. The rate limiter's backoff honors `retry-after` when present, falling back to configured exponential backoff + jitter otherwise.

## 5. Pricing

- **Source:** https://console.groq.com/docs/model/openai/gpt-oss/20b (accessed 2026-10-24) — a Groq-first-party page, fetched directly (not a third-party tracker).
- `openai/gpt-oss-20b`: **$0.075 / 1M input tokens**, **$0.30 / 1M output tokens**.
- **Cached-input pricing:** not stated on the fetched page. **Unverified** — recorded as `null` with reason `"not confirmed on primary source"` in `config/default.toml`'s pricing table; cost estimates that would depend on cached-token pricing fall back to treating cached tokens as priced at the regular input rate only when `cached_tokens` is itself reported (never fabricated), and the cost field is annotated accordingly.
- A general marketing page (`https://groq.com/pricing/`) was also checked and did not expose per-model numbers (rendered client-side); the per-model docs page above was used instead as the primary source.
- `verified_at = "2026-10-24"`, `source_url = "https://console.groq.com/docs/model/openai/gpt-oss/20b"` are recorded alongside the pricing values in `config/default.toml`.

## 6. Tokenizer for local estimation

- No offline `tiktoken` encoding is confirmed to match GPT-OSS's actual tokenizer (GPT-OSS uses a Harmony/o200k-family tokenizer per OpenAI's open release, not validated against Groq's hosted version in this environment — no network access to download/verify a matching `tiktoken` encoding was exercised here beyond the doc fetches above). The project therefore uses a conservative heuristic token estimator (`src/lab_core/tokens.py`): character-count/4 for English-like text and a Turkish-tuned divisor (empirically Turkish agglutinative text tends to tokenize slightly denser; the estimator uses ~3.3 chars/token for Turkish content, configurable), clearly labeled as an **estimate**, never used as a measured metric. Provider-reported `usage.prompt_tokens`/`usage.completion_tokens` are the only values ever recorded as measured token counts (Section 7 of the spec).

## 7. What remains unverified going into M1–M2

- Reasoning-token reporting for GPT-OSS models on Groq (no live call made).
- Cached-input price for `openai/gpt-oss-20b`.
- Exact RPM/RPD numeric limits for this project's own Groq account/tier (depends on the account used at training time, not on this research pass).
- Exhaustive strict-mode JSON Schema keyword support beyond what section 2 lists.

These are carried into `config/default.toml` as `null`/absent with explicit comments, and into the relevant labs' READMEs (Lab 07, Lab 08) as explicit "unverified — treat capability-dependent branches as `unsupported`, not failed" notes, per spec Section 4 and Section 13.

# Architecture & Design Decisions

Append-only log. Each entry: date, decision, rationale, alternatives considered.

## 2026-10-24 — Reference repository analysis

Both reference repositories were cloned and read directly (not guessed from memory):
- `https://github.com/Burakkylmz/llm-token-economics-lab` (primary reference)
- `https://github.com/Burakkylmz/llm-sampling-lab` (secondary reference)

**Adopted from `llm-token-economics-lab`:**
- The `src/lab_core/` + `src/labs/labNN_<name>/` split, with each lab exposing `LAB_ID` and a `register(subparsers)` function; the root CLI discovers labs by an **explicit hardcoded list** of module paths (not a filesystem scan), so a half-written lab directory is never picked up accidentally. We keep this pattern exactly — `src/lab_core/cli.py` hardcodes the 8 lab modules.
- The `--live` + `config.execution.live_api_enabled` double-gate pattern (`lab_cli_support.build_context`), including: `LiveExecutionNotAllowed` raised (not silently downgraded) when `--live` is passed without the config opt-in, and a cost-warning line printed before any live call. We extend this with the spec's additional requirement that the *fake client* is injected by default and the *real client's constructor itself* also refuses to build when live is not authorized (defense in depth at two layers, not just the CLI layer) — see `src/lab_core/groq_client.py`.
- `TokenCostMetrics`/`PerformanceMetrics`-style dataclasses that default every provider-reported numeric field to `None` and normalize defensively via `getattr`, never fabricating `0`. We carry this principle into `src/lab_core/metrics.py` and `src/lab_core/groq_client.py` verbatim as a design rule.
- TOML config loaded into a frozen dataclass tree with a `_require()` helper that raises `ConfigError` on missing keys. We generalize this into Pydantic models instead (spec Section 4 mandates Pydantic), which gives us "reject unknown keys" via `model_config = {"extra": "forbid"}` for free instead of hand-written presence checks — a direct improvement, not a deviation.
- Dockerfile shape: `uv sync --frozen --no-install-project` first (dependency layer caches independently of source changes), then copy source and `uv sync --frozen` again. Adopted as-is for `Dockerfile`, with the spec's additional requirement of a non-root user and `.gitattributes`-forced LF line endings for Windows/Docker Desktop compatibility.
- Exponential-backoff-with-jitter as a standalone, policy-free helper function (`compute_backoff_delay_seconds`), deliberately not auto-wired into the client, so retry behavior stays an explicit, testable decision at the call site. Adopted into `src/lab_core/rate_limiter.py`, extended to also honor a provider `retry-after` header when present (per spec Section 7).

**Adopted from `llm-sampling-lab`:**
- Fewer directly-reusable patterns (it is single-package rather than shared-core/multi-lab), but its `settings.toml` validation style (explicit per-section, per-field checks with descriptive `ValueError` messages) confirmed the value of fail-fast, explicit config validation, which we now get more cheaply via Pydantic validators.
- Its `tests/conftest.py`-style fake-client factories (a class that mimics only the attribute shape the production code actually reads, recording calls for assertions) is the model for this project's `FakeGroqClient` in `src/lab_core/fake_client.py`, extended to support **labeled fixture-file-driven** and **deterministic-rule-driven** responses (this project's fixture mode is richer than either reference repo's: it must serve a whole evaluation pipeline, not just return canned text).

**Changed, and why:**
- **Pydantic instead of hand-rolled dataclasses + `_require()`** for config (spec-mandated; also gives "reject unknown keys" and declarative range/type validation for free).
- **`jsonschema` for dataset/schema validation** — neither reference repo needed this (they don't validate structured datasets), so this is new, not a deviation from a prior pattern.
- **Three execution modes (fixture / replay / live) instead of two (simulated-flag / `--live`).** Neither reference repo has a replay mode. This is this project's architectural novelty per spec Section 2 and is designed fresh in `docs/architecture.md`.
- **Evaluation Engine, Statistics module (Wilson CI, bootstrap, McNemar, flips), Context Manager, Prompt Builder** are all new — the reference repos measure token/cost/latency/sampling behavior, not prompt-quality or context-engineering outcomes. This project's "Prompt Quality Evaluation Engine" is the other architectural novelty called out in spec Section 2.
- **argparse retained** (not Typer) to stay consistent with the reference repos' CLI style and avoid adding a dependency without clear value, per spec Section 4's "add other dependencies only with clear value" rule.

## 2026-10-24 — Dataset language

All dataset *content* (customer messages, policy documents, questions, lead messages, expense/leave cases) is written in **Turkish**, per spec Section 9.1. Code, field names, JSON keys, and all documentation in `docs/*.md` (except participant/instructor guides and per-lab READMEs) are English. This is a deliberate asymmetry: the training audience is Turkish-speaking, but the codebase must remain readable by anyone reviewing or maintaining it.

**Consequence recorded for later labs:** Turkish text is denser per token than English under BPE-style tokenizers (agglutinative morphology, diacritics) — this affects every token-budget calculation in Lab 04 (context budgets), Lab 05 (context-rot lengths), and Lab 06 (fixed-length filler). The local token estimator (`src/lab_core/tokens.py`) uses a Turkish-specific chars-per-token ratio for this reason (see `docs/groq-capabilities.md` Section 6), and all token-length *targets* in dataset generation are expressed as "generate until the estimator says length L," then corrected against **provider-reported** tokens once a live/replay run exists, never assumed equal to the English heuristic.

## 2026-10-24 — Pricing & capability verification

Pricing for `openai/gpt-oss-20b` ($0.075/1M input, $0.30/1M output) was confirmed directly from `https://console.groq.com/docs/model/openai/gpt-oss/20b` on 2026-10-24 — a first-party Groq page, fetched live, not a third-party tracker (the reference `llm-token-economics-lab` repo explicitly flagged its own pricing numbers as third-party-sourced and unconfirmed against Groq's own page; this project improves on that by using a confirmed first-party source for the default model). Cached-input pricing for this model was **not found** on the fetched page and is recorded as unverified (`null` + reason) rather than guessed or copied from a third-party tracker. See `docs/groq-capabilities.md` for the full capability/pricing verification record.

## 2026-10-24 — No dataset-minimum deviations in M0–M2

No deviation from the Section 9.2 minimum dataset sizes was needed for Lab 01 (the only lab built through the M2 checkpoint). Lab 01's dataset meets or exceeds: ≥60 eval messages, 5 classes, ≥12/class, ≥15% ambiguous/edge-case tagged, example pool ≥15. See `src/labs/lab01_prompt_anatomy/README.md` for the exact counts once generated, and `docs/verification-log.md` for the test that asserts class balance.

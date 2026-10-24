"""Lab 05's fixture-mode resolver: a deterministic, length-dependent degradation rule
(correct at short lengths, confused by the near-miss distractor at medium lengths, reports
"not found" at the longest length). This produces a measurable SIMULATED degradation curve
so the pipeline/report mechanics can be exercised and inspected — it is not a claim about
how a real model's accuracy actually degrades with length; that can only come from
`--replay` or `--live`.
"""

from __future__ import annotations

from lab_core.config import TokensConfig
from lab_core.experiment_runner import Case
from lab_core.fake_client import Resolver
from lab_core.groq_client import CompletionRequest
from lab_core.tokens import estimate_tokens

CORRECT_UP_TO_TOKENS = 5000
CONFUSED_UP_TO_TOKENS = 18000


def make_fixture_resolver(cases: list[Case], tokens_config: TokensConfig) -> Resolver:
    def resolve(request: CompletionRequest) -> str:
        user_text = request.messages[-1].content
        matched = next((c for c in cases if c.metadata["fact_sentence"] in user_text), None)
        if matched is None:
            return "CEVAP: BULUNAMADI"

        estimated_tokens = estimate_tokens(user_text, tokens_config)
        if estimated_tokens <= CORRECT_UP_TO_TOKENS:
            return f"CEVAP: {matched.expected['gold_answer']}"
        if estimated_tokens <= CONFUSED_UP_TO_TOKENS:
            return f"CEVAP: {matched.expected['near_miss_answer']}"
        return "CEVAP: BULUNAMADI"

    return resolve

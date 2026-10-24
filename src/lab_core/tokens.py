"""Local token-count *estimation* only.

Estimates are used for planning (pre-flight plans, budget-based context selection) and are
always labeled as estimates. They are never recorded as a measured token count — only the
Groq API's own `usage.prompt_tokens` / `usage.completion_tokens` are measured values
(spec Section 7). See docs/groq-capabilities.md Section 6 for why no exact tokenizer is used.
"""

from __future__ import annotations

from lab_core.config import TokensConfig


def estimate_tokens(text: str, tokens_config: TokensConfig, language: str = "tr") -> int:
    """Conservative heuristic estimate: character count / chars-per-token ratio.

    `language="tr"` uses the Turkish-tuned ratio (Turkish text tends to tokenize denser under
    BPE-style tokenizers); any other value uses the general-purpose default ratio.
    """
    if not text:
        return 0
    ratio = (
        tokens_config.turkish_chars_per_token
        if language == "tr"
        else tokens_config.default_chars_per_token
    )
    return max(1, round(len(text) / ratio))


def estimate_messages_tokens(
    messages: list[dict[str, str]], tokens_config: TokensConfig, language: str = "tr"
) -> int:
    """Estimate total tokens across a list of {"role", "content"} chat messages.

    Adds a small fixed per-message overhead (role/formatting tokens) to the content estimate;
    this constant is not independently verified against Groq's tokenizer (see
    docs/groq-capabilities.md) and exists only to avoid under-estimating multi-message prompts.
    """
    per_message_overhead = 4
    total = 0
    for message in messages:
        total += estimate_tokens(message.get("content", ""), tokens_config, language)
        total += per_message_overhead
    return total

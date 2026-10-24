from __future__ import annotations

from lab_core.config import TokensConfig
from lab_core.tokens import estimate_messages_tokens, estimate_tokens

CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def test_empty_text_is_zero_tokens():
    assert estimate_tokens("", CFG) == 0


def test_turkish_ratio_differs_from_default_ratio():
    text = "a" * 100
    turkish_estimate = estimate_tokens(text, CFG, language="tr")
    default_estimate = estimate_tokens(text, CFG, language="en")
    assert turkish_estimate != default_estimate
    assert turkish_estimate == round(100 / 3.3)
    assert default_estimate == round(100 / 4.0)


def test_estimate_is_never_zero_for_nonempty_text():
    assert estimate_tokens("a", CFG) >= 1


def test_messages_tokens_adds_overhead_per_message():
    messages = [{"role": "system", "content": "a" * 33}, {"role": "user", "content": "a" * 33}]
    single = estimate_tokens("a" * 33, CFG)
    total = estimate_messages_tokens(messages, CFG)
    assert total == 2 * single + 2 * 4

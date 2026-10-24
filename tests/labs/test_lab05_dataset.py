from __future__ import annotations

import pytest

from lab_core.config import TokensConfig
from lab_core.datasets import DatasetError
from labs.lab05_context_rot.data import MIN_FACTS, load_facts, load_filler

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def test_facts_meet_minimum_count():
    facts, _payload = load_facts()
    assert len(facts) >= MIN_FACTS


def test_filler_pool_reaches_32000_tokens_without_dataset_error():
    filler, near_miss_noise, _payload = load_filler(32000, TOKENS_CFG)
    assert len(filler) > 0
    assert isinstance(near_miss_noise, list)


def test_filler_pool_insufficient_for_absurd_length_raises():
    with pytest.raises(DatasetError):
        load_filler(10_000_000, TOKENS_CFG)


def test_fact_sentences_never_appear_in_filler_pool():
    facts, _payload = load_facts()
    filler, _near_miss, _payload2 = load_filler(1000, TOKENS_CFG)
    for fact in facts:
        assert fact.fact_sentence not in filler


def test_each_fact_has_distinct_gold_and_near_miss_answers():
    facts, _payload = load_facts()
    for fact in facts:
        assert fact.gold_answer != fact.near_miss_answer

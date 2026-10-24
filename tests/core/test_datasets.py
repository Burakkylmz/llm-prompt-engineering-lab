from __future__ import annotations

import pytest

from lab_core.datasets import (
    DatasetError,
    check_class_balance,
    check_leakage,
    edge_case_fraction,
    stratified_subset,
)


def _case(case_id, text, label, tags=None):
    return {
        "case_id": case_id,
        "text": text,
        "label": label,
        "priority": "low",
        "metadata": {
            "difficulty": "normal",
            "tags": tags or [],
            "source": "synthetic",
            "language": "tr",
        },
    }


def test_check_class_balance_passes_when_sufficient():
    cases = [_case(f"c{i}", f"metin {i}", "a") for i in range(5)] + [
        _case(f"d{i}", f"baska metin {i}", "b") for i in range(5)
    ]
    check_class_balance(cases, labels=["a", "b"], min_per_class=5)  # should not raise


def test_check_class_balance_raises_when_under_minimum():
    cases = [_case("c1", "metin", "a")]
    with pytest.raises(DatasetError):
        check_class_balance(cases, labels=["a", "b"], min_per_class=2)


def test_check_class_balance_raises_on_unknown_label():
    cases = [_case("c1", "metin", "unknown_label")]
    with pytest.raises(DatasetError):
        check_class_balance(cases, labels=["a"], min_per_class=1)


def test_check_leakage_detects_near_duplicate():
    eval_cases = [
        _case("e1", "Siparişim KE-1001 numaralı akıllı saat için iki kez çekim yapılmış", "billing")
    ]
    pool_cases = [
        _case(
            "p1", "Siparişim KE-1001 numaralı akıllı saat için iki kez tahsilat yapılmış", "billing"
        )
    ]
    leaks = check_leakage(eval_cases, pool_cases, threshold=0.5)
    assert len(leaks) == 1
    assert leaks[0][0] == "e1" and leaks[0][1] == "p1"


def test_check_leakage_empty_when_disjoint():
    eval_cases = [_case("e1", "Faturamda hata var ve düzeltme istiyorum", "billing")]
    pool_cases = [
        _case("p1", "Garanti süresi ne kadar acaba bilgi almak istiyorum", "general_inquiry")
    ]
    assert check_leakage(eval_cases, pool_cases, threshold=0.8) == []


def test_edge_case_fraction_counts_tagged_cases():
    cases = [_case("c1", "x", "a", tags=["edge_case"]), _case("c2", "y", "a", tags=[])]
    assert edge_case_fraction(cases) == 0.5


def test_edge_case_fraction_empty_list_is_zero():
    assert edge_case_fraction([]) == 0.0


def test_stratified_subset_balances_across_classes():
    items = [("a", i) for i in range(10)] + [("b", i) for i in range(10)]
    subset = stratified_subset(items, max_count=4, key_fn=lambda x: x[0])
    counts = {}
    for label, _ in subset:
        counts[label] = counts.get(label, 0) + 1
    assert len(subset) == 4
    assert counts == {"a": 2, "b": 2}


def test_stratified_subset_returns_all_when_max_count_exceeds_total():
    items = [("a", 1), ("b", 2)]
    assert stratified_subset(items, max_count=10, key_fn=lambda x: x[0]) == items


def test_stratified_subset_preserves_within_group_order():
    items = [("a", 1), ("a", 2), ("a", 3), ("b", 1)]
    subset = stratified_subset(items, max_count=3, key_fn=lambda x: x[0])
    a_items = [x for x in subset if x[0] == "a"]
    assert a_items == [("a", 1), ("a", 2)]


def test_stratified_subset_handles_unbalanced_groups():
    items = [("a", i) for i in range(2)] + [("b", i) for i in range(10)]
    subset = stratified_subset(items, max_count=6, key_fn=lambda x: x[0])
    counts = {}
    for label, _ in subset:
        counts[label] = counts.get(label, 0) + 1
    assert counts["a"] == 2  # group "a" exhausts after 2
    assert counts["b"] == 4
    assert len(subset) == 6


def test_stratified_subset_zero_max_count():
    items = [("a", 1)]
    assert stratified_subset(items, max_count=0, key_fn=lambda x: x[0]) == []

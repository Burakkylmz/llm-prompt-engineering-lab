"""Deterministic evaluation primitives shared across labs (spec Section 8).

No LLM-as-judge anywhere in this module or any lab's evaluator — every check here is code
that can be read, unit-tested on hand-built cases, and re-run identically in replay mode.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

# For matching purposes (not for display), fold all four Turkish I-like characters — dotted
# capital İ (U+0130), ASCII capital I (U+0049), dotless lowercase ı (U+0131), and dotted
# lowercase i (U+0069) — onto a single representative ("i") before the generic casefold.
# Python's default str.casefold() does NOT do this (it is Unicode-default, not Turkish-locale
# casefolding: casefold("İ") == "i̇" with a combining dot, which does NOT equal casefold("i")
# == "i"). Without this explicit map, "İptal" and "iptal" would compare as different
# normalized strings, which is wrong for this project's matching.
_TURKISH_FOLD_MAP = str.maketrans({"İ": "i", "I": "i", "ı": "i"})


def normalize_text_tr(text: str) -> str:
    """Casefold + Turkish İ/ı-aware + strip + collapse whitespace + strip punctuation.

    Used for comparing free-text model output against gold labels/values where exact
    Python str.casefold() would not treat Turkish dotted/dotless I the way a Turkish reader
    expects two spellings of the "same" word to match.
    """
    text = text.translate(_TURKISH_FOLD_MAP)
    text = text.casefold()
    text = "".join(ch for ch in text if not unicodedata.category(ch).startswith("P"))
    text = " ".join(text.split())
    return text.strip()


def closed_set_match(predicted: str, gold: str, normalize: bool = True) -> bool:
    if normalize:
        return normalize_text_tr(predicted) == normalize_text_tr(gold)
    return predicted == gold


@dataclass(frozen=True)
class EvaluationResult:
    """One case's evaluation outcome: a dict of independently-reportable named checks plus a
    single `primary_correct` flag used for accuracy/F1 roll-ups."""

    checks: dict[str, bool]
    primary_correct: bool
    parsed_label: str | None = None
    notes: dict[str, Any] = field(default_factory=dict)

    @property
    def all_checks_passed(self) -> bool:
        return all(self.checks.values())


@dataclass(frozen=True)
class ClassificationMetrics:
    accuracy: int
    n: int
    per_class_precision: dict[str, float]
    per_class_recall: dict[str, float]
    per_class_f1: dict[str, float]
    macro_f1: float
    confusion_matrix: dict[str, dict[str, int]]

    @property
    def accuracy_rate(self) -> float:
        return self.accuracy / self.n if self.n else 0.0


def classification_metrics(
    predictions: list[tuple[str, str]], labels: list[str]
) -> ClassificationMetrics:
    """`predictions` is a list of (predicted_label, gold_label) pairs. `labels` is the closed
    label set (used to report every class even if it never appears as a prediction)."""
    confusion: dict[str, dict[str, int]] = {gold: dict.fromkeys(labels, 0) for gold in labels}
    correct = 0
    for predicted, gold in predictions:
        if gold not in confusion:
            confusion[gold] = dict.fromkeys(labels, 0)
        if predicted not in confusion[gold]:
            confusion[gold][predicted] = 0
        confusion[gold][predicted] += 1
        if predicted == gold:
            correct += 1

    predicted_counts = Counter(p for p, _g in predictions)
    gold_counts = Counter(g for _p, g in predictions)

    precision: dict[str, float] = {}
    recall: dict[str, float] = {}
    f1: dict[str, float] = {}
    for label in labels:
        true_positive = confusion.get(label, {}).get(label, 0)
        predicted_total = predicted_counts.get(label, 0)
        gold_total = gold_counts.get(label, 0)
        precision[label] = true_positive / predicted_total if predicted_total else 0.0
        recall[label] = true_positive / gold_total if gold_total else 0.0
        f1[label] = (
            2 * precision[label] * recall[label] / (precision[label] + recall[label])
            if (precision[label] + recall[label]) > 0
            else 0.0
        )

    macro_f1 = sum(f1.values()) / len(labels) if labels else 0.0

    return ClassificationMetrics(
        accuracy=correct,
        n=len(predictions),
        per_class_precision=precision,
        per_class_recall=recall,
        per_class_f1=f1,
        macro_f1=macro_f1,
        confusion_matrix=confusion,
    )

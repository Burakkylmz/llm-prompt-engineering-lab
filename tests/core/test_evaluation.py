from __future__ import annotations

from lab_core.evaluation import classification_metrics, closed_set_match, normalize_text_tr


def test_normalize_handles_turkish_dotted_i():
    assert normalize_text_tr("İptal") == normalize_text_tr("iptal")


def test_normalize_handles_turkish_dotless_i():
    assert normalize_text_tr("Iptal") == normalize_text_tr("iptal")
    assert normalize_text_tr("ıptal") == normalize_text_tr("iptal")


def test_normalize_strips_punctuation_and_whitespace():
    assert normalize_text_tr("  Fatura,  sorunu! ") == normalize_text_tr("fatura sorunu")


def test_closed_set_match_case_insensitive():
    assert closed_set_match("BILLING", "billing")
    assert not closed_set_match("billing", "technical_issue")


def test_closed_set_match_exact_mode():
    assert not closed_set_match("BILLING", "billing", normalize=False)
    assert closed_set_match("billing", "billing", normalize=False)


def test_classification_metrics_perfect():
    predictions = [("a", "a"), ("b", "b"), ("c", "c")]
    metrics = classification_metrics(predictions, labels=["a", "b", "c"])
    assert metrics.accuracy_rate == 1.0
    assert metrics.macro_f1 == 1.0


def test_classification_metrics_confusion():
    predictions = [("a", "a"), ("b", "a"), ("b", "b")]
    metrics = classification_metrics(predictions, labels=["a", "b"])
    assert metrics.accuracy == 2
    assert metrics.n == 3
    assert metrics.confusion_matrix["a"]["a"] == 1
    assert metrics.confusion_matrix["a"]["b"] == 1
    # precision for "b": 1 true positive / 2 predicted as b = 0.5
    assert metrics.per_class_precision["b"] == 0.5
    # recall for "a": 1 true positive / 2 actual a = 0.5
    assert metrics.per_class_recall["a"] == 0.5


def test_classification_metrics_handles_unseen_label_gracefully():
    predictions = [("a", "a")]
    metrics = classification_metrics(predictions, labels=["a", "b"])
    assert metrics.per_class_precision["b"] == 0.0
    assert metrics.per_class_recall["b"] == 0.0

"""Loads and validates Lab 04's corpus + question set (spec Section 9.2: >=25 questions
with gold answers and gold evidence doc IDs; corpus >=40 documents including exact
duplicates, near-duplicates, irrelevant documents, >=8 old/new conflicting version pairs)."""

from __future__ import annotations

from pathlib import Path

from lab_core.context_manager import Document
from lab_core.datasets import DatasetError, load_json, validate_against_schema
from lab_core.experiment_runner import Case

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "golden" / "lab04"

MIN_QUESTIONS = 25
MIN_CORPUS_DOCS = 40
MIN_SUPERSEDED_PAIRS = 8


def load_corpus() -> tuple[list[Document], dict]:
    payload = load_json(DATA_DIR / "corpus.json")
    validate_against_schema(payload, "lab04_corpus.schema.json")

    if len(payload["documents"]) < MIN_CORPUS_DOCS:
        raise DatasetError(
            f"Lab04 corpus has {len(payload['documents'])} documents, minimum is {MIN_CORPUS_DOCS}"
        )
    superseded_pairs = sum(1 for d in payload["documents"] if d["superseded_by"])
    if superseded_pairs < MIN_SUPERSEDED_PAIRS:
        raise DatasetError(
            f"Lab04 corpus has {superseded_pairs} superseded pairs, "
            f"minimum is {MIN_SUPERSEDED_PAIRS}"
        )

    docs = [
        Document(
            doc_id=d["doc_id"],
            text=d["text"],
            effective_date=d["effective_date"],
            superseded_by=d["superseded_by"],
            tags=tuple(d["tags"]),
        )
        for d in payload["documents"]
    ]
    return docs, payload


def load_questions() -> tuple[list[Case], dict]:
    payload = load_json(DATA_DIR / "questions.json")
    validate_against_schema(payload, "lab04_questions.schema.json")

    if len(payload["questions"]) < MIN_QUESTIONS:
        raise DatasetError(
            f"Lab04 has {len(payload['questions'])} questions, minimum is {MIN_QUESTIONS}"
        )

    cases = [
        Case(
            case_id=q["question_id"],
            input_text=q["question"],
            expected={
                "gold_answer": q["gold_answer"],
                "gold_evidence_doc_ids": q["gold_evidence_doc_ids"],
                "stale_value": q["stale_value"],
                "stale_doc_id": q["stale_doc_id"],
            },
            metadata={"topic": q["topic"], "tags": q["metadata"]["tags"]},
        )
        for q in payload["questions"]
    ]
    return cases, payload

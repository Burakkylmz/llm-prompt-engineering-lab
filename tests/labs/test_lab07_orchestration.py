from __future__ import annotations

from lab_core.config import TokensConfig
from lab_core.fake_client import FakeGroqClient
from labs.lab07_task_decomposition.data import load_cases
from labs.lab07_task_decomposition.fixtures import make_fixture_resolver
from labs.lab07_task_decomposition.orchestration import (
    run_direct_answer,
    run_multi_call_decomposition,
    run_structured_single_call,
)
from labs.lab07_task_decomposition.parsing import parse_rule_outcomes
from labs.lab07_task_decomposition.policy import decision_from_outcomes

TOKENS_CFG = TokensConfig(turkish_chars_per_token=3.3, default_chars_per_token=4.0)


def _client_and_cases():
    cases, _payload = load_cases()
    client = FakeGroqClient(resolver=make_fixture_resolver(cases), tokens_config=TOKENS_CFG)
    return client, cases


def test_direct_answer_makes_exactly_one_call():
    client, cases = _client_and_cases()
    result = run_direct_answer(client, cases[0], "m", {})
    assert result.api_call_count == 1
    assert result.extracted_facts is None
    assert result.final_decision == cases[0].expected["gold_decision"]


def test_structured_single_call_produces_all_intermediate_fields_in_one_call():
    client, cases = _client_and_cases()
    result = run_structured_single_call(client, cases[0], "m", {})
    assert result.api_call_count == 1
    assert result.extracted_facts is not None
    assert result.applicable_rules is not None
    assert result.rule_outcomes is not None


def test_multi_call_decomposition_makes_exactly_four_calls():
    client, cases = _client_and_cases()
    result = run_multi_call_decomposition(client, cases[0], "m", {}, validate=False)
    assert result.api_call_count == 4
    assert result.validator_triggered is False


def test_multi_call_decomposition_correct_on_full_dataset():
    client, cases = _client_and_cases()
    for case in cases:
        result = run_multi_call_decomposition(client, case, "m", {}, validate=False)
        assert result.final_decision == case.expected["gold_decision"], case.case_id
        assert result.extracted_facts == case.expected["gold_facts"], case.case_id
        assert set(result.applicable_rules) == set(case.expected["gold_applicable_rules"]), (
            case.case_id
        )
        assert result.rule_outcomes == case.expected["gold_rule_outcomes"], case.case_id


def _resolver_wrong_once_then_correct(case):
    state = {"evaluate_calls": 0}

    def resolve(request):
        system_text = request.messages[0].content
        user_text = request.messages[1].content
        facts = case.expected["gold_facts"]

        if "su alanlari cikar" in system_text.lower():
            return (
                f"TUTAR: {facts['amount']} | KATEGORI: {facts['category']} | "
                f"FIS: {'var' if facts['has_receipt'] else 'yok'} | "
                f"ONAY: {'var' if facts['manager_preapproved'] else 'yok'}"
            )
        if "GECERLIDIR" in system_text:
            return f"GECERLI_KURALLAR: {','.join(case.expected['gold_applicable_rules'])}"
        if "PASS veya FAIL" in system_text:
            state["evaluate_calls"] += 1
            if state["evaluate_calls"] == 1:
                return "KURAL_SONUCLARI: category_check:fail"  # deliberately wrong
            outcomes = case.expected["gold_rule_outcomes"]
            return f"KURAL_SONUCLARI: {','.join(f'{k}:{v}' for k, v in outcomes.items())}"
        if "nihai karari ver" in system_text:
            outcomes = parse_rule_outcomes(user_text) or {}
            return f"KARAR: {decision_from_outcomes(outcomes)}"
        return "KARAR: escalate"

    return resolve, state


def test_validator_catches_wrong_rule_outcome_and_reasks_once():
    _client, cases = _client_and_cases()
    # Pick a case whose gold outcome isn't already {"category_check": "fail"} so the
    # deliberately-wrong first answer actually differs from gold and triggers the validator.
    case = next(c for c in cases if c.expected["gold_rule_outcomes"] != {"category_check": "fail"})

    resolver, state = _resolver_wrong_once_then_correct(case)
    client = FakeGroqClient(resolver=resolver, tokens_config=TOKENS_CFG)

    result = run_multi_call_decomposition(client, case, "m", {}, validate=True)

    assert result.validator_triggered is True
    assert state["evaluate_calls"] == 2  # exactly one re-ask, not more (bounded)
    assert result.rule_outcomes == case.expected["gold_rule_outcomes"]
    assert result.final_decision == case.expected["gold_decision"]
    assert result.api_call_count == 5  # 4 normal steps + 1 re-ask


def test_validator_not_triggered_when_model_is_already_correct():
    client, cases = _client_and_cases()
    case = cases[0]
    result = run_multi_call_decomposition(client, case, "m", {}, validate=True)
    assert result.validator_triggered is False
    assert result.api_call_count == 4

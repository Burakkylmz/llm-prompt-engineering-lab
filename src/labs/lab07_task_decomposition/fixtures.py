"""Lab 07's fixture-mode resolver: always computes the policy-correct answer at every step
(unlike Labs 02/05/06's deliberately-imperfect fixtures). Lab 07's point is to exercise the
multi-call orchestration and intermediate-accuracy measurement machinery correctly, not to
demonstrate a particular accuracy-degradation hypothesis — so a maximally-cooperative
simulated model is the more useful (and still clearly labeled SIMULATED) choice here.
"""

from __future__ import annotations

from lab_core.experiment_runner import Case
from lab_core.fake_client import Resolver
from lab_core.groq_client import CompletionRequest
from labs.lab07_task_decomposition.parsing import parse_facts, parse_rule_outcomes
from labs.lab07_task_decomposition.policy import applicable_rules, decision_from_outcomes
from labs.lab07_task_decomposition.policy import rule_outcomes as compute_rule_outcomes


def make_fixture_resolver(cases: list[Case]) -> Resolver:
    cases_by_description = {case.input_text: case for case in cases}

    def resolve(request: CompletionRequest) -> str:
        system_text = request.messages[0].content
        user_text = request.messages[1].content

        if (
            "nihai karari ver." in system_text
            and "SIRAYLA" not in system_text
            and "cikar" not in system_text.lower()
        ):
            # DIRECT_SYSTEM or DECIDE_SYSTEM: distinguish by whether the user turn is the
            # raw case description (direct) or a rule-outcomes summary (decide).
            if user_text in cases_by_description:
                case = cases_by_description[user_text]
                return f"KARAR: {case.expected['gold_decision']}"
            outcomes = parse_rule_outcomes(user_text) or {}
            return f"KARAR: {decision_from_outcomes(outcomes)}"

        if "SIRAYLA" in system_text:  # structured single call
            case = cases_by_description.get(user_text)
            if case is None:
                return "KARAR: escalate"
            facts = case.expected["gold_facts"]
            rules = case.expected["gold_applicable_rules"]
            outcomes = case.expected["gold_rule_outcomes"]
            return (
                f"TUTAR: {facts['amount']} | KATEGORI: {facts['category']} | "
                f"FIS: {'var' if facts['has_receipt'] else 'yok'} | "
                f"ONAY: {'var' if facts['manager_preapproved'] else 'yok'} | "
                f"GECERLI_KURALLAR: {','.join(rules)} | "
                f"KURAL_SONUCLARI: {','.join(f'{k}:{v}' for k, v in outcomes.items())} | "
                f"KARAR: {case.expected['gold_decision']}"
            )

        if "su alanlari cikar" in system_text.lower():  # extract facts
            case = cases_by_description.get(user_text)
            if case is None:
                return "TUTAR: 0 | KATEGORI: bilinmiyor | FIS: yok | ONAY: yok"
            facts = case.expected["gold_facts"]
            return (
                f"TUTAR: {facts['amount']} | KATEGORI: {facts['category']} | "
                f"FIS: {'var' if facts['has_receipt'] else 'yok'} | "
                f"ONAY: {'var' if facts['manager_preapproved'] else 'yok'}"
            )

        if "GECERLIDIR" in system_text:  # determine applicable rules
            facts = parse_facts(user_text)
            if facts is None:
                return "GECERLI_KURALLAR: category_check"
            rules = applicable_rules(facts["amount"], facts["category"])
            return f"GECERLI_KURALLAR: {','.join(rules)}"

        if "PASS veya FAIL" in system_text:  # evaluate rules (and re-validation re-ask)
            facts = parse_facts(user_text)
            if facts is None:
                return "KURAL_SONUCLARI: category_check:fail"
            outcomes = compute_rule_outcomes(
                facts["amount"],
                facts["category"],
                facts["has_receipt"],
                facts["manager_preapproved"],
            )
            return f"KURAL_SONUCLARI: {','.join(f'{k}:{v}' for k, v in outcomes.items())}"

        return "KARAR: escalate"

    return resolve

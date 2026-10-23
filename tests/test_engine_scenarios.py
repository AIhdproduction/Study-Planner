"""Definition-of-done scenarios, all using the invented synthetic profile."""

from studyplan.engine import evaluate
from studyplan.models import CreditAttempt, CreditsFile, RecognizedCredit, Rule, SourceReference
from tests.engine_support import checklist, credit, credits, plan, program, student


def _result(data: CreditsFile, *, rules=None, planned=None):
    base = program()
    return evaluate(
        base.model_copy(update={"rules": rules or base.rules}),
        student(),
        data,
        planned or plan(),
        checklist("manual_note"),
        "forecast" if planned else "current",
    )


def _with_parameters(rule: Rule, parameters: dict[str, object]) -> Rule:
    return Rule.model_validate({**rule.model_dump(), "parameters": parameters})


def test_scenario_1_category_gap() -> None:
    result = _result(
        credits(
            credit("SYN.CORE1"), credit("SYN.CORE2"), credit("SYN.PROJECT1"), credit("SYN.RELATED1")
        )
    )
    assert any("category" in gap["text"] for gap in result.gaps)


def test_scenario_2_flexible_module_fills_short_category() -> None:
    rules = [rule for rule in program().rules if rule.id in {"project_min"}]
    result = _result(credits(credit("SYN.CORE2")), rules=rules)
    assert result.category_ects["project"] == 3


def test_scenario_3_category_cap() -> None:
    result = _result(credits(credit("SYN.CORE1"), credit("SYN.ADVANCED"), credit("SYN.RENAMED")))
    assert result.category_ects["core"] == 6


def test_scenario_4_second_alternative() -> None:
    assert (
        next(
            rule for rule in _result(credits(credit("SYN.ALT_B"))).rules if rule.id == "alternative"
        ).status
        == "fulfilled"
    )


def test_scenario_5_failed_attempt_limit() -> None:
    data = credits(*(credit("SYN.CORE1", passed=False, attempt=value) for value in range(1, 4)))
    assert (
        next(rule for rule in _result(data).rules if rule.id == "attempts").status
        == "not_fulfilled"
    )


def test_scenario_6_recognized_forced_category() -> None:
    recognition = RecognizedCredit(
        id="r1",
        ects=3,
        basis="synthetic basis",
        category_id="related",
        decision_document=SourceReference(document="synthetic"),
        status="confirmed",
    )
    result = _result(CreditsFile(recognized_credits=[recognition]))
    assert result.category_ects["related"] == 3


def test_scenario_7_unverified_rule_is_provisional() -> None:
    base = program()
    total = next(rule for rule in base.rules if rule.id == "total").model_copy(
        update={"verification_status": "unverified"}
    )
    data = credits(
        credit("SYN.CORE1"), credit("SYN.CORE2"), credit("SYN.PROJECT1"), credit("SYN.RELATED1")
    )
    assert _result(data, rules=[total]).rules[0].status == "provisional"


def test_scenario_8_forecast_closes_gaps() -> None:
    base = program()
    total = next(rule for rule in base.rules if rule.id == "total")
    goal = _with_parameters(
        next(rule for rule in base.rules if rule.id == "graduation"),
        {"type": "composite", "operator": "and", "rule_ids": ["total"]},
    )
    rules = [total, goal]
    current = _result(credits(credit("SYN.CORE1")), rules=rules)
    forecast = _result(
        credits(credit("SYN.CORE1")),
        rules=rules,
        planned=plan(("SYN.CORE2", "FS00"), ("SYN.PROJECT1", "HS00"), ("SYN.RELATED1", "FS01")),
    )
    assert current.verdict == "not_eligible" and forecast.verdict == "eligible"


def test_scenario_9_predecessor_code_counts() -> None:
    old = CreditAttempt(
        module_code="SYN.OLD",
        semester="HS99",
        ects=3,
        grade="B",
        passed=True,
        attempt=1,
        source=SourceReference(document="synthetic"),
        verification_status="verified",
    )
    required = _with_parameters(
        next(rule for rule in program().rules if rule.id == "required"),
        {"type": "required_module", "module_code": "SYN.RENAMED"},
    )
    assert _result(CreditsFile(credits=[old]), rules=[required]).rules[0].status == "fulfilled"


def test_scenario_10_level_gate_timing() -> None:
    result = _result(
        credits(
            credit("SYN.ADVANCED", "HS99"), credit("SYN.CORE1", "FS00"), credit("SYN.CORE2", "FS00")
        )
    )
    assert next(rule for rule in result.rules if rule.id == "gate").status == "not_fulfilled"


def test_scenario_11_level_deadline() -> None:
    result = _result(credits(credit("SYN.PROJECT1", "HS00")))
    assert next(rule for rule in result.rules if rule.id == "deadline").status == "not_fulfilled"


def test_scenario_12_retake_budget() -> None:
    result = _result(credits(credit("SYN.ADVANCED", attempt=3)))
    assert next(rule for rule in result.rules if rule.id == "retake").status == "not_fulfilled"


def test_scenario_13_recognition_excluded_from_institution_ects() -> None:
    recognition = RecognizedCredit(
        id="r1",
        ects=9,
        basis="synthetic basis",
        decision_document=SourceReference(document="synthetic"),
        status="confirmed",
    )
    result = _result(CreditsFile(recognized_credits=[recognition]))
    assert next(rule for rule in result.rules if rule.id == "at_institution").current_value == 0


def test_scenario_14_interruptions_excluded_from_duration() -> None:
    base = program()
    duration = _with_parameters(
        next(rule for rule in base.rules if rule.id == "duration"),
        {
            "type": "max_study_duration",
            "maximum_semesters": 2,
            "maximum_interruptions": 2,
        },
    )
    result = evaluate(
        base.model_copy(update={"rules": [duration]}),
        student(interruptions=["FS00", "HS00"]),
        credits(credit("SYN.CORE1", "HS00")),
        plan(),
        checklist(),
        "current",
    )
    assert result.rules[0].status == "fulfilled"


def test_scenario_15_mandatory_only_blocks_graduation() -> None:
    base = program()
    thesis = _with_parameters(
        next(rule for rule in base.rules if rule.id == "thesis_admission"),
        {"type": "composite", "operator": "and", "rule_ids": ["total"]},
    )
    total = next(rule for rule in base.rules if rule.id == "total")
    mandatory = next(rule for rule in base.rules if rule.id == "mandatory")
    graduation = _with_parameters(
        next(rule for rule in base.rules if rule.id == "graduation"),
        {"type": "composite", "operator": "and", "rule_ids": ["total", "mandatory"]},
    )
    data = credits(
        credit("SYN.CORE1"), credit("SYN.CORE2"), credit("SYN.RELATED1"), credit("SYN.MINOR1")
    )
    result = _result(data, rules=[total, mandatory, thesis, graduation])
    assert {goal.id: goal.verdict for goal in result.goals} == {
        "thesis_admission": "eligible",
        "graduation": "not_eligible",
    }


def test_scenario_17b_lump_sum_recognition() -> None:
    recognition = RecognizedCredit(
        id="r1",
        ects=6,
        basis="synthetic basis",
        category_id="minor",
        decision_document=SourceReference(document="synthetic"),
        status="confirmed",
    )
    result = _result(CreditsFile(recognized_credits=[recognition]))
    assert result.total_ects == 6 and result.category_ects["minor"] == 6
    assert next(rule for rule in result.rules if rule.id == "at_institution").current_value == 0


def test_provisional_recognition_without_category() -> None:
    recognition = RecognizedCredit(
        id="r1",
        ects=3,
        basis="synthetic basis",
        decision_document=SourceReference(document="synthetic"),
        status="provisional",
    )
    result = _result(
        CreditsFile(recognized_credits=[recognition]),
        rules=[next(rule for rule in program().rules if rule.id == "total")],
    )
    assert result.rules[0].status == "not_fulfilled"
    full = _result(
        CreditsFile(
            recognized_credits=[recognition, recognition.model_copy(update={"id": "r2", "ects": 9})]
        ),
        rules=[next(rule for rule in program().rules if rule.id == "total")],
    )
    assert full.rules[0].status == "provisional"

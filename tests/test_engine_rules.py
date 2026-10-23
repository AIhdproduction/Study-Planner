"""One fulfilled and one failing assertion for every supported rule type."""

from studyplan.engine import evaluate
from studyplan.models import CreditsFile, RecognizedCredit, SourceReference
from tests.engine_support import checklist, credit, credits, plan, program, student


def _status(rule_id: str, data: CreditsFile, *, planned=None, checks=None) -> str:
    base = program()
    selected = next(rule for rule in base.rules if rule.id == rule_id)
    result = evaluate(
        base.model_copy(update={"rules": [selected]}),
        student(),
        data,
        planned or plan(),
        checks or checklist(),
        "forecast" if planned else "current",
    )
    return result.rules[0].status


def test_min_ects_total_rule() -> None:
    assert (
        _status(
            "total",
            credits(
                credit("SYN.CORE1"),
                credit("SYN.CORE2"),
                credit("SYN.PROJECT1"),
                credit("SYN.RELATED1"),
            ),
        )
        == "fulfilled"
    )
    assert _status("total", credits(credit("SYN.CORE1"))) == "not_fulfilled"


def test_min_ects_in_category_rule() -> None:
    assert _status("core_min", credits(credit("SYN.CORE1"))) == "fulfilled"
    assert _status("core_min", credits()) == "not_fulfilled"


def test_max_ects_in_category_rule() -> None:
    assert _status("core_cap", credits(credit("SYN.CORE1"))) == "fulfilled"
    assert (
        _status(
            "core_cap", credits(credit("SYN.CORE1"), credit("SYN.ADVANCED"), credit("SYN.RENAMED"))
        )
        == "fulfilled"
    )


def test_required_module_rule() -> None:
    assert _status("required", credits(credit("SYN.CORE1"))) == "fulfilled"
    assert _status("required", credits()) == "not_fulfilled"


def test_required_all_mandatory_rule() -> None:
    complete = credits(credit("SYN.CORE1"), credit("SYN.CORE2"), credit("SYN.PROJECT1"))
    assert _status("mandatory", complete) == "fulfilled"
    assert _status("mandatory", credits(credit("SYN.CORE1"))) == "not_fulfilled"


def test_required_one_of_rule() -> None:
    assert _status("alternative", credits(credit("SYN.ALT_B"))) == "fulfilled"
    assert _status("alternative", credits()) == "not_fulfilled"


def test_min_modules_in_category_rule() -> None:
    assert _status("module_count", credits(credit("SYN.MINOR1"))) == "fulfilled"
    assert _status("module_count", credits()) == "not_fulfilled"


def test_prerequisite_rule() -> None:
    passed = credits(credit("SYN.CORE1", "HS99"), credit("SYN.ADVANCED", "FS00"))
    assert _status("prerequisite", passed) == "fulfilled"
    assert _status("prerequisite", credits(credit("SYN.ADVANCED"))) == "not_fulfilled"


def test_max_attempts_rule() -> None:
    assert _status("attempts", credits(credit("SYN.CORE1", passed=False, attempt=1))) == "fulfilled"
    failed = credits(*(credit("SYN.CORE1", passed=False, attempt=index) for index in range(1, 4)))
    assert _status("attempts", failed) == "not_fulfilled"


def test_retake_budget_rule() -> None:
    assert _status("retake", credits(credit("SYN.CORE1", attempt=3))) == "fulfilled"
    assert _status("retake", credits(credit("SYN.ADVANCED", attempt=3))) == "not_fulfilled"


def test_level_gate_rule() -> None:
    passed = credits(credit("SYN.CORE1"), credit("SYN.CORE2"), credit("SYN.ADVANCED", "FS00"))
    assert _status("gate", passed) == "fulfilled"
    assert _status("gate", credits(credit("SYN.ADVANCED"))) == "not_fulfilled"


def test_level_deadline_rule() -> None:
    passed = credits(credit("SYN.CORE1"), credit("SYN.CORE2"), credit("SYN.PROJECT1", "HS00"))
    assert _status("deadline", passed) == "fulfilled"
    late = credits(credit("SYN.PROJECT1", "HS00"))
    assert _status("deadline", late) == "not_fulfilled"


def test_min_ects_at_institution_rule() -> None:
    data = credits(credit("SYN.CORE1"), credit("SYN.CORE2"), credit("SYN.PROJECT1"))
    assert _status("at_institution", data) == "fulfilled"
    assert _status("at_institution", credits(credit("SYN.CORE1"))) == "not_fulfilled"


def test_max_recognized_ects_rule() -> None:
    recognised = RecognizedCredit(
        id="r1",
        ects=6,
        basis="synthetic basis",
        decision_document=SourceReference(document="synthetic"),
        status="confirmed",
    )
    assert _status("recognition_cap", CreditsFile(recognized_credits=[recognised])) == "fulfilled"
    too_many = recognised.model_copy(update={"ects": 9})
    assert _status("recognition_cap", CreditsFile(recognized_credits=[too_many])) == "not_fulfilled"


def test_max_study_duration_rule() -> None:
    assert _status("duration", credits(credit("SYN.CORE1", "HS02"))) == "fulfilled"
    assert _status("duration", credits(credit("SYN.CORE1", "FS04"))) == "not_fulfilled"


def test_composite_rule() -> None:
    base = program()
    selected = [
        rule for rule in base.rules if rule.id in {"total", "manual_note", "thesis_admission"}
    ]
    complete = credits(
        credit("SYN.CORE1"), credit("SYN.CORE2"), credit("SYN.PROJECT1"), credit("SYN.RELATED1")
    )
    result = evaluate(
        base.model_copy(update={"rules": selected}),
        student(),
        complete,
        plan(),
        checklist("manual_note"),
        "current",
    )
    assert result.rules[-1].status == "fulfilled"
    result = evaluate(
        base.model_copy(update={"rules": selected}),
        student(),
        credits(),
        plan(),
        checklist(),
        "current",
    )
    assert result.rules[-1].status == "manual"


def test_custom_note_rule() -> None:
    assert _status("manual_note", credits(), checks=checklist("manual_note")) == "fulfilled"
    assert _status("manual_note", credits()) == "manual"

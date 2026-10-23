from studyplan.engine import evaluate
from tests.engine_support import checklist, credit, credits, plan, program, student


def _allocation(*codes: str):
    result = evaluate(
        program(),
        student(),
        credits(*(credit(code) for code in codes)),
        plan(),
        checklist(),
        "current",
    )
    return [
        (item.module_code, item.allocated_category_id, item.ects_counted)
        for item in result.allocation
    ]


def test_solver_is_deterministic() -> None:
    assert _allocation("SYN.CORE1", "SYN.CORE2", "SYN.PROJECT1") == _allocation(
        "SYN.CORE1", "SYN.CORE2", "SYN.PROJECT1"
    )


def test_forced_category_is_respected() -> None:
    item = credit("SYN.CORE2", forced_category_id="project")
    result = evaluate(program(), student(), credits(item), plan(), checklist(), "current")
    assert result.allocation[0].allocated_category_id == "project"


def test_category_cap_limits_counted_ects() -> None:
    result = evaluate(
        program(),
        student(),
        credits(credit("SYN.CORE1"), credit("SYN.ADVANCED"), credit("SYN.RENAMED")),
        plan(),
        checklist(),
        "current",
    )
    assert result.category_ects["core"] == 6


def test_module_is_counted_once() -> None:
    allocation = _allocation("SYN.CORE2")
    assert sum(ects for code, _category, ects in allocation if code == "SYN.CORE2") == 3

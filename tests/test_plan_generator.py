"""Deterministic semester-plan generation tests."""

from __future__ import annotations

from studyplan.engine.plan import generate_plan, plan_report, semester_for_relative, semester_key
from studyplan.models import (
    CreditsFile,
    PlanFile,
    PlanItem,
    RecognizedCredit,
    Semester,
    SourceReference,
)

from .engine_support import checklist, credit, credits, program, student


def _generate(now: str, existing: PlanFile | None = None, *items):
    return generate_plan(
        program(), student(), credits(*items), existing or PlanFile(), checklist(), now
    )


def test_calendar_mapping_for_hs_and_fs_starts() -> None:
    assert str(semester_for_relative("HS99", 2)) == "FS00"
    assert str(semester_for_relative("FS99", 2)) == "HS99"


def test_retake_uses_next_matching_offering_term() -> None:
    plan, _ = _generate("HS00", None, credit("SYN.CORE2", "FS00", passed=False))
    retake = next(
        item
        for item in plan.planned_modules
        if item.module_code == "SYN.CORE2" and item.status == "retake"
    )
    assert str(retake.target_semester) == "FS01"


def test_past_recommended_semester_moves_to_next_offering() -> None:
    plan, _ = _generate("HS01")
    core = next(item for item in plan.planned_modules if item.module_code == "SYN.CORE1")
    assert str(core.target_semester) == "HS01"


def test_level_gate_shifts_advanced_module_after_basic_retake() -> None:
    plan, _ = _generate("HS00", None, credit("SYN.CORE2", "FS00", passed=False))
    thesis = next(item for item in plan.planned_modules if item.module_code == "SYN.BAA")
    assert str(thesis.target_semester) == "FS02"


def test_basic_deadline_violation_is_reported() -> None:
    _, warnings = _generate("HS03")
    assert any("Basic deadline violated" in warning for warning in warnings)


def test_thesis_waits_for_forecast_threshold() -> None:
    existing = PlanFile(
        planned_modules=[
            PlanItem(
                module_code="SYN.RELATED1",
                target_semester="HS00",
                status="planned",
                origin="manual",
            )
        ]
    )
    plan, _ = _generate("HS99", existing)
    thesis = next(item for item in plan.planned_modules if item.module_code == "SYN.BAA")
    assert str(thesis.target_semester) == "FS01"


def test_elective_gap_creates_placeholder_with_recommended_suggestion() -> None:
    plan, _ = _generate("HS99")
    related = next(item for item in plan.placeholders if item.category_id == "related")
    assert related.suggested_module_codes[0] == "SYN.RELATED1"


def test_manual_items_survive_generation_and_force() -> None:
    existing = PlanFile(
        planned_modules=[
            PlanItem(
                module_code="SYN.RELATED1",
                target_semester="HS01",
                status="planned",
                origin="manual",
            )
        ]
    )
    merged, _ = _generate("HS99", existing)
    forced, _ = generate_plan(program(), student(), credits(), existing, checklist(), "HS99", True)
    assert any(
        item.origin == "manual" and item.module_code == "SYN.RELATED1"
        for item in merged.planned_modules
    )
    assert any(
        item.origin == "manual" and item.module_code == "SYN.RELATED1"
        for item in forced.planned_modules
    )


def test_running_credit_items_survive_generation_without_duplicate() -> None:
    existing = PlanFile(
        planned_modules=[
            PlanItem(
                module_code="SYN.RELATED1",
                target_semester="HS00",
                status="running",
                origin="credits",
            )
        ]
    )
    plan, _ = _generate("HS99", existing)
    running = [item for item in plan.planned_modules if item.module_code == "SYN.RELATED1"]
    assert len(running) == 1 and running[0].status == "running" and running[0].origin == "credits"


def test_recognized_credits_count_from_start_semester() -> None:
    recognized = RecognizedCredit(
        id="recognized-related",
        category_id="related",
        ects=3,
        basis="synthetic",
        decision_document=SourceReference(document="recognition.pdf"),
        status="provisional",
    )
    store = CreditsFile(recognized_credits=[recognized])
    plan, _ = generate_plan(program(), student(), store, PlanFile(), checklist(), "HS99")
    report = plan_report(program(), student(), store, plan, checklist())
    assert report["semesters"]["HS99"]["cumulative_ects"] >= 3
    assert report["semesters"]["HS99"]["items"][0]["status"] == "recognized"


def test_thesis_never_exceeds_maximum_duration() -> None:
    selected = program()
    plan, _ = generate_plan(selected, student(), credits(), PlanFile(), checklist(), "HS05")
    latest = max((item.target_semester for item in plan.planned_modules), key=semester_key)
    assert latest.sort_key <= Semester("FS05").sort_key


def test_placeholders_count_as_planned_ects_in_report() -> None:
    plan, _ = _generate("HS99")
    report = plan_report(program(), student(), credits(), plan, checklist())
    placeholder = plan.placeholders[0]
    semester = report["semesters"][str(placeholder.target_semester)]
    assert any(item["status"] == "placeholder" for item in semester["items"])
    assert semester["planned_ects"] >= placeholder.ects_needed


def test_offering_term_history_does_not_raise_warning() -> None:
    historical = PlanFile(
        planned_modules=[
            PlanItem(
                module_code="SYN.CORE1",
                target_semester="FS00",
                status="passed",
                origin="credits",
            )
        ]
    )
    report = plan_report(program(), student(), credits(), historical, checklist())
    assert not report["violations"]


def test_placeholder_chunks_do_not_exceed_the_model_semester_load() -> None:
    selected = program()
    plan, _ = _generate("HS99")
    report = plan_report(selected, student(), credits(), plan, checklist())
    modules = {module.code: module.ects for module in selected.modules}
    entries = selected.model_timetables["part_time"]["HS"]
    limit = max(
        sum(
            modules.get(entry.module_code, 0)
            for entry in entries
            if entry.relative_semester == number
        )
        for number in range(1, 5)
    )
    assert max(row["planned_ects"] for row in report["semesters"].values()) <= limit


def test_placeholders_never_in_past_or_current_semester() -> None:
    now = "HS00"
    plan, _ = _generate(
        now,
        None,
        credit("SYN.CORE1", "HS99", passed=True),
        credit("SYN.CORE2", "FS00", passed=False),
    )
    thesis = next(item for item in plan.planned_modules if item.module_code == "SYN.BAA")
    assert plan.placeholders
    for placeholder in plan.placeholders:
        assert semester_key(placeholder.target_semester) > semester_key(now)
        assert semester_key(placeholder.target_semester) < semester_key(thesis.target_semester)
    assert not any(semester_key(p.target_semester) <= semester_key(now) for p in plan.placeholders)
    assert not any(
        semester_key(p.target_semester) >= semester_key(thesis.target_semester)
        for p in plan.placeholders
    )


def test_placeholders_use_calendar_semesters_without_items() -> None:
    existing = PlanFile(
        planned_modules=[
            PlanItem(
                module_code="SYN.BAA",
                target_semester="FS02",
                status="planned",
                origin="manual",
            )
        ]
    )
    plan, _ = _generate(
        "HS00",
        existing,
        credit("SYN.CORE1", "HS99", passed=True),
        credit("SYN.CORE2", "FS00", passed=True),
        credit("SYN.PROJECT1", "HS00", passed=True),
    )
    assert not any(item.target_semester == "FS01" for item in plan.planned_modules)
    assert any(placeholder.target_semester == "FS01" for placeholder in plan.placeholders)
    report = plan_report(program(), student(), credits(), plan, checklist())
    assert "FS01" in report["semesters"]
    assert any(item["status"] == "placeholder" for item in report["semesters"]["FS01"]["items"])
    assert report["semesters"]["FS01"]["planned_ects"] == 3

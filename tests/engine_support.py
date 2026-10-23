"""Shared invented data builders for rule-engine tests."""

from __future__ import annotations

from pathlib import Path

from studyplan.io import ProfileRepository
from studyplan.models import (
    ChecklistFile,
    ChecklistItem,
    CreditAttempt,
    CreditsFile,
    PlanFile,
    PlanItem,
    SourceReference,
    StudentProfile,
)

PROFILES = Path("tests/fixtures/synthetic/profiles")


def program():
    return ProfileRepository(PROFILES).program("synthetic_u", "synthetic_program_2099")


def student(*, interruptions: list[str] | None = None) -> StudentProfile:
    return StudentProfile(
        university_id="synthetic_u",
        program_id="synthetic_program_2099",
        intake_year=2099,
        study_mode="part_time",
        start_semester="HS99",
        regulation_version_id="synthetic_2099",
        language="en",
        interruption_semesters=interruptions or [],
    )


def credit(
    code: str,
    semester: str = "HS99",
    *,
    passed: bool = True,
    attempt: int = 1,
    forced_category_id: str | None = None,
    mapping_verification_status: str | None = None,
) -> CreditAttempt:
    module = next(item for item in program().modules if item.code == code)
    return CreditAttempt(
        module_code=code,
        semester=semester,
        ects=module.ects,
        grade="B" if passed else "F",
        passed=passed,
        attempt=attempt,
        forced_category_id=forced_category_id,
        source=SourceReference(document="synthetic-source"),
        verification_status="verified",
        mapping_verification_status=mapping_verification_status,
    )


def credits(*items: CreditAttempt) -> CreditsFile:
    return CreditsFile(credits=list(items))


def plan(*codes: tuple[str, str]) -> PlanFile:
    return PlanFile(
        planned_modules=[
            PlanItem(module_code=code, target_semester=semester, status="planned")
            for code, semester in codes
        ]
    )


def checklist(*checked_ids: str) -> ChecklistFile:
    return ChecklistFile(
        items=[ChecklistItem(rule_id=rule_id, checked=True) for rule_id in checked_ids]
    )

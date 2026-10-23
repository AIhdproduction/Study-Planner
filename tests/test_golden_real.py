from pathlib import Path

import pytest
from ruamel.yaml import YAML

from studyplan.engine import evaluate
from studyplan.io import ProfileRepository
from studyplan.models import (
    ChecklistFile,
    CreditAttempt,
    CreditsFile,
    PlanFile,
    PlanItem,
    RecognizedCredit,
    SourceReference,
    StudentProfile,
)


@pytest.mark.real
def test_golden_real_fixture_matches_verdicts_and_missing_items() -> None:
    path = Path("tests/fixtures/real/golden.yaml")
    if not path.exists():
        pytest.skip("Private golden fixture is unavailable.")
    data = YAML(typ="safe").load(path)
    profile_data = data["profile"]
    repository = ProfileRepository(Path("profiles"))
    program = repository.program(profile_data["university"], profile_data["program_id"])
    profile = StudentProfile(
        university_id=profile_data["university"],
        program_id=profile_data["program_id"],
        intake_year=profile_data["intake_year"],
        study_mode=profile_data["study_mode"],
        start_semester=profile_data["start_semester"],
        regulation_version_id=program.regulation_version_id,
        language="de",
    )
    records = [
        CreditAttempt(
            module_code=item["code"],
            semester=item["semester"],
            ects=item["ects"],
            grade=item.get("grade"),
            passed=item["passed"],
            attempt=item["attempt"],
            source=SourceReference(document="golden.yaml"),
            verification_status="unverified",
        )
        for item in data.get("credits", [])
        if item.get("code")
    ]
    category_ids = {item.curriculum_letter: item.id for item in program.categories}
    recognized = [
        RecognizedCredit(
            id=f"golden-{index}",
            module_code=item.get("module_code") or None,
            category_id=category_ids.get(item.get("category")),
            ects=item["ects"],
            basis=item["basis"],
            decision_document=SourceReference(document=item["decision_document"]),
            status="provisional" if not item.get("category") else "confirmed",
        )
        for index, item in enumerate(data.get("recognized", []))
        if item.get("ects", 0) > 0
    ]
    planned = PlanFile(
        planned_modules=[
            PlanItem(module_code=item["code"], target_semester=item["semester"], status="planned")
            for item in data.get("planned", [])
            if item.get("code")
        ]
    )
    credits = CreditsFile(credits=records, recognized_credits=recognized)
    for mode in ("current", "forecast"):
        result = evaluate(program, profile, credits, planned, ChecklistFile(), mode)
        expected = data["expected"][mode]
        assert result.verdict == expected["verdict"]
        gap_text = "\n".join(item["text"] for item in result.gaps)
        for item in expected.get("missing", []):
            assert item in gap_text

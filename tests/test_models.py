import pytest
from pydantic import ValidationError

from studyplan.models import Semester
from studyplan.models.core import Rule


def test_semester_order_and_mycampus_conversion() -> None:
    assert Semester.from_mycampus_run("H2502") == "HS25"
    assert Semester.from_mycampus_run("F2601") == "FS26"
    assert Semester("HS25") == "HS25"
    assert Semester("FS26") == "FS26"
    assert Semester("FS26").sort_key < Semester("HS26").sort_key


@pytest.mark.parametrize("value", ["H25", "HS2025", "SS25", "H2502", "FS2A"])
def test_invalid_semester_strings_are_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        Semester(value)


@pytest.mark.parametrize(
    "kind,parameters",
    [
        ("min_ects_total", {"type": "min_ects_total"}),
        ("min_ects_in_category", {"type": "min_ects_in_category", "category_id": "x"}),
        ("required_module", {"type": "required_module"}),
        ("required_all_mandatory", {"type": "required_all_mandatory", "category_ids": []}),
        ("required_one_of", {"type": "required_one_of", "module_codes": []}),
        ("min_modules_in_category", {"type": "min_modules_in_category", "category_id": "x"}),
        ("prerequisite", {"type": "prerequisite", "module_code": "x"}),
        ("max_attempts", {"type": "max_attempts"}),
        ("retake_budget", {"type": "retake_budget"}),
        ("level_gate", {"type": "level_gate", "gated_level": "basic"}),
        ("level_deadline", {"type": "level_deadline", "level": "basic"}),
        ("min_ects_at_institution", {"type": "min_ects_at_institution"}),
        ("max_recognized_ects", {"type": "max_recognized_ects", "basis": "x"}),
        ("max_study_duration", {"type": "max_study_duration"}),
        ("composite", {"type": "composite", "operator": "and", "rule_ids": []}),
        ("custom_note", {"type": "custom_note"}),
    ],
)
def test_every_rule_parameter_rejects_bad_input(kind: str, parameters: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Rule(
            id="bad",
            type=kind,
            parameters=parameters,
            description="bad",
            verification_status="unverified",
        )

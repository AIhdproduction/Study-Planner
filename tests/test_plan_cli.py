"""CLI coverage for plan edits and machine-readable checks."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from studyplan.cli import app
from studyplan.io.yaml_store import load_model
from studyplan.models import PlanFile


def _common(tmp_path: Path) -> list[str]:
    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "--study-dir",
            str(tmp_path),
            "--profiles-dir",
            str(profiles),
            "init",
            "--university",
            "synthetic_u",
            "--program",
            "synthetic_program_2099",
            "--intake-year",
            "2099",
            "--study-mode",
            "part_time",
            "--start-semester",
            "HS99",
        ],
    )
    assert result.exit_code == 0, result.output
    return ["--study-dir", str(tmp_path), "--profiles-dir", str(profiles)]


def test_plan_add_move_remove_marks_manual_and_validates(tmp_path: Path) -> None:
    runner, common = CliRunner(), _common(tmp_path)
    assert (
        runner.invoke(
            app, [*common, "plan", "add", "--code", "SYN.CORE1", "--semester", "HS99"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, [*common, "plan", "move", "--code", "SYN.CORE1", "--semester", "HS00"]
        ).exit_code
        == 0
    )
    plan = load_model(tmp_path / "plan.yaml", PlanFile)
    assert (
        plan.planned_modules[0].origin == "manual"
        and str(plan.planned_modules[0].target_semester) == "HS00"
    )
    assert (
        runner.invoke(
            app, [*common, "plan", "add", "--code", "UNKNOWN", "--semester", "HS99"]
        ).exit_code
        != 0
    )
    assert runner.invoke(app, [*common, "plan", "remove", "--code", "SYN.CORE1"]).exit_code == 0


def test_plan_json_has_semester_ects_violations_and_admission(tmp_path: Path) -> None:
    runner, common = CliRunner(), _common(tmp_path)
    assert (
        runner.invoke(app, [*common, "plan", "generate", "--current-semester", "HS99"]).exit_code
        == 0
    )
    result = runner.invoke(app, [*common, "plan", "--json"])
    payload = json.loads(result.output)
    assert {"semesters", "violations", "earliest_thesis_admission_semester"} <= payload.keys()
    assert "planned_ects" in next(iter(payload["semesters"].values()))

"""Readable, goal-oriented gap and localized check output tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from studyplan.cli import app
from studyplan.engine.rules import evaluate
from tests.engine_support import checklist, credits, plan, program, student


def test_gaps_name_goal_and_target_without_composite_duplicate() -> None:
    result = evaluate(program(), student(), credits(), plan(), checklist(), "current")
    texts = [item["text"] for item in result.gaps]
    assert any("Graduation" in text and "required" in text for text in texts)
    assert all("Composite requirements" not in text for text in texts)


def test_check_groups_gaps_without_repeating_the_goal_prefix(tmp_path: Path) -> None:
    runner = CliRunner()
    common = [
        "--study-dir",
        str(tmp_path),
        "--profiles-dir",
        str(Path("tests/fixtures/synthetic/profiles").resolve()),
    ]
    assert (
        runner.invoke(
            app,
            [
                *common,
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
                "--lang",
                "de",
            ],
        ).exit_code
        == 0
    )
    output = runner.invoke(app, [*common, "check"]).output
    gaps = output.split("ECTS gesamt: 0\n", maxsplit=1)[1]
    assert "Gesamtergebnis" in output and gaps.count("Abschluss:") == 1
    assert "0 / 3" in output


def test_check_localizes_german_goal_and_manual_note(tmp_path: Path) -> None:
    runner = CliRunner()
    common = [
        "--study-dir",
        str(tmp_path),
        "--profiles-dir",
        str(Path("tests/fixtures/synthetic/profiles").resolve()),
    ]
    assert (
        runner.invoke(
            app,
            [
                *common,
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
                "--lang",
                "de",
            ],
        ).exit_code
        == 0
    )
    output = runner.invoke(app, [*common, "check"]).output
    assert "Bachelorarbeitszulassung" in output
    assert "Synthetische Anforderung" in output

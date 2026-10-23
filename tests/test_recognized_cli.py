"""Tests for recognized-credit CLI operations and engine effects."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from studyplan.cli import app
from studyplan.engine.rules import evaluate
from studyplan.models import CreditsFile, RecognizedCredit, SourceReference
from tests.engine_support import checklist, plan, program, student


def _common(study: Path) -> list[str]:
    return [
        "--study-dir",
        str(study),
        "--profiles-dir",
        str(Path("tests/fixtures/synthetic/profiles").resolve()),
    ]


def _init(runner: CliRunner, study: Path) -> list[str]:
    common = _common(study)
    result = runner.invoke(
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
        ],
    )
    assert result.exit_code == 0, result.output
    return common


def test_recognized_add_with_category_and_list_json(tmp_path: Path) -> None:
    runner, common = CliRunner(), _init(CliRunner(), tmp_path / "study")
    result = runner.invoke(
        app,
        [
            *common,
            "credits",
            "recognize",
            "add",
            "--ects",
            "3",
            "--basis",
            "invented prior study",
            "--category",
            "core",
            "--document",
            "invented.pdf",
        ],
    )
    assert result.exit_code == 0, result.output
    listed = runner.invoke(app, [*common, "credits", "recognize", "list", "--json"])
    payload = json.loads(listed.output)
    assert payload[0]["category_id"] == "core" and payload[0]["status"] == "confirmed"


def test_recognized_list_json_returns_only_recognitions(tmp_path: Path) -> None:
    runner, common = CliRunner(), _init(CliRunner(), tmp_path / "study")
    assert (
        runner.invoke(
            app,
            [
                *common,
                "credits",
                "recognize",
                "add",
                "--ects",
                "3",
                "--basis",
                "invented prior study",
                "--category",
                "core",
                "--document",
                "invented.pdf",
            ],
        ).exit_code
        == 0
    )
    payload = json.loads(
        runner.invoke(app, [*common, "credits", "recognize", "list", "--json"]).output
    )
    assert len(payload) == 1 and payload[0]["id"]


def test_recognized_provisional_without_category_and_remove(tmp_path: Path) -> None:
    runner, common = CliRunner(), _init(CliRunner(), tmp_path / "study")
    added = runner.invoke(
        app,
        [
            *common,
            "credits",
            "recognize",
            "add",
            "--ects",
            "3",
            "--basis",
            "invented prior study",
            "--no-category",
            "--document",
            "invented.pdf",
            "--status",
            "provisional",
            "--open-issue",
            "invented ambiguity",
        ],
    )
    assert added.exit_code == 0, added.output
    item = json.loads(
        runner.invoke(app, [*common, "credits", "recognize", "list", "--json"]).output
    )[0]
    assert item["category_id"] is None and item["status"] == "provisional"
    assert (
        runner.invoke(
            app, [*common, "credits", "recognize", "remove", "--id", item["id"]]
        ).exit_code
        == 0
    )


def test_recognized_remove_deletes_the_selected_item(tmp_path: Path) -> None:
    runner, common = CliRunner(), _init(CliRunner(), tmp_path / "study")
    assert (
        runner.invoke(
            app,
            [
                *common,
                "credits",
                "recognize",
                "add",
                "--ects",
                "3",
                "--basis",
                "invented prior study",
                "--category",
                "core",
                "--document",
                "invented.pdf",
            ],
        ).exit_code
        == 0
    )
    item = json.loads(
        runner.invoke(app, [*common, "credits", "recognize", "list", "--json"]).output
    )[0]
    assert (
        runner.invoke(
            app, [*common, "credits", "recognize", "remove", "--id", item["id"]]
        ).exit_code
        == 0
    )
    assert (
        json.loads(runner.invoke(app, [*common, "credits", "recognize", "list", "--json"]).output)
        == []
    )


def test_recognized_invalid_category_rejected(tmp_path: Path) -> None:
    runner, common = CliRunner(), _init(CliRunner(), tmp_path / "study")
    result = runner.invoke(
        app,
        [
            *common,
            "credits",
            "recognize",
            "add",
            "--ects",
            "3",
            "--basis",
            "invented",
            "--category",
            "unknown",
            "--document",
            "invented.pdf",
        ],
    )
    assert result.exit_code != 0


def test_confirmed_recognized_credit_counts_without_institution_ects() -> None:
    confirmed = RecognizedCredit(
        id="confirmed",
        ects=3,
        basis="invented prior study",
        category_id="core",
        decision_document=SourceReference(document="invented.pdf"),
        status="confirmed",
    )
    result = evaluate(
        program(),
        student(),
        CreditsFile(recognized_credits=[confirmed]),
        plan(),
        checklist(),
        "current",
    )
    assert result.total_ects == 3 and result.category_ects["core"] == 3
    assert next(rule for rule in result.rules if rule.id == "at_institution").current_value == 0


def test_provisional_recognized_credit_makes_the_affected_goal_provisional() -> None:
    confirmed = RecognizedCredit(
        id="confirmed",
        ects=3,
        basis="invented prior study",
        category_id="core",
        decision_document=SourceReference(document="invented.pdf"),
        status="confirmed",
    )
    provisional = confirmed.model_copy(
        update={"id": "provisional", "ects": 12, "status": "provisional"}
    )
    provisional_result = evaluate(
        program(),
        student(),
        CreditsFile(recognized_credits=[provisional]),
        plan(),
        checklist("manual_note"),
        "current",
    )
    assert (
        next(rule for rule in provisional_result.rules if rule.id == "total").status
        == "provisional"
    )

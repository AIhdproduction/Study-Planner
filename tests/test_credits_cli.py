"""CLI tests for managing study credits."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from studyplan.cli import app

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"


@pytest.fixture
def initialized_study(tmp_path: Path) -> tuple[CliRunner, list[str]]:
    runner = CliRunner()
    common_args = [
        "--study-dir",
        str(tmp_path),
        "--profiles-dir",
        str(PROFILES_DIR),
    ]
    init_args = [
        *common_args,
        "init",
        "--university",
        "hslu_ta",
        "--program",
        "digital_construction_architecture_2025",
        "--intake-year",
        "2025",
        "--study-mode",
        "part_time",
        "--start-semester",
        "HS25",
    ]
    init_res = runner.invoke(app, init_args)
    assert init_res.exit_code == 0
    return runner, common_args


def test_add_valid_credit(initialized_study: tuple[CliRunner, list[str]]) -> None:
    runner, common = initialized_study
    add_args = [
        *common,
        "credits",
        "add",
        "--code",
        "TA.BA_NABA",
        "--semester",
        "HS25",
        "--ects",
        "3",
        "--grade",
        "B",
    ]
    result = runner.invoke(app, add_args)
    assert result.exit_code == 0

    list_result = runner.invoke(app, [*common, "credits", "list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output)
    assert any(
        c["module_code"] == "TA.BA_NABA"
        and c["semester"] == "HS25"
        and c["ects"] == 3
        and c["grade"] == "B"
        for c in payload["credits"]
    )


def test_unknown_code_rejected(initialized_study: tuple[CliRunner, list[str]]) -> None:
    runner, common = initialized_study
    add_args = [
        *common,
        "credits",
        "add",
        "--code",
        "TA.BA_UNKNOWN",
        "--semester",
        "HS25",
        "--ects",
        "3",
        "--grade",
        "B",
    ]
    result = runner.invoke(app, add_args)
    assert result.exit_code != 0

    list_result = runner.invoke(app, [*common, "credits", "list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output)
    assert payload["credits"] == []


def test_duplicate_attempt_rejected(initialized_study: tuple[CliRunner, list[str]]) -> None:
    runner, common = initialized_study
    add_args = [
        *common,
        "credits",
        "add",
        "--code",
        "TA.BA_NABA",
        "--semester",
        "HS25",
        "--ects",
        "3",
        "--grade",
        "B",
        "--attempt",
        "1",
    ]
    result1 = runner.invoke(app, add_args)
    assert result1.exit_code == 0

    result2 = runner.invoke(app, add_args)
    assert result2.exit_code != 0

    list_result = runner.invoke(app, [*common, "credits", "list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output)
    assert len(payload["credits"]) == 1


def test_ects_mismatch_rejected(initialized_study: tuple[CliRunner, list[str]]) -> None:
    runner, common = initialized_study
    add_args = [
        *common,
        "credits",
        "add",
        "--code",
        "TA.BA_NABA",
        "--semester",
        "HS25",
        "--ects",
        "6",
        "--grade",
        "B",
    ]
    result = runner.invoke(app, add_args)
    assert result.exit_code != 0

    list_result = runner.invoke(app, [*common, "credits", "list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output)
    assert payload["credits"] == []


def test_invalid_grade_rejected(initialized_study: tuple[CliRunner, list[str]]) -> None:
    runner, common = initialized_study
    add_args = [
        *common,
        "credits",
        "add",
        "--code",
        "TA.BA_NABA",
        "--semester",
        "HS25",
        "--ects",
        "3",
        "--grade",
        "G",
    ]
    result = runner.invoke(app, add_args)
    assert result.exit_code != 0

    list_result = runner.invoke(app, [*common, "credits", "list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output)
    assert payload["credits"] == []


def test_edit_changes_grade(initialized_study: tuple[CliRunner, list[str]]) -> None:
    runner, common = initialized_study
    add_args = [
        *common,
        "credits",
        "add",
        "--code",
        "TA.BA_NABA",
        "--semester",
        "HS25",
        "--ects",
        "3",
        "--grade",
        "B",
        "--attempt",
        "1",
    ]
    assert runner.invoke(app, add_args).exit_code == 0

    edit_args = [
        *common,
        "credits",
        "edit",
        "--code",
        "TA.BA_NABA",
        "--attempt",
        "1",
        "--grade",
        "A",
    ]
    edit_result = runner.invoke(app, edit_args)
    assert edit_result.exit_code == 0

    list_result = runner.invoke(app, [*common, "credits", "list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output)
    assert len(payload["credits"]) == 1
    assert payload["credits"][0]["grade"] == "A"


def test_remove_deletes_entry(initialized_study: tuple[CliRunner, list[str]]) -> None:
    runner, common = initialized_study
    add_args = [
        *common,
        "credits",
        "add",
        "--code",
        "TA.BA_NABA",
        "--semester",
        "HS25",
        "--ects",
        "3",
        "--grade",
        "B",
        "--attempt",
        "1",
    ]
    assert runner.invoke(app, add_args).exit_code == 0

    remove_args = [
        *common,
        "credits",
        "remove",
        "--code",
        "TA.BA_NABA",
        "--attempt",
        "1",
    ]
    remove_result = runner.invoke(app, remove_args)
    assert remove_result.exit_code == 0

    list_result = runner.invoke(app, [*common, "credits", "list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output)
    assert payload["credits"] == []


def test_list_json_returns_expected_fields(
    initialized_study: tuple[CliRunner, list[str]],
) -> None:
    runner, common = initialized_study
    add_args = [
        *common,
        "credits",
        "add",
        "--code",
        "TA.BA_NABA",
        "--semester",
        "HS25",
        "--ects",
        "3",
        "--grade",
        "B",
        "--attempt",
        "1",
    ]
    assert runner.invoke(app, add_args).exit_code == 0

    list_result = runner.invoke(app, [*common, "credits", "list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output)

    assert "credits" in payload
    assert "recognized_credits" in payload
    assert isinstance(payload["credits"], list)
    assert len(payload["credits"]) == 1

    entry = payload["credits"][0]
    expected_fields = {
        "module_code",
        "semester",
        "ects",
        "grade",
        "passed",
        "attempt",
        "forced_category_id",
        "forced_category_reason",
        "recognized_external",
        "source",
        "verification_status",
    }
    assert expected_fields.issubset(entry.keys())
    assert entry["module_code"] == "TA.BA_NABA"
    assert entry["semester"] == "HS25"
    assert entry["ects"] == 3
    assert entry["grade"] == "B"
    assert entry["passed"] is True
    assert entry["attempt"] == 1

"""Tests for the doctor --inbox command and document inspection."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from studyplan.cli import app


def test_empty_inbox_reports_all_missing(tmp_path: Path) -> None:
    runner = CliRunner()
    study = tmp_path / "study"
    study.mkdir()
    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    common = ["--study-dir", str(study), "--profiles-dir", str(profiles)]

    result_json = runner.invoke(app, [*common, "doctor", "--inbox", "--json"])
    assert result_json.exit_code == 0
    data = json.loads(result_json.output)
    assert data["missing_recommended"] == ["mycampus_page"]
    assert data["profile_exists"] is False
    assert len(data["items"]) == 6
    assert all(item["status"] == "missing" for item in data["items"])
    assert all(item["count"] == 0 for item in data["items"])

    result_human = runner.invoke(app, [*common, "doctor", "--inbox"])
    assert result_human.exit_code == 0
    assert "missing" in result_human.output
    assert "See `studyplan guide` for how to save it." in result_human.output

    (study / "profile.yaml").write_text("language: en\n", encoding="utf-8")
    result_with_profile = runner.invoke(app, [*common, "doctor", "--inbox", "--json"])
    assert result_with_profile.exit_code == 0
    assert json.loads(result_with_profile.output)["profile_exists"] is True


def test_dummy_files_present_counted_correctly(tmp_path: Path) -> None:
    runner = CliRunner()
    study = tmp_path / "study"
    inbox = study / "inbox"
    (inbox / "transcript").mkdir(parents=True)
    (inbox / "regulations").mkdir(parents=True)
    (inbox / "modules").mkdir(parents=True)

    (inbox / "transcript" / "Meine Anmeldungen Max Muster.html").write_text("ok", encoding="utf-8")
    (inbox / "transcript" / ".gitkeep").write_text("", encoding="utf-8")
    (inbox / "regulations" / "Regulation_2025.pdf").write_text("ok", encoding="utf-8")
    (inbox / "regulations" / "Curriculum_2025.pdf").write_text("ok", encoding="utf-8")
    (inbox / "modules" / "Thesis.PDF").write_text("ok", encoding="utf-8")

    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    common = ["--study-dir", str(study), "--profiles-dir", str(profiles)]

    result = runner.invoke(app, [*common, "doctor", "--inbox", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    items = {item["id"]: item for item in data["items"]}

    assert items["mycampus_page"]["status"] == "present"
    assert items["mycampus_page"]["count"] == 1
    assert items["regulations"]["status"] == "present"
    assert items["regulations"]["count"] == 2
    assert items["module_descriptions"]["status"] == "present"
    assert items["module_descriptions"]["count"] == 1

    assert items["model_timetable"]["status"] == "missing"
    assert items["model_timetable"]["count"] == 0
    assert items["transcript_pdf"]["status"] == "missing"
    assert items["transcript_pdf"]["count"] == 0
    assert items["recognition"]["status"] == "missing"
    assert items["recognition"]["count"] == 0

    assert data["missing_recommended"] == []

    result_human = runner.invoke(app, [*common, "doctor", "--inbox"])
    assert result_human.exit_code == 0
    assert "Study regulation and curriculum: present (2)" in result_human.output
    assert "Module descriptions: present (1)" in result_human.output
    assert 'MyCampus "Meine Anmeldungen": present (1)' in result_human.output
    assert "Model timetable: missing" in result_human.output


def test_output_does_not_contain_dummy_file_names(tmp_path: Path) -> None:
    runner = CliRunner()
    study = tmp_path / "study"
    inbox = study / "inbox"
    (inbox / "transcript").mkdir(parents=True)
    (inbox / "regulations").mkdir(parents=True)
    (inbox / "modules").mkdir(parents=True)

    dummy_names = [
        "Meine Anmeldungen Max Muster.html",
        "Regulation_Max_Muster_2025.pdf",
        "Thesis.PDF",
    ]
    (inbox / "transcript" / dummy_names[0]).write_text("ok", encoding="utf-8")
    (inbox / "regulations" / dummy_names[1]).write_text("ok", encoding="utf-8")
    (inbox / "modules" / dummy_names[2]).write_text("ok", encoding="utf-8")

    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    common = ["--study-dir", str(study), "--profiles-dir", str(profiles)]

    json_result = runner.invoke(app, [*common, "doctor", "--inbox", "--json"])
    assert json_result.exit_code == 0
    assert "Max Muster" not in json_result.output
    for name in dummy_names:
        assert name not in json_result.output

    human_result = runner.invoke(app, [*common, "doctor", "--inbox"])
    assert human_result.exit_code == 0
    assert "Max Muster" not in human_result.output
    for name in dummy_names:
        assert name not in human_result.output


def test_german_language_human_output_contains_german_labels(tmp_path: Path) -> None:
    runner = CliRunner()
    study = tmp_path / "study"
    study.mkdir()
    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    common = ["--study-dir", str(study), "--profiles-dir", str(profiles)]

    result = runner.invoke(app, [*common, "doctor", "--inbox", "--lang", "de"])
    assert result.exit_code == 0
    assert "Studienreglement und Curriculum" in result.output
    assert "Modellstundenplan" in result.output
    assert "Offizieller Notenausweis" in result.output
    assert "Anerkennungsentscheide" in result.output
    assert "Modulbeschreibungen" in result.output
    assert "fehlt" in result.output
    assert "Anleitung: `studyplan guide`" in result.output


def test_doctor_without_inbox_output_unchanged(tmp_path: Path) -> None:
    runner = CliRunner()
    study = tmp_path / "study"
    study.mkdir()
    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    common = ["--study-dir", str(study), "--profiles-dir", str(profiles)]

    result_en = runner.invoke(app, [*common, "doctor"])
    assert result_en.exit_code == 0
    assert "StudyPlan environment is ready." in result_en.output
    assert "present" not in result_en.output
    assert "missing" not in result_en.output

    result_de = runner.invoke(app, [*common, "doctor", "--lang", "de"])
    assert result_de.exit_code == 0
    assert "StudyPlan-Umgebung ist bereit." in result_de.output
    assert "vorhanden" not in result_de.output
    assert "fehlt" not in result_de.output


def test_invalid_profile_does_not_break_doctor(tmp_path: Path) -> None:
    runner = CliRunner()
    study = tmp_path / "study"
    study.mkdir()
    (study / "profile.yaml").write_text("invalid: yaml: content: [", encoding="utf-8")
    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    common = ["--study-dir", str(study), "--profiles-dir", str(profiles)]

    result = runner.invoke(app, [*common, "doctor", "--inbox"])
    assert result.exit_code == 0

    result_json = runner.invoke(app, [*common, "doctor", "--inbox", "--json"])
    assert result_json.exit_code == 0
    data = json.loads(result_json.output)
    assert data["profile_exists"] is True

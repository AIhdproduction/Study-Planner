"""Tests for the guide command and localized workflow instructions."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from studyplan.cli import app


def test_guide_en_contains_expected_commands_and_paths() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["guide", "--lang", "en"])
    assert result.exit_code == 0
    assert "/setup —" in result.output
    assert "/credits —" in result.output
    assert "/check —" in result.output
    assert "/plan —" in result.output
    assert "/excel —" in result.output
    assert "/missing —" in result.output
    assert "my_study" in result.output
    assert "my_study\\inbox\\regulations" in result.output


def test_guide_de_contains_expected_german_texts() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["guide", "--lang", "de"])
    assert result.exit_code == 0
    assert "Strg+S" in result.output
    assert "Als PDF speichern" in result.output
    assert "Studienplan" in result.output
    assert "/setup —" in result.output
    assert "/credits —" in result.output
    assert "/check —" in result.output
    assert "/plan —" in result.output
    assert "/excel —" in result.output
    assert "/missing —" in result.output


def test_guide_output_writes_utf8_with_bom(tmp_path: Path) -> None:
    runner = CliRunner()
    out_file = tmp_path / "ABLAUF.txt"
    result = runner.invoke(app, ["guide", "--output", str(out_file)])
    assert result.exit_code == 0
    assert out_file.exists()
    raw = out_file.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    content = raw.decode("utf-8-sig")
    assert "/setup —" in content
    assert "/credits —" in content
    assert "/check —" in content
    assert "/plan —" in content
    assert "/excel —" in content
    assert "/missing —" in content


def test_guide_language_fallback_to_studyplan_lang_without_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    monkeypatch.setenv("STUDYPLAN_LANG", "de")
    empty_study = tmp_path / "empty_study"
    empty_study.mkdir()
    result = runner.invoke(app, ["--study-dir", str(empty_study), "guide"])
    assert result.exit_code == 0
    assert "Strg+S" in result.output
    assert "Als PDF speichern" in result.output
    assert "Studienplan" in result.output


def test_guide_output_contains_disclaimer() -> None:
    runner = CliRunner()
    result_en = runner.invoke(app, ["guide", "--lang", "en"])
    assert result_en.exit_code == 0
    assert (
        "Not legally binding. The official study regulations and the program management decide."
        in result_en.output
    )
    result_de = runner.invoke(app, ["guide", "--lang", "de"])
    assert result_de.exit_code == 0
    assert (
        "Nicht rechtsverbindlich. Es gelten das offizielle Studienreglement und die"
        in result_de.output
    )


def test_guide_has_no_personal_example_values() -> None:
    runner = CliRunner()
    forbidden = ["2025", "HS25", "Teilzeit", "part time", "Digital Construction", "Architecture"]
    for lang in ["en", "de"]:
        result = runner.invoke(app, ["guide", "--lang", lang])
        assert result.exit_code == 0
        for item in forbidden:
            assert item not in result.output

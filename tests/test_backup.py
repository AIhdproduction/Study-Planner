"""Backup and restore CLI tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from studyplan.cli import app


def test_backup_round_trip_and_restore_refusal(tmp_path: Path) -> None:
    runner = CliRunner()
    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    first = tmp_path / "first"
    common = ["--study-dir", str(first), "--profiles-dir", str(profiles)]
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
            ],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, [*common, "backup"]).exit_code == 0
    archive = next((first / "backups").glob("*.json"))
    second = tmp_path / "second"
    other = ["--study-dir", str(second), "--profiles-dir", str(profiles)]
    assert runner.invoke(app, [*other, "restore", str(archive)]).exit_code == 0
    for name in ("profile.yaml", "credits.yaml", "plan.yaml", "checklist.yaml"):
        assert (first / name).read_text(encoding="utf-8") == (second / name).read_text(
            encoding="utf-8"
        )
    assert runner.invoke(app, [*other, "restore", str(archive)]).exit_code != 0


def test_restore_force_overwrites_existing_files(tmp_path: Path) -> None:
    runner = CliRunner()
    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    original = tmp_path / "original"
    common = ["--study-dir", str(original), "--profiles-dir", str(profiles)]
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
            ],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, [*common, "backup"]).exit_code == 0
    archive = next((original / "backups").glob("*.json"))
    target = tmp_path / "target"
    other = ["--study-dir", str(target), "--profiles-dir", str(profiles)]
    assert runner.invoke(app, [*other, "restore", str(archive)]).exit_code == 0
    (target / "credits.yaml").write_text("credits: []\nrecognized_credits: []\n", encoding="utf-8")
    assert runner.invoke(app, [*other, "restore", str(archive), "--force"]).exit_code == 0
    assert (target / "credits.yaml").read_text(encoding="utf-8") == (
        original / "credits.yaml"
    ).read_text(encoding="utf-8")

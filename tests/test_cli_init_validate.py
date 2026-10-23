import json
from pathlib import Path

from typer.testing import CliRunner

from studyplan.cli import app


def test_help_lists_foundation_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0 and "init" in result.output


def test_init_validate_modules_and_profiles_use_configured_directories(tmp_path: Path) -> None:
    runner = CliRunner()
    study = tmp_path / "study"
    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    common = ["--study-dir", str(study), "--profiles-dir", str(profiles)]
    args = [
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
    ]
    assert runner.invoke(app, args).exit_code == 0
    assert all(
        (study / name).exists()
        for name in ["profile.yaml", "credits.yaml", "plan.yaml", "checklist.yaml"]
    )
    assert runner.invoke(app, args).exit_code == 2
    assert runner.invoke(app, [*common, "validate"]).exit_code == 0
    assert "SYN.CORE1" in runner.invoke(app, [*common, "modules", "--search", "Core"]).output
    listed = runner.invoke(app, [*common, "profiles", "--json"])
    assert "synthetic_u" in json.loads(listed.output)[0]["id"]


def test_missing_profile_has_clean_error(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["--study-dir", str(tmp_path), "modules"])
    assert result.exit_code == 2
    assert "No study profile found" in result.output

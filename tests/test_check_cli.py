import json
from pathlib import Path

from jsonschema import validate
from typer.testing import CliRunner

from studyplan.cli import DISCLAIMER, app


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


def test_check_json_validates_against_schema(tmp_path: Path) -> None:
    runner = CliRunner()
    common = _init(runner, tmp_path / "study")
    assert runner.invoke(app, [*common, "schema"]).exit_code == 0
    result = runner.invoke(app, [*common, "check", "--mode", "current", "--json"])
    assert result.exit_code == 0, result.output
    schema = json.loads(Path("schemas/check_result.schema.json").read_text(encoding="utf-8"))
    validate(json.loads(result.output), schema)


def test_check_human_output_has_disclaimer(tmp_path: Path) -> None:
    runner = CliRunner()
    common = _init(runner, tmp_path / "study")
    result = runner.invoke(app, [*common, "check"])
    assert result.exit_code == 0 and DISCLAIMER in result.output


def test_check_without_profile_exits_two(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, [*(_common(tmp_path / "missing")), "check"])
    assert result.exit_code == 2

import json
from pathlib import Path

from typer.testing import CliRunner

from studyplan.cli import app
from studyplan.models import Semester


def test_run_suffix_conversion() -> None:
    assert Semester.from_mycampus_run("F2601") == "FS26"


def test_synthetic_page_preserves_attempt_order_and_privacy(tmp_path: Path) -> None:
    runner = CliRunner()
    study = tmp_path / "study"
    profiles = Path("tests/fixtures/synthetic/profiles").resolve()
    common = ["--study-dir", str(study), "--profiles-dir", str(profiles)]
    init = runner.invoke(
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
    assert init.exit_code == 0
    page = Path("tests/fixtures/synthetic/mycampus_sample.html")
    result = runner.invoke(app, [*common, "credits", "import-mycampus", str(page), "--json"])
    rows = json.loads(result.output)
    python_rows = [row for row in rows if row.get("module_code") == "SYN.CORE1"]
    assert [(row.get("grade"), row.get("attempt")) for row in python_rows if "attempt" in row] == [
        ("E", 2),
        ("F", 1),
    ]
    assert any(row["status"] == "running" for row in rows)
    assert any(row["status"] == "unmapped" for row in rows)
    assert any(row["status"] == "ignored_event" for row in rows)

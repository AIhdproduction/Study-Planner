import json
from pathlib import Path

import pytest
from selectolax.lexbor import LexborHTMLParser
from typer.testing import CliRunner

from studyplan.cli import app


@pytest.mark.real
def test_real_mycampus_dry_run_is_complete_and_private(tmp_path: Path) -> None:
    page = Path("tests/fixtures/real/Meine Anmeldungen _ Hochschule Luzern.html")
    if not page.exists():
        pytest.skip("Private MyCampus fixture is unavailable.")
    study = tmp_path / "study"
    profiles = Path("profiles").resolve()
    runner = CliRunner()
    common = ["--study-dir", str(study), "--profiles-dir", str(profiles)]
    init = runner.invoke(
        app,
        [
            *common,
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
        ],
    )
    assert init.exit_code == 0, init.output
    result = runner.invoke(app, [*common, "credits", "import-mycampus", str(page), "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert len(rows) == 20
    assert sum(row["status"] == "ignored_event" for row in rows) == 1
    assert not [row for row in rows if row["status"] == "unmapped"]
    assert sum(row["status"] == "running" for row in rows) == 5
    python_rows = [row for row in rows if row.get("module_code") == "TA.BA_PYTHON_MM"]
    assert {(row["grade"], row["attempt"]) for row in python_rows} == {("F", 1), ("E", 2)}
    document = LexborHTMLParser(page.read_text(encoding="utf-8", errors="replace"))
    names = [cell.text(strip=True) for cell in document.css("tr td") if cell.text(strip=True)]
    assert all(name not in result.output for name in names if " " in name and len(name) > 4)

from studyplan.io import load_yaml, validate_yaml
from studyplan.models import StudentProfile

FIXTURES = "tests/fixtures/synthetic"


def test_round_trip_reader_preserves_comment() -> None:
    from pathlib import Path

    path = Path(FIXTURES) / "commented.yaml"
    assert load_yaml(path)["value"] == 1
    assert "# retained" in path.read_text(encoding="utf-8")


def test_broken_yaml_has_file_and_line() -> None:
    from pathlib import Path

    path = Path(FIXTURES) / "broken.yaml"
    issues = validate_yaml(path, StudentProfile)
    assert issues and issues[0].file == path and issues[0].line

"""Extract relative module semesters from a HSLU part-time model timetable PDF.

Usage: uv run python scripts/extract_model_timetable.py "<PDF path>"
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader
from ruamel.yaml import YAML

CODE_RE = re.compile(r"TA\.BA_[A-Z0-9+_]+")
CURRICULUM_CODES = {
    "TA.BA_DATA1": "TA.BA_DATA1_MM",
    "TA.BA_DATA2": "TA.BA_DATA2_MM",
    "TA.BA_DATA3": "TA.BA_DATA3_MM",
    "TA.BA_PYTHON": "TA.BA_PYTHON_MM",
}
ELECTIVES = {
    "TA.BA_BAUKLI_MM",
    "TA.BA_TRL1",
    "TA.BA_BRE",
    "TA.BA_IMM_TECH",
    "TA.BA_DC_SR1",
    "TA.BA_DC_BRIDGE",
}


def relative_semester(y: float) -> int:
    """Map the eight vertical timetable bands, read bottom to top, to semesters 1-8."""
    return (
        8
        if y > 1000
        else 7
        if y > 900
        else 6
        if y > 780
        else 5
        if y > 640
        else 4
        if y > 506
        else 3
        if y > 400
        else 2
        if y > 300
        else 1
    )


def extract(path: Path) -> list[dict[str, object]]:
    words: list[tuple[str, float]] = []

    def visitor(text: str, _cm: object, tm: list[float], *_rest: object) -> None:
        for code in CODE_RE.findall(text):
            words.append((CURRICULUM_CODES.get(code, code), tm[5]))

    for page in PdfReader(path).pages:
        page.extract_text(visitor_text=visitor)
    placements: defaultdict[str, list[int]] = defaultdict(list)
    for code, y in words:
        placements[code].append(relative_semester(y))
    return [
        {
            "module_code": code,
            "relative_semester": max(values),
            "recommended": code in ELECTIVES,
            "offered_terms": ["HS" if max(values) % 2 else "FS"],
            "source": {"document": path.name, "page": 1},
            "verification_status": "unverified",
        }
        for code, values in sorted(placements.items(), key=lambda item: (max(item[1]), item[0]))
    ]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: extract_model_timetable.py <PDF path>")
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.dump({"model_timetables": {"part_time": {"HS": extract(Path(sys.argv[1]))}}}, sys.stdout)


if __name__ == "__main__":
    main()

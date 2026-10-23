"""Public real-fixture timetable extraction test."""

from __future__ import annotations

from pathlib import Path

import pytest

from studyplan.io import ProfileRepository


@pytest.mark.real
def test_model_timetable_places_every_mandatory_module() -> None:
    pdf = Path("tests/fixtures/real/DCA Musterstundenplan Arch Teilzeit.pdf")
    if not pdf.exists():
        pytest.skip("Real model timetable fixture is unavailable.")
    program = ProfileRepository(Path("profiles")).program(
        "hslu_ta", "digital_construction_architecture_2025"
    )
    entries = program.model_timetables["part_time"]["HS"]
    expected = {
        1: {
            "TA.BA_DC_BRIDGE": True,
            "TA.BA_DC_GRND1_MM": False,
            "TA.BA_DC_GRND2_MM": False,
            "TA.BA_DT_GRND_MM": False,
            "TA.BA_GRU_A": False,
            "TA.BA_NABA": False,
            "TA.BA_PYTHON_MM": False,
        },
        2: {
            "TA.BA_DC_METH": False,
            "TA.BA_DC_SR1": True,
            "TA.BA_DC_STUD1": False,
            "TA.BA_DT_PARAM": False,
            "TA.BA_KOENW": False,
            "TA.BA_WIRK": False,
            "TA.BA_ZYKLUS": False,
        },
        3: {
            "TA.BA_DATA1_MM": False,
            "TA.BA_DC_TECH_MM": False,
            "TA.BA_DT_PROGR": False,
            "TA.BA_B_WERK": False,
        },
        4: {
            "TA.BA_AT_TEAM": False,
            "TA.BA_DC_COLLAB_MM": False,
            "TA.BA_IMM_TECH": True,
            "TA.BA_KONZEPT": False,
            "TA.BA_WISSARB": False,
        },
        5: {
            "TA.BA_BRE": True,
            "TA.BA_DC_STUD2": False,
            "TA.BA_DT_DESIGN": False,
            "TA.BA_RESS": False,
            "TA.BA_TRL1": True,
        },
        6: {
            "TA.BA_BAUKLI_MM": True,
            "TA.BA_B_IW": False,
            "TA.BA_DATA2_MM": False,
            "TA.BA_DC_STUD3": False,
            "TA.BA_DT_CONST": False,
        },
        7: {
            "TA.BA_BEST": False,
            "TA.BA_DATA3_MM": False,
            "TA.BA_DC_STUD4": False,
            "TA.BA_DT_BETR_LIFE": False,
        },
        8: {"TA.BA_BAA_DC": False},
    }
    actual = {item.relative_semester: {} for item in entries}
    for item in entries:
        actual[item.relative_semester][item.module_code] = item.recommended
    assert actual == expected

"""Tests for HSLU code mapping configuration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from studyplan.io.yaml_store import load_yaml

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"
MAPPING_PATH = PROFILES_DIR / "hslu_ta" / "code_mapping.yaml"
PROGRAM_PATH = PROFILES_DIR / "hslu_ta" / "programs" / "digital_construction_architecture_2025.yaml"


@pytest.fixture
def mapping_entries() -> list[dict[str, Any]]:
    data = load_yaml(MAPPING_PATH)
    return data["mappings"]


@pytest.fixture
def program_module_codes() -> set[str]:
    data = load_yaml(PROGRAM_PATH)
    return {module["code"] for module in data["modules"]}


def test_code_mapping_entry_count(mapping_entries: list[dict[str, Any]]) -> None:
    assert len(mapping_entries) == 31


def test_curriculum_codes_exist_in_program(
    mapping_entries: list[dict[str, Any]], program_module_codes: set[str]
) -> None:
    for entry in mapping_entries:
        curr_code = entry.get("curriculum_code")
        if curr_code is not None:
            msg = (
                f"Curriculum code '{curr_code}' for foreign "
                f"'{entry.get('foreign_code')}' not in program"
            )
            assert curr_code in program_module_codes, msg


def test_no_run_or_version_suffixes(mapping_entries: list[dict[str, Any]]) -> None:
    run_suffix_pattern = re.compile(r"\.[HF]\d{4}$")
    version_suffix_pattern = re.compile(r"\.\d{2}$")

    for entry in mapping_entries:
        foreign = entry["foreign_code"]
        assert not run_suffix_pattern.search(foreign), f"Foreign code '{foreign}' has a run suffix"
        assert not version_suffix_pattern.search(foreign), (
            f"Foreign code '{foreign}' has a version suffix"
        )


def test_no_duplicate_source_foreign_code_pairs(mapping_entries: list[dict[str, Any]]) -> None:
    seen: set[tuple[str, str]] = set()
    for entry in mapping_entries:
        pair = (entry["source"], entry["foreign_code"])
        assert pair not in seen, f"Duplicate pair found: {pair}"
        seen.add(pair)


def test_no_entry_where_foreign_equals_curriculum(mapping_entries: list[dict[str, Any]]) -> None:
    for entry in mapping_entries:
        assert entry["foreign_code"] != entry.get("curriculum_code"), (
            f"Foreign code equals curriculum code: {entry['foreign_code']}"
        )


def test_source_validity(mapping_entries: list[dict[str, Any]]) -> None:
    allowed_sources = {"mycampus", "timetable", "module_directory"}
    for entry in mapping_entries:
        assert entry["source"] in allowed_sources, (
            f"Invalid source '{entry.get('source')}' in entry {entry}"
        )


def test_every_verification_status_is_unverified(mapping_entries: list[dict[str, Any]]) -> None:
    for entry in mapping_entries:
        assert entry["verification_status"] == "unverified", f"Status is not unverified for {entry}"

"""Source-specific, explicit curriculum code matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from studyplan.models import CodeMapping, Program
from studyplan.models.core import VerificationStatus

CodeSource = Literal["mycampus", "timetable", "module_directory"]


@dataclass(frozen=True)
class CodeMatch:
    """The transparent outcome of a source-code lookup."""

    source: CodeSource
    raw_code: str
    stem: str
    status: Literal["direct", "mapped", "unmapped", "not_in_curriculum"]
    curriculum_code: str | None
    verification_status: VerificationStatus | None = None


def extract_code_stem(source: CodeSource, code: str) -> str:
    """Remove only the documented source-specific decoration from a code."""
    value = code.strip()
    if source == "mycampus":
        return re.sub(r"\.[HF]\d{4}$", "", value)
    if source == "module_directory":
        return re.sub(r"\.\d{2}$", "", value)
    return re.sub(r"^[A-Z]+-[A-Z]-", "", value)


def match_code(
    program: Program, mappings: list[CodeMapping], source: CodeSource, raw_code: str
) -> CodeMatch:
    """Match by identical stem first, then by an explicit source-specific mapping."""
    stem = extract_code_stem(source, raw_code)
    module_codes = {module.code for module in program.modules}
    if stem in module_codes:
        return CodeMatch(source, raw_code, stem, "direct", stem, "verified")
    mapping = next(
        (item for item in mappings if item.source == source and item.foreign_code == stem), None
    )
    if mapping is None:
        return CodeMatch(source, raw_code, stem, "unmapped", None)
    if mapping.curriculum_code is None:
        return CodeMatch(
            source, raw_code, stem, "not_in_curriculum", None, mapping.verification_status
        )
    return CodeMatch(
        source,
        raw_code,
        stem,
        "mapped",
        mapping.curriculum_code,
        mapping.verification_status,
    )

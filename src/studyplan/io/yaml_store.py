"""Round-trip YAML storage with useful validation diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError

from studyplan.models import CodeMappingsFile, Program, University

_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.default_flow_style = False


@dataclass(frozen=True)
class ValidationIssue:
    file: Path
    line: int | None
    message: str
    hint: str


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return _yaml.load(handle)


def save_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        _yaml.dump(data, handle)


def load_model[T: BaseModel](path: Path, model: type[T]) -> T:
    return model.model_validate(load_yaml(path))


def save_model(path: Path, model: BaseModel) -> None:
    save_yaml(path, model.model_dump(mode="json", exclude_none=False))


def validate_yaml[T: BaseModel](path: Path, model: type[T]) -> list[ValidationIssue]:
    try:
        data = load_yaml(path)
        model.model_validate(data)
    except MarkedYAMLError as error:
        return [
            ValidationIssue(
                path,
                error.problem_mark.line + 1 if error.problem_mark else None,
                str(error.problem),
                "Fix the YAML syntax at the reported location.",
            )
        ]
    except ValidationError as error:
        return [
            ValidationIssue(path, 1, item["msg"], f"Fix field: {'.'.join(map(str, item['loc']))}.")
            for item in error.errors()
        ]
    return []


@dataclass(frozen=True)
class ProfileRepository:
    root: Path

    def university(self, university_id: str) -> University:
        return load_model(self.root / university_id / "university.yaml", University)

    def program(self, university_id: str, program_id: str) -> Program:
        for path in (self.root / university_id / "programs").glob("*.yaml"):
            program = load_model(path, Program)
            if program.id == program_id:
                return program
        raise FileNotFoundError(
            f"Program '{program_id}' was not found for university '{university_id}'."
        )

    def mappings(self, university_id: str) -> CodeMappingsFile:
        return load_model(self.root / university_id / "code_mapping.yaml", CodeMappingsFile)

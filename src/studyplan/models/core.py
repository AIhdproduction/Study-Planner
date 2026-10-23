"""Strict, forward-compatible Pydantic models for StudyPlan YAML files."""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, PositiveInt, model_validator
from pydantic_core import core_schema

VerificationStatus = Literal["unverified", "verified", "edited"]
StudyMode = Literal["full_time", "part_time", "extra_occupational"]
Grade = Literal["A", "B", "C", "D", "E", "F"]
Level = Literal["basic", "intermediate", "advanced"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Semester(str):
    """A Swiss semester code that orders chronologically."""

    _pattern = re.compile(r"^(HS|FS)(\d{2})$")

    def __new__(cls, value: str) -> Self:
        match = cls._pattern.fullmatch(value)
        if not match:
            raise ValueError("Semester must use HSyy or FSyy, for example HS25.")
        return str.__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: object, _handler: object
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())

    @property
    def sort_key(self) -> tuple[int, int]:
        match = self._pattern.fullmatch(self)
        assert match is not None
        term, year = match.groups()
        return int(year), 0 if term == "FS" else 1

    @classmethod
    def from_mycampus_run(cls, value: str) -> Self:
        match = re.fullmatch(r"([HF])(\d{2})\d{2}", value)
        if not match:
            raise ValueError("MyCampus run must use Hyyrr or Fyyrr, for example H2502.")
        term, year = match.groups()
        return cls(f"{'HS' if term == 'H' else 'FS'}{year}")


class SourceReference(Model):
    document: str
    page: int | None = None
    url: HttpUrl | None = None
    retrieved_on: date | None = None
    note: str | None = None


class ManualSource(Model):
    id: str
    instructions: str


class RegulationVersion(Model):
    id: str
    document: SourceReference
    valid_intake_years: list[int]
    retrieval_date: date | None = None
    transition_text: str | None = None
    previous_version_id: str | None = None


class University(Model):
    id: str
    name: str
    regulation_versions: list[RegulationVersion]
    sources: list[SourceReference] = Field(default_factory=list)
    manual_sources: list[ManualSource] = Field(default_factory=list)


class StudyModeDuration(Model):
    standard_semesters: PositiveInt | None = None
    maximum_semesters: PositiveInt | None = None


class ModuleCategory(Model):
    id: str
    official_name: str
    curriculum_letter: str | None = None
    description: str | None = None
    source: SourceReference | None = None
    verification_status: VerificationStatus


class Prerequisite(Model):
    module_code: str | None = None
    rule_id: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def has_reference(self) -> Self:
        if not self.module_code and not self.rule_id and not self.description:
            raise ValueError("Prerequisite needs a module code, rule id, or description.")
        return self


class Module(Model):
    code: str
    title: str
    ects: PositiveInt
    eligible_category_ids: list[str]
    level: Level
    mandatory: bool
    semesters_offered: list[str] = Field(default_factory=list)
    offering_frequency: str | None = None
    prerequisites: list[Prerequisite] = Field(default_factory=list)
    language: str | None = None
    ects_restriction_note: str | None = None
    offered_until: Semester | None = None
    predecessor_codes: list[str] = Field(default_factory=list)
    successor_codes: list[str] = Field(default_factory=list)
    source: SourceReference | None = None
    verification_status: VerificationStatus


class ModelTimetableEntry(Model):
    """A module placement extracted from an official model timetable."""

    module_code: str
    relative_semester: PositiveInt
    recommended: bool = False
    offered_terms: list[Literal["HS", "FS"]]
    source: SourceReference
    verification_status: VerificationStatus


class RuleParameters(Model):
    type: str


class MinEctsTotalParameters(RuleParameters):
    type: Literal["min_ects_total"]
    minimum_ects: PositiveInt


class CategoryEctsParameters(RuleParameters):
    type: Literal["min_ects_in_category", "max_ects_in_category"]
    category_id: str
    ects: PositiveInt


class RequiredModuleParameters(RuleParameters):
    type: Literal["required_module"]
    module_code: str


class RequiredAllMandatoryParameters(RuleParameters):
    type: Literal["required_all_mandatory"]
    category_ids: list[str] = Field(min_length=1)


class RequiredOneOfParameters(RuleParameters):
    type: Literal["required_one_of"]
    module_codes: list[str] = Field(min_length=1)


class MinModulesCategoryParameters(RuleParameters):
    type: Literal["min_modules_in_category"]
    category_id: str
    minimum_modules: PositiveInt


class PrerequisiteParameters(RuleParameters):
    type: Literal["prerequisite"]
    module_code: str
    prerequisite_module_codes: list[str] = Field(min_length=1)


class MaxAttemptsParameters(RuleParameters):
    type: Literal["max_attempts"]
    maximum_attempts: PositiveInt


class RetakeBudgetParameters(RuleParameters):
    type: Literal["retake_budget"]
    ects_budget: PositiveInt
    excluded_module_codes: list[str] = Field(default_factory=list)


class LevelGateParameters(RuleParameters):
    type: Literal["level_gate"]
    gated_level: Level
    required_level: Level
    mandatory_only: bool = True


class LevelDeadlineParameters(RuleParameters):
    type: Literal["level_deadline"]
    level: Level
    completed_semesters: PositiveInt
    mandatory_only: bool = True


class MinEctsInstitutionParameters(RuleParameters):
    type: Literal["min_ects_at_institution"]
    minimum_ects: PositiveInt


class MaxRecognizedParameters(RuleParameters):
    type: Literal["max_recognized_ects"]
    basis: str
    maximum_ects: PositiveInt
    study_modes: list[StudyMode] | None = None


class MaxStudyDurationParameters(RuleParameters):
    type: Literal["max_study_duration"]
    maximum_semesters: PositiveInt
    maximum_interruptions: int = Field(ge=0)
    study_modes: list[StudyMode] | None = None


class CompositeParameters(RuleParameters):
    type: Literal["composite"]
    operator: Literal["and", "or"]
    rule_ids: list[str] = Field(min_length=1)


class CustomNoteParameters(RuleParameters):
    type: Literal["custom_note"]
    note: str


RuleParametersUnion = Annotated[
    MinEctsTotalParameters
    | CategoryEctsParameters
    | RequiredModuleParameters
    | RequiredAllMandatoryParameters
    | RequiredOneOfParameters
    | MinModulesCategoryParameters
    | PrerequisiteParameters
    | MaxAttemptsParameters
    | RetakeBudgetParameters
    | LevelGateParameters
    | LevelDeadlineParameters
    | MinEctsInstitutionParameters
    | MaxRecognizedParameters
    | MaxStudyDurationParameters
    | CompositeParameters
    | CustomNoteParameters,
    Field(discriminator="type"),
]


class Rule(Model):
    id: str
    type: Literal[
        "min_ects_total",
        "min_ects_in_category",
        "max_ects_in_category",
        "required_module",
        "required_all_mandatory",
        "required_one_of",
        "min_modules_in_category",
        "prerequisite",
        "max_attempts",
        "retake_budget",
        "level_gate",
        "level_deadline",
        "min_ects_at_institution",
        "max_recognized_ects",
        "max_study_duration",
        "composite",
        "custom_note",
    ]
    parameters: RuleParametersUnion
    description: str
    source: SourceReference | None = None
    verification_status: VerificationStatus

    @model_validator(mode="after")
    def matching_type(self) -> Self:
        if self.type != self.parameters.type:
            raise ValueError("Rule type must match parameters.type.")
        return self


class CodeMapping(Model):
    source: Literal["mycampus", "timetable", "module_directory"]
    foreign_code: str
    source_document: SourceReference
    curriculum_code: str | None = None
    evidence: str
    valid_from: date | None = None
    valid_until: date | None = None
    verification_status: VerificationStatus


class CodeMappingsFile(Model):
    mappings: list[CodeMapping]


class Program(Model):
    id: str
    name: str
    specialization: str | None = None
    degree: str
    total_ects: PositiveInt
    intake_year: int
    study_modes: dict[StudyMode, StudyModeDuration]
    regulation_version_id: str
    categories: list[ModuleCategory]
    modules: list[Module]
    rules: list[Rule]
    model_timetables: dict[StudyMode, dict[Literal["HS", "FS"], list[ModelTimetableEntry]]] = Field(
        default_factory=dict
    )


class StudentProfile(Model):
    university_id: str
    program_id: str
    intake_year: int
    study_mode: StudyMode
    start_semester: Semester
    regulation_version_id: str
    language: Literal["en", "de"]
    interruption_semesters: list[Semester] = Field(default_factory=list)


class CreditAttempt(Model):
    module_code: str
    semester: Semester
    ects: PositiveInt
    grade: Grade | Literal["pass", "fail"] | None = None
    passed: bool
    attempt: PositiveInt
    forced_category_id: str | None = None
    forced_category_reason: str | None = None
    recognized_external: bool = False
    source: SourceReference
    verification_status: VerificationStatus
    mapping_verification_status: VerificationStatus | None = None


class RecognizedCredit(Model):
    id: str
    module_code: str | None = None
    category_id: str | None = None
    ects: PositiveInt
    basis: str
    reason: str | None = None
    decision_document: SourceReference
    decision_date: date | None = None
    status: Literal["confirmed", "provisional"]
    open_issue: str | None = None


class CreditsFile(Model):
    credits: list[CreditAttempt] = Field(default_factory=list)
    recognized_credits: list[RecognizedCredit] = Field(default_factory=list)


class PlanItem(Model):
    module_code: str | None = None
    target_semester: Semester
    source: SourceReference | None = None
    status: Literal["passed", "running", "planned", "failed", "retake"]
    origin: Literal["credits", "generated", "manual"] = "generated"
    note: str | None = None
    attempt: PositiveInt | None = None
    mapping_verification_status: VerificationStatus | None = None


class PlanPlaceholder(Model):
    category_id: str
    ects_needed: PositiveInt
    suggested_module_codes: list[str] = Field(default_factory=list)
    target_semester: Semester
    origin: Literal["generated", "manual"] = "generated"
    note: str | None = None


class PlanFile(Model):
    planned_modules: list[PlanItem] = Field(default_factory=list)
    placeholders: list[PlanPlaceholder] = Field(default_factory=list)


class ChecklistItem(Model):
    rule_id: str
    checked: bool
    checked_on: date | None = None
    note: str | None = None


class ChecklistFile(Model):
    items: list[ChecklistItem] = Field(default_factory=list)

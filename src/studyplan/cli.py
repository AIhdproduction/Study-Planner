"""Typer command line interface for local StudyPlan state."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

import typer
from pydantic import ValidationError
from rich.console import Console
from selectolax.lexbor import LexborHTMLParser

from studyplan.engine.matching import match_code
from studyplan.engine.plan import current_semester, generate_plan, plan_report, semester_key
from studyplan.engine.rules import CheckResult, evaluate
from studyplan.exporters.excel import export_workbook
from studyplan.i18n import (
    category_label,
    goal_label,
    localized_text,
    message,
    status_label,
    without_goal_prefix,
)
from studyplan.io.yaml_store import (
    ProfileRepository,
    load_model,
    load_yaml,
    save_model,
    validate_yaml,
)
from studyplan.models import (
    ChecklistFile,
    CodeMappingsFile,
    CreditAttempt,
    CreditsFile,
    PlanFile,
    PlanItem,
    Program,
    RecognizedCredit,
    SourceReference,
    StudentProfile,
)
from studyplan.models.core import Semester, University

app = typer.Typer(no_args_is_help=True, add_completion=False)
credits_app = typer.Typer(
    no_args_is_help=True, help="Manage passed, failed, and recognized credits."
)
plan_app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=False,
    help="Check and edit the saved semester plan.",
)
app.add_typer(credits_app, name="credits")
app.add_typer(plan_app, name="plan")
DISCLAIMER = (
    "Not legally binding. The official study regulations and the program management decide."
)
ROOT = Path.cwd()
STUDY_DIR: Path | None = None
PROFILES_DIR: Path | None = None
LANGUAGE: str | None = None
console = Console(width=200)


@app.callback()
def configure(
    study_dir: Annotated[
        Path | None, typer.Option("--study-dir", help="Directory with study files.")
    ] = None,
    profiles_dir: Annotated[
        Path | None,
        typer.Option("--profiles-dir", help="Directory with university profiles."),
    ] = None,
    lang: Annotated[str | None, typer.Option("--lang", help="Output language: en or de.")] = None,
) -> None:
    """Configure the local study state and profile directories."""
    global LANGUAGE, PROFILES_DIR, STUDY_DIR
    STUDY_DIR = study_dir or Path(os.environ.get("STUDYPLAN_STUDY_DIR", ROOT / "my_study"))
    PROFILES_DIR = profiles_dir or Path(os.environ.get("STUDYPLAN_PROFILES_DIR", ROOT / "profiles"))
    LANGUAGE = lang


def _profiles() -> ProfileRepository:
    return ProfileRepository(PROFILES_DIR or ROOT / "profiles")


def _study() -> Path:
    return STUDY_DIR or ROOT / "my_study"


def _out(data: Any, as_json: bool = False) -> None:
    if as_json:
        typer.echo(json.dumps(data, ensure_ascii=False, default=str))
        return
    elif isinstance(data, str):
        console.print(data)
    else:
        console.print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    console.print(DISCLAIMER)


def _language(override: str | None = None) -> str:
    """Choose the explicit language or the initialized profile language."""
    if override or LANGUAGE:
        return override or LANGUAGE or "en"
    profile = _study() / "profile.yaml"
    if profile.exists():
        try:
            return load_model(profile, StudentProfile).language
        except Exception:
            pass
    return os.environ.get("STUDYPLAN_LANG") or "en"


def _student() -> StudentProfile:
    path = _study() / "profile.yaml"
    if not path.exists():
        typer.echo("No study profile found. Run `studyplan init` first.", err=True)
        raise typer.Exit(2)
    issues = validate_yaml(path, StudentProfile)
    if issues:
        issue = issues[0]
        typer.echo(f"{issue.file}:{issue.line or 1}: {issue.message} Hint: {issue.hint}", err=True)
        raise typer.Exit(2)
    return load_model(path, StudentProfile)


def _program() -> Program:
    student = _student()
    return _profiles().program(student.university_id, student.program_id)


def _credits() -> CreditsFile:
    return load_model(_study() / "credits.yaml", CreditsFile)


def _resolve(program: Program, university_id: str, code: str) -> str | None:
    mappings = _profiles().mappings(university_id).mappings
    return match_code(program, mappings, "mycampus", code).curriculum_code


def _credit_valid(
    program: Program, credits: CreditsFile, item: CreditAttempt, *, old: int | None = None
) -> None:
    module = next((module for module in program.modules if module.code == item.module_code), None)
    if module is None:
        raise typer.BadParameter(f"Unknown module code: {item.module_code}")
    if item.ects != module.ects:
        raise typer.BadParameter(f"ECTS must be {module.ects} for {module.code}.")
    for index, existing in enumerate(credits.credits):
        if (
            index != old
            and existing.module_code == item.module_code
            and existing.attempt == item.attempt
        ):
            raise typer.BadParameter("Duplicate module attempt.")


def _plan_file() -> PlanFile:
    return load_model(_study() / "plan.yaml", PlanFile)


def _plan_valid_code(program: Program, code: str) -> None:
    if code not in {module.code for module in program.modules}:
        raise typer.BadParameter(f"Unknown module code: {code}")


@app.command()
def guide(
    lang: Annotated[str | None, typer.Option("--lang", help="Language for the guide.")] = None,
    output: Annotated[
        Path | None, typer.Option("--output", help="Write the guide to this file.")
    ] = None,
) -> None:
    """Print the complete student workflow so it can be copied."""
    selected_lang = _language(lang)
    text = message(selected_lang, "guide")
    console.print(text)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(f"{text}\n", encoding="utf-8-sig")
        console.print(str(output))


INBOX_SPEC: list[dict[str, Any]] = [
    {
        "id": "regulations",
        "folder": "regulations",
        "extensions": (".pdf",),
        "importance": "optional",
        "purpose_key": "inbox_regulations",
    },
    {
        "id": "model_timetable",
        "folder": "timetable",
        "extensions": (".pdf", ".ics", ".csv", ".xlsx"),
        "importance": "optional",
        "purpose_key": "inbox_model_timetable",
    },
    {
        "id": "mycampus_page",
        "folder": "transcript",
        "extensions": (".html", ".htm"),
        "importance": "recommended",
        "purpose_key": "inbox_mycampus_page",
    },
    {
        "id": "transcript_pdf",
        "folder": "transcript",
        "extensions": (".pdf",),
        "importance": "optional",
        "purpose_key": "inbox_transcript_pdf",
    },
    {
        "id": "recognition",
        "folder": "recognition",
        "extensions": (".pdf",),
        "importance": "optional",
        "purpose_key": "inbox_recognition",
    },
    {
        "id": "module_descriptions",
        "folder": "modules",
        "extensions": (".pdf", ".html", ".htm"),
        "importance": "optional",
        "purpose_key": "inbox_module_descriptions",
    },
]


@app.command()
def doctor(
    lang: Annotated[str | None, typer.Option("--lang", help="Output language: en or de.")] = None,
    inbox: Annotated[bool, typer.Option("--inbox", help="Inspect document inbox folders.")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    """Check the local folders and inbox documents required by Study Planner."""
    required = {"profiles": _profiles().root, "my_study": _study()}
    missing = [name for name, path in required.items() if not path.exists()]
    selected_lang = _language(lang)
    if not inbox:
        _out(
            message(selected_lang, "environment_ready")
            if not missing
            else f"Missing folders: {', '.join(missing)}"
        )
        if missing:
            raise typer.Exit(1)
        return

    if missing:
        _out(f"Missing folders: {', '.join(missing)}")
        raise typer.Exit(1)

    inbox_dir = _study() / "inbox"
    items: list[dict[str, Any]] = []
    for spec in INBOX_SPEC:
        folder_path = inbox_dir / spec["folder"]
        count = 0
        if folder_path.is_dir():
            for entry in folder_path.iterdir():
                if (
                    entry.is_file()
                    and not entry.name.startswith(".")
                    and entry.suffix.lower() in spec["extensions"]
                ):
                    count += 1
        items.append(
            {
                "id": spec["id"],
                "folder": spec["folder"],
                "status": "present" if count > 0 else "missing",
                "count": count,
                "importance": spec["importance"],
                "purpose": message(selected_lang, spec["purpose_key"]),
            }
        )

    missing_recommended = [
        item["id"]
        for item in items
        if item["importance"] == "recommended" and item["status"] == "missing"
    ]
    profile_exists = (_study() / "profile.yaml").is_file()

    if as_json:
        _out(
            {
                "items": items,
                "missing_recommended": missing_recommended,
                "profile_exists": profile_exists,
            },
            as_json=True,
        )
        return

    lines: list[str] = []
    for item in items:
        status_text = status_label(selected_lang, item["status"])
        if item["count"] > 0:
            lines.append(f"{item['purpose']}: {status_text} ({item['count']})")
        else:
            lines.append(f"{item['purpose']}: {status_text}")
    if any(item["status"] == "missing" for item in items):
        lines.append(message(selected_lang, "inbox_guide_hint"))

    _out("\n".join(lines))


@app.command()
def profiles(
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """List the available universities and programs."""
    data: list[dict[str, Any]] = []
    for path in _profiles().root.glob("*/university.yaml"):
        university = load_model(path, University)
        programs = [load_model(file, Program) for file in (path.parent / "programs").glob("*.yaml")]
        data.append(
            {
                "id": university.id,
                "name": university.name,
                "programs": [
                    {
                        "id": program.id,
                        "name": program.name,
                        "specialization": program.specialization,
                        "intake_year": program.intake_year,
                        "study_modes": sorted(program.study_modes),
                    }
                    for program in programs
                ],
            }
        )
    _out(data, as_json)


@app.command()
def modules(
    search: str | None = typer.Option(None, "--search", help="Find modules by code or title."),
    category: str | None = typer.Option(None, "--category", help="Filter by category ID."),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """List modules in the selected program."""
    program = _program()
    selected = [
        module
        for module in program.modules
        if (not search or search.lower() in f"{module.code} {module.title}".lower())
        and (not category or category in module.eligible_category_ids)
    ]
    data = [module.model_dump(mode="json") for module in selected]
    _out(data, as_json)


@app.command()
def init(
    university: str = typer.Option(..., help="University profile ID."),
    program: str = typer.Option(..., help="Program profile ID."),
    intake_year: int = typer.Option(..., help="Year the student started."),
    study_mode: str = typer.Option(..., help="Study mode from the program profile."),
    start_semester: str = typer.Option(..., help="First semester, for example HS25."),
    interruptions: list[str] | None = typer.Option(None, help="Interruption semesters."),  # noqa: B008
    lang: str = typer.Option("de", help="Preferred output language: en or de."),
) -> None:
    """Create a new study profile and empty state files."""
    profile_path = _study() / "profile.yaml"
    if profile_path.exists():
        raise typer.BadParameter("my_study/profile.yaml already exists; init never overwrites it.")
    try:
        selected = _profiles().program(university, program)
    except FileNotFoundError:
        available = [path.name for path in _profiles().root.glob("*/university.yaml")]
        typer.echo(
            f"Unknown university or program. Available universities: {', '.join(available)}.",
            err=True,
        )
        raise typer.Exit(2) from None
    if intake_year != selected.intake_year or study_mode not in selected.study_modes:
        raise typer.BadParameter(
            "The selected intake year or study mode is unavailable for this program."
        )
    student = StudentProfile(
        university_id=university,
        program_id=program,
        intake_year=intake_year,
        study_mode=study_mode,
        start_semester=Semester(start_semester),
        regulation_version_id=selected.regulation_version_id,
        language=lang,
        interruption_semesters=[Semester(value) for value in interruptions or []],
    )
    for name in ["imports", "logs", "backups", "output"]:
        (_study() / name).mkdir(parents=True, exist_ok=True)
    save_model(profile_path, student)
    save_model(_study() / "credits.yaml", CreditsFile())
    save_model(_study() / "plan.yaml", PlanFile())
    save_model(_study() / "checklist.yaml", ChecklistFile())
    _out(message(lang, "profile_created"))


@app.command()
def validate(
    path: Annotated[
        Path | None, typer.Option("--path", help="Validate only this YAML file.")
    ] = None,
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Validate study files and profile data."""
    paths = (
        [path] if path else list(_study().glob("*.yaml")) + list(_profiles().root.glob("**/*.yaml"))
    )
    models = {
        "profile.yaml": StudentProfile,
        "credits.yaml": CreditsFile,
        "plan.yaml": PlanFile,
        "checklist.yaml": ChecklistFile,
        "university.yaml": University,
        "code_mapping.yaml": CodeMappingsFile,
    }
    issues = []
    for file in paths:
        model = models.get(file.name, Program if file.parent.name == "programs" else None)
        if model:
            issues.extend(validate_yaml(file, model))
    result = [
        {"file": str(issue.file), "line": issue.line, "message": issue.message, "hint": issue.hint}
        for issue in issues
    ]
    _out(result if issues else message(_language(), "validation_success"), as_json)
    if issues:
        raise typer.Exit(1)


@app.command()
def schema() -> None:
    """Export JSON Schemas for the supported data files."""
    destination = ROOT / "schemas"
    destination.mkdir(exist_ok=True)
    for model in [
        University,
        Program,
        StudentProfile,
        CreditsFile,
        PlanFile,
        ChecklistFile,
        CodeMappingsFile,
    ]:
        (destination / f"{model.__name__.lower()}.json").write_text(
            json.dumps(model.model_json_schema(), indent=2), encoding="utf-8"
        )
    (destination / "check_result.schema.json").write_text(
        json.dumps(CheckResult.model_json_schema(), indent=2), encoding="utf-8"
    )
    _out("JSON Schemas exported.")


@app.command()
def check(
    mode: str = typer.Option("current", "--mode", help="Evaluation mode: current or forecast."),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    lang: str | None = typer.Option(None, "--lang", help="Output language: en or de."),
) -> None:
    """Evaluate thesis admission and graduation requirements."""
    if mode not in {"current", "forecast"}:
        raise typer.BadParameter("Mode must be current or forecast.")
    program = _program()
    result = evaluate(
        program,
        _student(),
        _credits(),
        load_model(_study() / "plan.yaml", PlanFile),
        load_model(_study() / "checklist.yaml", ChecklistFile),
        mode,
    )
    if as_json:
        _out(result.model_dump(mode="json"), True)
        return
    language = _language(lang)
    category_names = {
        category.id: category_label(language, category.official_name)
        for category in program.categories
    }
    lines = [
        f"{message(language, 'overall_verdict')}: {status_label(language, result.verdict)}",
        f"{message(language, 'goals')}:",
    ]
    lines.extend(
        f"- {goal_label(language, goal.id)}: {status_label(language, goal.verdict)}"
        for goal in result.goals
    )
    lines.append(f"{message(language, 'category_ects')}:")
    targets = {
        rule.parameters.category_id: rule.parameters.ects
        for rule in program.rules
        if rule.parameters.type == "min_ects_in_category"
    }
    lines.extend(
        f"- {category_names.get(category, category)}: {ects} / {targets.get(category, 0)}"
        for category, ects in sorted(result.category_ects.items())
    )
    lines.append(f"{message(language, 'total_ects')}: {result.total_ects}")
    if result.gaps:
        lines.append(f"{message(language, 'gaps')}:")
        rule_gaps = {item["rule_id"]: item["text"] for item in result.gaps}
        for goal in result.goals:
            open_rules = [
                localized_text(language, without_goal_prefix(rule_gaps[rule_id]))
                for rule_id in goal.rule_ids
                if rule_id in rule_gaps
            ]
            if open_rules:
                lines.append(f"- {goal_label(language, goal.id)}:")
                lines.extend(f"  - {item}" for item in open_rules)
        ungrouped = [
            item["text"]
            for item in result.gaps
            if item["rule_id"]
            not in {rule_id for goal in result.goals for rule_id in goal.rule_ids}
        ]
        lines.extend(f"- {localized_text(language, item)}" for item in ungrouped)
    provisional = [rule for rule in result.rules if rule.status == "provisional"]
    if provisional:
        lines.append(f"{message(language, 'provisional')}:")
        lines.extend(
            f"- {rule.id}: "
            + ", ".join(localized_text(language, item) for item in rule.provisional_reasons)
            for rule in provisional
        )
    if result.manual_checklist:
        lines.append(f"{message(language, 'manual_checklist')}:")
        manual_rules = {rule.id: rule for rule in result.rules if rule.type == "custom_note"}
        lines.extend(
            f"- {item.rule_id}: "
            + (message(language, "checked") if item.checked else message(language, "open"))
            + (
                f" — {localized_text(language, manual_rules[item.rule_id].gap.text)}"
                if item.rule_id in manual_rules and manual_rules[item.rule_id].gap
                else ""
            )
            for item in result.manual_checklist
        )
    if result.allocation:
        lines.append(f"{message(language, 'allocation')}:")
        lines.extend(
            f"- {item.module_code or item.recognized_credit_id}: "
            f"{item.allocated_category_id or 'unallocated'} ({item.ects_counted} ECTS)"
            for item in result.allocation
        )
    _out("\n".join(lines))


@credits_app.command("list")
def credits_list(
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """List all saved credits and recognitions."""
    _out(_credits().model_dump(mode="json"), as_json)


@credits_app.command("add")
def credits_add(
    code: str = typer.Option(..., help="Module code."),
    semester: str = typer.Option(..., help="Semester, for example HS25."),
    ects: int = typer.Option(..., help="ECTS value from the curriculum."),
    grade: str | None = typer.Option(None, help="Grade A-F, pass, or fail."),
    attempt: int = typer.Option(1, help="Attempt number for this module."),
) -> None:
    """Add a passed or failed module attempt."""
    program, store = _program(), _credits()
    mapped = _resolve(program, _student().university_id, code)
    if not mapped:
        raise typer.BadParameter(f"Unknown module code: {code}")
    grade_value = grade.upper() if grade and grade.lower() not in {"pass", "fail"} else grade
    if grade_value not in {"A", "B", "C", "D", "E", "F", "pass", "fail"}:
        raise typer.BadParameter("Grade must be A-F, pass, or fail.")
    item = CreditAttempt(
        module_code=mapped,
        semester=Semester(semester),
        ects=ects,
        grade=grade_value,
        passed=grade_value not in {"F", "fail"},
        attempt=attempt,
        source=SourceReference(document="manual entry"),
        verification_status="edited",
    )
    _credit_valid(program, store, item)
    store.credits.append(item)
    save_model(_study() / "credits.yaml", store)
    _out(message(_language(), "credit_added"))


@credits_app.command("remove")
def credits_remove(
    code: str = typer.Option(..., help="Module code."),
    attempt: int = typer.Option(..., help="Attempt number to remove."),
) -> None:
    """Remove one saved module attempt."""
    store = _credits()
    remaining = [
        item for item in store.credits if not (item.module_code == code and item.attempt == attempt)
    ]
    if len(remaining) == len(store.credits):
        raise typer.BadParameter("Credit attempt was not found.")
    store.credits = remaining
    save_model(_study() / "credits.yaml", store)
    _out(message(_language(), "credit_removed"))


@credits_app.command("edit")
def credits_edit(
    code: str = typer.Option(..., help="Module code."),
    attempt: int = typer.Option(..., help="Attempt number to edit."),
    semester: str | None = typer.Option(None, help="Replacement semester."),
    ects: int | None = typer.Option(None, help="Replacement ECTS value."),
    grade: str | None = typer.Option(None, help="Replacement grade."),
) -> None:
    """Edit one saved module attempt."""
    store, program = _credits(), _program()
    index = next(
        (
            i
            for i, item in enumerate(store.credits)
            if item.module_code == code and item.attempt == attempt
        ),
        None,
    )
    if index is None:
        raise typer.BadParameter("Credit attempt was not found.")
    old = store.credits[index]
    new_grade = (
        grade.upper() if grade and grade.lower() not in {"pass", "fail"} else (grade or old.grade)
    )
    item = old.model_copy(
        update={
            "semester": Semester(semester) if semester else old.semester,
            "ects": ects or old.ects,
            "grade": new_grade,
            "passed": new_grade not in {"F", "fail"},
        }
    )
    _credit_valid(program, store, item, old=index)
    store.credits[index] = item
    save_model(_study() / "credits.yaml", store)
    _out(message(_language(), "credit_updated"))


recognize_app = typer.Typer(
    no_args_is_help=True, help="Manage credits recognized from earlier education."
)
credits_app.add_typer(recognize_app, name="recognize")


def _recognized_valid(program: Program, item: RecognizedCredit, store: CreditsFile) -> None:
    category_ids = {category.id for category in program.categories}
    module_codes = {module.code for module in program.modules}
    if item.category_id and item.category_id not in category_ids:
        raise typer.BadParameter(f"Unknown category: {item.category_id}")
    if item.module_code and item.module_code not in module_codes:
        raise typer.BadParameter(f"Unknown module code: {item.module_code}")
    if any(existing.id == item.id for existing in store.recognized_credits):
        raise typer.BadParameter(f"Recognized credit id already exists: {item.id}")


@recognize_app.command("add")
def recognized_add(
    ects: int = typer.Option(..., help="Recognized ECTS."),
    basis: str = typer.Option(..., help="Basis for the recognition."),
    document: str = typer.Option(..., help="Recognition decision document name."),
    category: str | None = typer.Option(None, help="Category ID for a lump-sum recognition."),
    no_category: bool = typer.Option(False, "--no-category", help="Record no category assignment."),
    module_code: str | None = typer.Option(None, help="Curriculum module code, if recognized."),
    date: str | None = typer.Option(None, help="Decision date in YYYY-MM-DD."),
    status: str = typer.Option("confirmed", help="Recognition status: confirmed or provisional."),
    open_issue: str | None = typer.Option(None, help="Reason the recognition remains open."),
) -> None:
    """Add a recognized credit from earlier education."""
    if no_category and category:
        raise typer.BadParameter("Use either --category or --no-category, not both.")
    if status not in {"confirmed", "provisional"}:
        raise typer.BadParameter("Status must be confirmed or provisional.")
    parsed_date = None
    if date:
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError as error:
            raise typer.BadParameter("Date must use YYYY-MM-DD.") from error
    store, program = _credits(), _program()
    item = RecognizedCredit(
        id=uuid4().hex,
        module_code=module_code,
        category_id=None if no_category else category,
        ects=ects,
        basis=basis,
        decision_document=SourceReference(document=document),
        decision_date=parsed_date,
        status=status,
        open_issue=open_issue,
    )
    _recognized_valid(program, item, store)
    store.recognized_credits.append(item)
    save_model(_study() / "credits.yaml", store)
    _out(f"{message(_language(), 'recognition_added')} ID: {item.id}")


@recognize_app.command("list")
def recognized_list(
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """List all recognized credits."""
    _out([item.model_dump(mode="json") for item in _credits().recognized_credits], as_json)


@recognize_app.command("remove")
def recognized_remove(id: str = typer.Option(..., help="Recognized credit ID.")) -> None:
    """Remove one recognized credit."""
    store = _credits()
    recognized = [item for item in store.recognized_credits if item.id != id]
    if len(recognized) == len(store.recognized_credits):
        raise typer.BadParameter("Recognized credit was not found.")
    store.recognized_credits = recognized
    save_model(_study() / "credits.yaml", store)
    _out(message(_language(), "recognition_removed"))


def _text_after(node: Any, label: str) -> str | None:
    for row in node.css("tr"):
        cells = [cell.text(strip=True) for cell in row.css("th,td")]
        if cells and cells[0].lower().startswith(label.lower()):
            return " ".join(cells[1:])
    return None


@credits_app.command("import-mycampus")
def import_mycampus(
    file: Annotated[Path, typer.Argument(help="Saved MyCampus Meine Anmeldungen HTML file.")],
    apply: bool = typer.Option(False, help="Save new parsed entries instead of a dry run."),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Import a saved MyCampus page locally, without a network connection."""
    if not file.exists():
        raise typer.BadParameter(f"File not found: {file}")
    document = LexborHTMLParser(file.read_text(encoding="utf-8", errors="replace"))
    program, student, store = _program(), _student(), _credits()
    mappings = _profiles().mappings(student.university_id).mappings
    results: list[dict[str, Any]] = []
    for block in document.css("li"):
        if len(block.css("h2")) != 1:
            continue
        raw_code = _text_after(block, "Nummer")
        ects_text = _text_after(block, "ECTS-Punkte")
        grade_text = _text_after(block, "Bewertung")
        if not raw_code:
            continue
        raw_code = raw_code.split()[0]
        run = re.search(r"\.([HF]\d{4})$", raw_code)
        if not ects_text:
            results.append({"code": raw_code, "status": "ignored_event"})
            continue
        ects_match = re.search(r"\d+", ects_text)
        if not ects_match or not run:
            results.append({"code": raw_code, "status": "unmapped"})
            continue
        match = match_code(program, mappings, "mycampus", raw_code)
        semester = str(Semester.from_mycampus_run(run.group(1)))
        grade = re.search(r"\b([A-F])\b", grade_text or "")
        if match.curriculum_code is None:
            results.append(
                {
                    "code": raw_code,
                    "stem": match.stem,
                    "semester": semester,
                    "status": match.status,
                }
            )
            continue
        mapped = match.curriculum_code
        if not grade:
            results.append(
                {
                    "code": raw_code,
                    "module_code": mapped,
                    "semester": semester,
                    "status": "running",
                    "mapping_verification_status": match.verification_status,
                }
            )
            continue
        attempts = [item for item in store.credits if item.module_code == mapped]
        status = (
            "already_present"
            if any(item.module_code == mapped and item.semester == semester for item in attempts)
            else "new"
        )
        result = {
            "code": raw_code,
            "module_code": mapped,
            "semester": semester,
            "attempt": 0,
            "ects": int(ects_match.group()),
            "grade": grade.group(1),
            "passed": grade.group(1) != "F",
            "status": status,
            "mapping_verification_status": match.verification_status,
        }
        results.append(result)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        if row.get("status") in {"new", "already_present"}:
            grouped.setdefault(row["module_code"], []).append(row)
    for module_code, rows in grouped.items():
        existing = sum(item.module_code == module_code for item in store.credits)
        for attempt, row in enumerate(
            sorted(rows, key=lambda item: Semester(item["semester"]).sort_key), existing + 1
        ):
            row["attempt"] = attempt
    plan = load_model(_study() / "plan.yaml", PlanFile) if apply else None
    for row in results:
        if row["status"] == "running" and apply and plan is not None:
            if not any(
                item.module_code == row["module_code"] and item.target_semester == row["semester"]
                for item in plan.planned_modules
            ):
                plan.planned_modules.append(
                    PlanItem(
                        module_code=row["module_code"],
                        target_semester=Semester(row["semester"]),
                        status="running",
                        origin="credits",
                        source=SourceReference(document=file.name),
                        mapping_verification_status=row.get("mapping_verification_status"),
                    )
                )
        if apply and row["status"] == "new":
            item = CreditAttempt(
                module_code=row["module_code"],
                semester=Semester(row["semester"]),
                ects=row["ects"],
                grade=row["grade"],
                passed=row["passed"],
                attempt=row["attempt"],
                source=SourceReference(document=file.name),
                verification_status="unverified",
                mapping_verification_status=row.get("mapping_verification_status"),
            )
            _credit_valid(program, store, item)
            store.credits.append(item)
    if apply:
        save_model(_study() / "credits.yaml", store)
        assert plan is not None
        save_model(_study() / "plan.yaml", plan)
    _out(results, as_json)


@plan_app.callback()
def plan(
    ctx: typer.Context,
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Check the saved semester plan."""
    if ctx.invoked_subcommand is not None:
        return
    report = plan_report(
        _program(),
        _student(),
        _credits(),
        _plan_file(),
        load_model(_study() / "checklist.yaml", ChecklistFile),
    )
    if as_json:
        _out(report, True)
        return
    lines = ["Semester plan:"]
    for semester, row in report["semesters"].items():
        lines.append(
            f"- {semester}: {row['planned_ects']} ECTS planned, "
            f"{row['cumulative_ects']} ECTS cumulative"
        )
    admission = report["earliest_thesis_admission_semester"] or "unknown"
    if admission != "unknown" and _language() == "de":
        admission_value = Semester(admission)
        year, term = admission_value.sort_key
        previous = Semester(f"{'HS' if term == 0 else 'FS'}{(year - (term == 0)) % 100:02d}")
        lines.append(
            f"Thesis frühestens: {admission} "
            f"({report['thesis_admission_threshold']} ECTS erreicht Ende {previous})"
        )
    else:
        lines.append(f"Earliest thesis admission semester: {admission}")
    lines.append(
        f"Earliest graduation semester: {report['earliest_graduation_semester'] or 'unknown'}"
    )
    lines.extend(f"- Warning: {item}" for item in report["violations"])
    _out("\n".join(lines))


@plan_app.command("generate")
def plan_generate(
    current: str | None = typer.Option(
        None, "--current-semester", help="Current semester, for example HS25."
    ),
    force: bool = typer.Option(False, "--force", help="Replace generated plan items."),
    as_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Generate a deterministic first-semester plan from credits and the model timetable."""
    now = Semester(current) if current else current_semester()
    generated, warnings = generate_plan(
        _program(),
        _student(),
        _credits(),
        _plan_file(),
        load_model(_study() / "checklist.yaml", ChecklistFile),
        now,
        force,
    )
    save_model(_study() / "plan.yaml", generated)
    payload = {"plan": generated.model_dump(mode="json"), "warnings": warnings}
    _out(
        payload
        if as_json
        else "Study plan generated." + ("\n" + "\n".join(warnings) if warnings else ""),
        as_json,
    )


@plan_app.command("add")
def plan_add(
    code: str = typer.Option(..., "--code", help="Module code."),
    semester: str = typer.Option(..., "--semester", help="Target semester."),
    status: str = typer.Option("planned", "--status", help="Status: planned, running, or retake."),
    note: str | None = typer.Option(None, "--note", help="Optional note for this item."),
) -> None:
    """Add a manually controlled plan item."""
    if status not in {"planned", "running", "retake"}:
        raise typer.BadParameter("Status must be planned, running, or retake.")
    program, plan_file = _program(), _plan_file()
    _plan_valid_code(program, code)
    target = Semester(semester)
    if any(
        item.module_code == code and item.target_semester == target
        for item in plan_file.planned_modules
    ):
        raise typer.BadParameter("That module is already planned in this semester.")
    plan_file.planned_modules.append(
        PlanItem(
            module_code=code, target_semester=target, status=status, origin="manual", note=note
        )
    )
    save_model(_study() / "plan.yaml", plan_file)
    _out("Manual plan item added.")


@plan_app.command("move")
def plan_move(
    code: str = typer.Option(..., "--code", help="Module code."),
    semester: str = typer.Option(..., "--semester", help="New target semester."),
) -> None:
    """Move a module and mark the choice as manual."""
    target = Semester(semester)
    plan_file = _plan_file()
    candidates = [item for item in plan_file.planned_modules if item.module_code == code]
    if not candidates:
        raise typer.BadParameter("Plan item was not found.")
    item = max(candidates, key=lambda value: semester_key(value.target_semester))
    item.target_semester = target
    item.origin = "manual"
    save_model(_study() / "plan.yaml", plan_file)
    _out("Plan item moved.")


@plan_app.command("remove")
def plan_remove(code: str = typer.Option(..., "--code", help="Module code.")) -> None:
    """Remove a plan item selected by module code."""
    plan_file = _plan_file()
    before = len(plan_file.planned_modules)
    plan_file.planned_modules = [
        item for item in plan_file.planned_modules if item.module_code != code
    ]
    if len(plan_file.planned_modules) == before:
        raise typer.BadParameter("Plan item was not found.")
    save_model(_study() / "plan.yaml", plan_file)
    _out("Plan item removed.")


timetable_app = typer.Typer(no_args_is_help=True, help="Reserve timetable functions for phase 4.")
app.add_typer(timetable_app, name="timetable")


@timetable_app.command("import")
def timetable_import(
    file: Annotated[Path, typer.Argument(help="Timetable file to import.")],
) -> None:
    """Reserve timetable import for phase 4."""
    _ = file
    _out("Timetable import is not available yet.")


@app.command()
def excel(
    mode: str = typer.Option("current", "--mode", help="Evaluation mode: current or forecast."),
    lang: str | None = typer.Option(None, "--lang", help="Workbook language: en or de."),
) -> None:
    """Export the selected engine view as a reviewable Excel workbook."""
    if mode not in {"current", "forecast"}:
        raise typer.BadParameter("Mode must be current or forecast.")
    program, student, store = _program(), _student(), _credits()
    result = evaluate(
        program,
        student,
        store,
        load_model(_study() / "plan.yaml", PlanFile),
        load_model(_study() / "checklist.yaml", ChecklistFile),
        mode,
    )
    output = _study() / "output" / f"study_plan_{datetime.now().date().isoformat()}.xlsx"
    export_workbook(
        output,
        program,
        store,
        result,
        _language(lang),
        load_model(_study() / "plan.yaml", PlanFile),
        student,
        load_model(_study() / "checklist.yaml", ChecklistFile),
    )
    _out(str(output))


_BACKUP_FILES = ("profile.yaml", "credits.yaml", "plan.yaml", "checklist.yaml")
_BACKUP_MODELS = {
    "profile.yaml": StudentProfile,
    "credits.yaml": CreditsFile,
    "plan.yaml": PlanFile,
    "checklist.yaml": ChecklistFile,
}


@app.command()
def backup() -> None:
    """Write a portable JSON snapshot of the complete student state."""
    missing = [name for name in _BACKUP_FILES if not (_study() / name).exists()]
    if missing:
        raise typer.BadParameter(f"Cannot create backup; missing: {', '.join(missing)}")
    payload = {name.removesuffix(".yaml"): load_yaml(_study() / name) for name in _BACKUP_FILES}
    destination = _study() / "backups" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    _out(f"{message(_language(), 'backup_created')} {destination}")


@app.command()
def restore(
    file: Path,
    force: bool = typer.Option(False, "--force", help="Allow replacement of existing state files."),
) -> None:
    """Restore a validated backup without silently replacing existing state."""
    if not file.exists():
        raise typer.BadParameter(f"File not found: {file}")
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise typer.BadParameter(f"Invalid backup JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise typer.BadParameter("Backup must contain a JSON object.")
    models: dict[str, Any] = {}
    for name, model in _BACKUP_MODELS.items():
        key = name.removesuffix(".yaml")
        if key not in payload:
            raise typer.BadParameter(f"Backup is missing '{key}'.")
        try:
            models[name] = model.model_validate(payload[key])
        except ValidationError as error:
            raise typer.BadParameter(f"Backup field '{key}' is invalid: {error}") from error
    existing = [name for name in _BACKUP_FILES if (_study() / name).exists()]
    if existing and not force:
        raise typer.BadParameter(
            "Restore refuses to overwrite existing files without --force: " + ", ".join(existing)
        )
    for name, model in models.items():
        save_model(_study() / name, model)
    _out(message(_language(), "restored"))


def main() -> None:
    try:
        app()
    except (ValidationError, FileNotFoundError, OSError) as error:
        console.print(str(error), file=sys.stderr)
        raise typer.Exit(2) from error


if __name__ == "__main__":
    main()

"""Typer command line interface for local StudyPlan state."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import typer
from pydantic import ValidationError
from rich.console import Console
from selectolax.lexbor import LexborHTMLParser

from studyplan.engine.matching import match_code
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
credits_app = typer.Typer(no_args_is_help=True)
app.add_typer(credits_app, name="credits")
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
    study_dir: Path | None = typer.Option(None, "--study-dir"),  # noqa: B008
    profiles_dir: Path | None = typer.Option(None, "--profiles-dir"),  # noqa: B008
    lang: str | None = typer.Option(None, "--lang"),
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
    return load_model(profile, StudentProfile).language if profile.exists() else "en"


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


@app.command()
def doctor(lang: str | None = typer.Option(None, "--lang")) -> None:
    required = {"profiles": _profiles().root, "my_study": _study()}
    missing = [name for name, path in required.items() if not path.exists()]
    _out(
        message(_language(lang), "environment_ready")
        if not missing
        else f"Missing folders: {', '.join(missing)}"
    )
    if missing:
        raise typer.Exit(1)


@app.command()
def profiles(as_json: bool = typer.Option(False, "--json")) -> None:
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
    search: str | None = None,
    category: str | None = None,
    as_json: bool = typer.Option(False, "--json"),
) -> None:
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
    university: str = typer.Option(...),
    program: str = typer.Option(...),
    intake_year: int = typer.Option(...),
    study_mode: str = typer.Option(...),
    start_semester: str = typer.Option(...),
    interruptions: list[str] | None = typer.Option(None),  # noqa: B008
    lang: str = typer.Option("de"),
) -> None:
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
def validate(path: Path | None = None, as_json: bool = typer.Option(False, "--json")) -> None:
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
    mode: str = typer.Option("current", "--mode"),
    as_json: bool = typer.Option(False, "--json"),
    lang: str | None = typer.Option(None, "--lang"),
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
def credits_list(as_json: bool = typer.Option(False, "--json")) -> None:
    _out(_credits().model_dump(mode="json"), as_json)


@credits_app.command("add")
def credits_add(
    code: str = typer.Option(...),
    semester: str = typer.Option(...),
    ects: int = typer.Option(...),
    grade: str | None = typer.Option(None),
    attempt: int = typer.Option(1),
) -> None:
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
def credits_remove(code: str = typer.Option(...), attempt: int = typer.Option(...)) -> None:
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
    code: str = typer.Option(...),
    attempt: int = typer.Option(...),
    semester: str | None = None,
    ects: int | None = None,
    grade: str | None = None,
) -> None:
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


recognize_app = typer.Typer(no_args_is_help=True)
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
    ects: int = typer.Option(...),
    basis: str = typer.Option(...),
    document: str = typer.Option(...),
    category: str | None = typer.Option(None),
    no_category: bool = typer.Option(False, "--no-category"),
    module_code: str | None = typer.Option(None),
    date: str | None = typer.Option(None),
    status: str = typer.Option("confirmed"),
    open_issue: str | None = typer.Option(None),
) -> None:
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
def recognized_list(as_json: bool = typer.Option(False, "--json")) -> None:
    _out([item.model_dump(mode="json") for item in _credits().recognized_credits], as_json)


@recognize_app.command("remove")
def recognized_remove(id: str = typer.Option(...)) -> None:
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
    file: Path, apply: bool = typer.Option(False), as_json: bool = typer.Option(False, "--json")
) -> None:
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


@app.command()
def excel(
    mode: str = typer.Option("current", "--mode"),
    lang: str | None = typer.Option(None, "--lang"),
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
    export_workbook(output, program, store, result, _language(lang))
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
def restore(file: Path, force: bool = typer.Option(False, "--force")) -> None:
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

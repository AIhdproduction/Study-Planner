"""Excel workbook export for a computed StudyPlan result."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

from studyplan.engine.plan import plan_report, semester_key
from studyplan.engine.rules import CheckResult
from studyplan.i18n import category_label, goal_label, localized_text, message, status_label
from studyplan.models import ChecklistFile, CreditsFile, PlanFile, Program, Semester, StudentProfile

VALIDATION_LAST_ROW = 1000


def _header(sheet, values: list[str]) -> None:
    sheet.append(values)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"


def _widths(sheet) -> None:
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(
            48, max(14, max(len(str(cell.value or "")) for cell in column) + 2)
        )


def _sheet_range(sheet_name: str, column: str, last_row: int) -> str:
    """Create an Excel-safe range formula, including localized sheet names."""
    escaped = sheet_name.replace("'", "''")
    return f"='{escaped}'!${column}$2:${column}${last_row}"


def export_workbook(
    path: Path,
    program: Program,
    credits: CreditsFile,
    result: CheckResult,
    language: str,
    plan: PlanFile | None = None,
    student: StudentProfile | None = None,
    checklist: ChecklistFile | None = None,
) -> Path:
    """Write a reviewable workbook; calculated verdict values originate from the engine."""
    workbook = Workbook()
    overview = workbook.active
    overview.title = message(language, "overview")
    overview.append([message(language, "overall_verdict"), status_label(language, result.verdict)])
    overview.append([message(language, "computed"), date.today().isoformat()])
    overview.append([])
    overview.append([message(language, "goals")])
    for goal in result.goals:
        overview.append([goal_label(language, goal.id), status_label(language, goal.verdict)])
    overview.append([])
    overview.append([message(language, "category_ects")])
    targets = {
        rule.parameters.category_id: rule.parameters.ects
        for rule in program.rules
        if rule.parameters.type == "min_ects_in_category"
    }
    for category in program.categories:
        overview.append(
            [
                category_label(language, category.official_name),
                f"{result.category_ects.get(category.id, 0)} / {targets.get(category.id, 0)}",
            ]
        )
    overview.append(
        [message(language, "total_ects"), f"{result.total_ects} / {program.total_ects}"]
    )
    overview.append([])
    overview.append([message(language, "disclaimer")])
    overview.column_dimensions["A"].width = 80

    rules = workbook.create_sheet(message(language, "rules"))
    _header(
        rules,
        [
            message(language, "id"),
            message(language, "type"),
            message(language, "status"),
            message(language, "current"),
            message(language, "target"),
            message(language, "gap"),
            message(language, "provisional_reason"),
        ],
    )
    for rule in result.rules:
        rules.append(
            [
                rule.id,
                rule.type,
                status_label(language, rule.status),
                str(rule.current_value),
                str(rule.target_value),
                localized_text(language, rule.gap.text) if rule.gap else "",
                ", ".join(localized_text(language, reason) for reason in rule.provisional_reasons),
            ]
        )
    for status, color in {
        "fulfilled": "C6EFCE",
        "not_fulfilled": "FFC7CE",
        "provisional": "FCE4D6",
        "manual": "D9E1F2",
    }.items():
        rules.conditional_formatting.add(
            "C2:C1048576",
            CellIsRule(
                operator="equal",
                formula=[f'"{status_label(language, status)}"'],
                fill=PatternFill("solid", fgColor=color),
            ),
        )

    modules = workbook.create_sheet(message(language, "modules"))
    _header(
        modules,
        [
            message(language, "code"),
            message(language, "title"),
            message(language, "ects"),
            message(language, "categories"),
            message(language, "mandatory"),
            "",
            message(language, "category"),
        ],
    )
    for index, item in enumerate(program.modules, start=2):
        modules.cell(index, 1, item.code)
        modules.cell(index, 2, item.title)
        modules.cell(index, 3, item.ects)
        modules.cell(index, 4, ", ".join(item.eligible_category_ids))
        modules.cell(index, 5, item.mandatory)
    for index, category in enumerate(program.categories, start=2):
        modules.cell(index, 7, category.id)

    sheet = workbook.create_sheet(message(language, "credits"))
    _header(
        sheet,
        [
            message(language, "module_code"),
            message(language, "semester"),
            message(language, "ects"),
            message(language, "grade"),
            message(language, "passed"),
            message(language, "category"),
            message(language, "recognition_status"),
        ],
    )
    allocations = {
        item.module_code: item.allocated_category_id
        for item in result.allocation
        if item.module_code
    }
    for item in credits.credits:
        sheet.append(
            [
                item.module_code,
                str(item.semester),
                item.ects,
                item.grade,
                item.passed,
                allocations.get(item.module_code),
                "",
            ]
        )
    for item in credits.recognized_credits:
        sheet.append(
            [
                item.module_code,
                "",
                item.ects,
                "",
                True,
                item.category_id,
                status_label(language, item.status),
            ]
        )
    table = Table(displayName="MyCredits", ref=f"A1:G{VALIDATION_LAST_ROW}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    sheet.add_table(table)
    code_validation = DataValidation(
        type="list",
        formula1=_sheet_range(modules.title, "A", len(program.modules) + 1),
        allow_blank=True,
    )
    category_validation = DataValidation(
        type="list",
        formula1=_sheet_range(modules.title, "G", len(program.categories) + 1),
        allow_blank=True,
    )
    sheet.add_data_validation(code_validation)
    sheet.add_data_validation(category_validation)
    code_validation.add(f"A2:A{VALIDATION_LAST_ROW}")
    category_validation.add(f"F2:F{VALIDATION_LAST_ROW}")
    summary_row = VALIDATION_LAST_ROW + 2
    sheet.cell(summary_row, 1, message(language, "category"))
    sheet.cell(summary_row, 2, message(language, "category_formula"))
    for index, category in enumerate(program.categories, start=summary_row + 1):
        sheet.cell(index, 1, category_label(language, category.official_name))
        sheet.cell(
            index,
            2,
            f'=SUMIF(F2:F{VALIDATION_LAST_ROW},"{category.id}",C2:C{VALIDATION_LAST_ROW})',
        )

    allocation = workbook.create_sheet(message(language, "allocation"))
    _header(
        allocation,
        [
            message(language, "module"),
            message(language, "recognized_credit"),
            message(language, "category"),
            message(language, "ects"),
            message(language, "reason"),
        ],
    )
    for item in result.allocation:
        allocation.append(
            [
                item.module_code,
                item.recognized_credit_id,
                item.allocated_category_id,
                item.ects_counted,
                localized_text(language, item.reason),
            ]
        )
    gaps = workbook.create_sheet(message(language, "gaps"))
    _header(gaps, [message(language, "id"), message(language, "status"), message(language, "text")])
    for gap in result.gaps:
        gaps.append(
            [
                gap["rule_id"],
                status_label(language, gap["status"]),
                localized_text(language, gap["text"]),
            ]
        )
    sources = workbook.create_sheet(message(language, "sources"))
    _header(
        sources,
        [message(language, "id"), message(language, "document"), message(language, "page")],
    )
    for rule in program.rules:
        if rule.source:
            sources.append([rule.id, rule.source.document, rule.source.page])
    issues = workbook.create_sheet(message(language, "issues"))
    _header(
        issues,
        [message(language, "id"), message(language, "severity"), message(language, "text")],
    )
    for issue in result.open_issues:
        issues.append([issue.id, issue.severity, localized_text(language, issue.text)])
    if student is not None:
        _add_plan_sheets(
            workbook, program, credits, plan or PlanFile(), student, checklist, language
        )
    for worksheet in workbook.worksheets:
        if worksheet.max_row > 1:
            worksheet.auto_filter.ref = worksheet.dimensions
        _widths(worksheet)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return path


def _add_plan_sheets(
    workbook: Workbook,
    program: Program,
    credits: CreditsFile,
    plan: PlanFile,
    student: StudentProfile | None,
    checklist: ChecklistFile | None,
    language: str,
) -> None:
    """Add a transparent, presentation-oriented view of plan state."""
    title = "Studienplan" if language == "de" else "Study Plan"
    sheet = workbook.create_sheet(title)
    headers = (
        [
            "Semester",
            "Code",
            "Titel",
            "Kategorie",
            "Stufe",
            "ECTS",
            "Typ",
            "Status",
            "Note",
            "Versuch",
            "Bedingung",
            "Quelle",
        ]
        if language == "de"
        else [
            "Semester",
            "Code",
            "Title",
            "Category",
            "Level",
            "ECTS",
            "Type",
            "Status",
            "Grade",
            "Attempt",
            "Condition",
            "Source",
        ]
    )
    _header(sheet, headers)
    modules = {module.code: module for module in program.modules}
    attempts = {
        (item.module_code, str(item.semester), item.attempt): item for item in credits.credits
    }
    basics = [
        module.code for module in program.modules if module.mandatory and module.level == "basic"
    ]
    thesis = next(
        (
            module.code
            for module in program.modules
            if "thesis" in module.title.lower() or "BAA" in module.code
        ),
        None,
    )
    threshold = next(
        (
            rule.parameters.minimum_ects
            for rule in program.rules
            if rule.id == "thesis_minimum" and rule.parameters.type == "min_ects_total"
        ),
        0,
    )
    for item in sorted(
        plan.planned_modules,
        key=lambda value: (semester_key(value.target_semester), value.module_code or ""),
    ):
        module = modules.get(item.module_code or "")
        if not module:
            continue
        attempt = attempts.get((module.code, str(item.target_semester), item.attempt or 1))
        condition = _condition_text(
            language,
            item,
            module.code,
            module.prerequisites,
            module.level,
            basics,
            thesis,
            threshold,
            plan,
        )
        sheet.append(
            [
                str(item.target_semester),
                module.code,
                module.title,
                category_label(
                    language,
                    next(
                        (
                            category.official_name
                            for category in program.categories
                            if category.id in module.eligible_category_ids
                        ),
                        "",
                    ),
                ),
                _level_label(language, module.level),
                module.ects,
                _type_label(language, module.mandatory),
                _plan_status_label(language, item.status),
                attempt.grade if attempt else "",
                attempt.attempt if attempt else (item.attempt or ""),
                condition,
                item.source.document if item.source else "",
            ]
        )
        _fill_plan_row(sheet, sheet.max_row, item.status)
    for recognition in credits.recognized_credits:
        sheet.append(
            [
                str(student.start_semester) if student else "",
                "",
                ("Anerkennung: " if language == "de" else "Recognition: ") + recognition.basis,
                _category_display(program, language, recognition.category_id),
                "",
                recognition.ects,
                "",
                _recognized_status_label(language, recognition.status),
                "",
                "",
                recognition.open_issue or "",
                recognition.decision_document.document,
            ]
        )
        _fill_plan_row(sheet, sheet.max_row, "recognized")
    for placeholder in sorted(
        plan.placeholders,
        key=lambda value: (semester_key(value.target_semester), value.category_id),
    ):
        label = "Wahlplatzhalter" if language == "de" else "Elective placeholder"
        sheet.append(
            [
                str(placeholder.target_semester),
                "",
                label,
                _category_display(program, language, placeholder.category_id),
                "",
                placeholder.ects_needed,
                "",
                _plan_status_label(language, "placeholder"),
                "",
                "",
                ", ".join(placeholder.suggested_module_codes),
                "",
            ]
        )
        _fill_plan_row(sheet, sheet.max_row, "placeholder")
    overview_title = "Semesterübersicht" if language == "de" else "Semester Overview"
    overview = workbook.create_sheet(overview_title)
    _header(
        overview,
        ["Semester", "ECTS geplant", "ECTS bestanden", "ECTS kumuliert", "Verstösse", "Zulassung"]
        if language == "de"
        else [
            "Semester",
            "ECTS planned",
            "ECTS passed",
            "ECTS cumulative",
            "Violations",
            "Admission",
        ],
    )
    report = (
        plan_report(program, student, credits, plan, checklist or ChecklistFile())
        if student
        else {"semesters": {}, "earliest_thesis_admission_semester": None}
    )
    passed_status = _plan_status_label(language, "passed")
    failed_status = _plan_status_label(language, "failed")
    for row, (semester, values) in enumerate(report["semesters"].items(), start=2):
        overview.append(
            [
                semester,
                f"=SUMIFS('{title}'!$F:$F,'{title}'!$A:$A,A{row},'{title}'!$H:$H,\"<>{failed_status}\")",
                f"=SUMIFS('{title}'!$F:$F,'{title}'!$A:$A,A{row},'{title}'!$H:$H,\"{passed_status}\")",
                f"=SUM($B$2:B{row})",
                len(values["violations"]),
                _admission_text(language, report, semester),
            ]
        )
        if semester == report["earliest_thesis_admission_semester"]:
            for cell in overview[overview.max_row]:
                cell.fill = PatternFill("solid", fgColor="FFF2CC")


def _condition_text(
    language: str,
    item,
    code: str,
    prerequisites: list,
    level: str,
    basics: list[str],
    thesis: str | None,
    threshold: int,
    plan: PlanFile,
) -> str:
    if item.status == "passed":
        return ""
    if code == thesis:
        german = (
            f"Zulassung ab {threshold} ECTS; "
            "programmspezifische Anforderungen gemäss Modulbeschreibung"
        )
        english = (
            f"Admission from {threshold} ECTS; "
            "programme-specific requirements in module description"
        )
        return german if language == "de" else english
    if prerequisites:
        codes = ", ".join(item.module_code or item.description or "" for item in prerequisites)
        return ("Voraussetzungen: " if language == "de" else "Prerequisites: ") + codes
    if level == "advanced":
        open_basics = []
        for basic in plan.planned_modules:
            if basic.module_code not in basics or basic.status == "passed":
                continue
            state = (
                "Wiederholung"
                if basic.status == "retake"
                else _plan_status_label(language, basic.status)
            )
            open_basics.append(f"{basic.module_code} ({state} {basic.target_semester})")
        return (
            "Erst nach allen Basic-Pflichtmodulen (Art. 20 Abs. 2); offen: "
            + ", ".join(open_basics)
            if language == "de"
            else "Level gate after: " + ", ".join(open_basics)
        )
    return (
        "Voraussetzungen unbekannt, Modulbeschreibung fehlt"
        if language == "de"
        else "prerequisites unknown, module description missing"
    )


def _fill_plan_row(sheet, row: int, status: str) -> None:
    colors = {
        "passed": "C6EFCE",
        "running": "BDD7EE",
        "planned": "FFFFFF",
        "failed": "FFC7CE",
        "retake": "FCE4D6",
        "placeholder": "FFF2CC",
        "recognized": "D9EAD3",
    }
    for cell in sheet[row]:
        cell.fill = PatternFill("solid", fgColor=colors[status])


def _plan_status_label(language: str, status: str) -> str:
    labels = {
        "en": {
            "passed": "passed",
            "failed": "failed",
            "running": "running",
            "planned": "planned",
            "retake": "retake",
            "placeholder": "placeholder",
        },
        "de": {
            "passed": "bestanden",
            "failed": "nicht bestanden",
            "running": "laufend",
            "planned": "geplant",
            "retake": "Wiederholung",
            "placeholder": "Platzhalter",
        },
    }
    return labels.get(language, labels["en"])[status]


def _recognized_status_label(language: str, status: str) -> str:
    if language == "de":
        return "anerkannt (vorläufig)" if status == "provisional" else "anerkannt"
    return "recognized (provisional)" if status == "provisional" else "recognized"


def _level_label(language: str, level: str) -> str:
    return {"basic": "Basic", "intermediate": "Intermediate", "advanced": "Advanced"}.get(
        level, level
    )


def _type_label(language: str, mandatory: bool) -> str:
    return (
        ("Pflicht" if mandatory else "Wahl")
        if language == "de"
        else ("Mandatory" if mandatory else "Elective")
    )


def _category_display(program: Program, language: str, category_id: str | None) -> str:
    if category_id is None:
        return "offen" if language == "de" else "open"
    category = next((item for item in program.categories if item.id == category_id), None)
    return category_label(language, category.official_name) if category else category_id


def _admission_text(language: str, report: dict, semester: str) -> str:
    if semester != report["earliest_thesis_admission_semester"]:
        return ""
    threshold = report["thesis_admission_threshold"]
    previous = _previous_semester(semester)
    if language == "de":
        return f"Thesis frühestens: {semester} ({threshold} ECTS erreicht Ende {previous})"
    return f"Thesis earliest: {semester} ({threshold} ECTS reached at end of {previous})"


def _previous_semester(value: str) -> str:
    semester = Semester(value)
    year, term = semester.sort_key
    return str(Semester(f"{'FS' if term else 'HS'}{(year if term else year - 1) % 100:02d}"))

"""Deterministic semester-plan generation and validation."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from studyplan.engine.rules import evaluate
from studyplan.models import (
    ChecklistFile,
    CreditsFile,
    ModelTimetableEntry,
    PlanFile,
    PlanItem,
    PlanPlaceholder,
    Program,
    Semester,
    StudentProfile,
)


def semester_key(value: str | Semester) -> tuple[int, int]:
    year, term = Semester(str(value)).sort_key
    return (year + 100 if year < 50 else year, term)


def next_semester(value: str | Semester) -> Semester:
    semester = Semester(str(value))
    year, term = semester.sort_key
    return Semester(f"{'HS' if term == 0 else 'FS'}{(year if term == 0 else year + 1) % 100:02d}")


def semester_for_relative(start: Semester, relative: int) -> Semester:
    result = start
    for _ in range(relative - 1):
        result = next_semester(result)
    return result


def current_semester(today: date | None = None) -> Semester:
    today = today or date.today()
    return Semester(f"{'HS' if today.month >= 8 else 'FS'}{today.year % 100:02d}")


def _term(value: Semester) -> str:
    return str(value)[:2]


def next_offering(start: Semester, offered_terms: list[str], not_before: Semester) -> Semester:
    candidate = start
    while (
        semester_key(candidate) < semester_key(not_before) or _term(candidate) not in offered_terms
    ):
        candidate = next_semester(candidate)
    return candidate


def _entries(program: Program, student: StudentProfile) -> dict[str, ModelTimetableEntry]:
    entries = program.model_timetables.get(student.study_mode, {}).get(
        str(student.start_semester)[:2], []
    )
    return {entry.module_code: entry for entry in entries}


def _maximum_semesters(program: Program, student: StudentProfile) -> int:
    duration = program.study_modes[student.study_mode].maximum_semesters
    return duration or 99


def _last_allowed_semester(program: Program, student: StudentProfile) -> Semester:
    """Return the final permitted semester, including recorded interruptions."""
    return semester_for_relative(
        student.start_semester,
        _maximum_semesters(program, student) + len(student.interruption_semesters),
    )


def _thesis_code(program: Program) -> str | None:
    for module in program.modules:
        if "thesis" in module.title.lower() or "BAA" in module.code:
            return module.code
    return None


def _thesis_threshold(program: Program) -> int:
    for rule in program.rules:
        if rule.id == "thesis_minimum" and rule.parameters.type == "min_ects_total":
            return rule.parameters.minimum_ects
    return 0


def _passed_codes(credits: CreditsFile) -> set[str]:
    return {item.module_code for item in credits.credits if item.passed}


def _last_failed(credits: CreditsFile, code: str) -> Any | None:
    failures = [item for item in credits.credits if item.module_code == code and not item.passed]
    return max(failures, key=lambda item: (semester_key(item.semester), item.attempt), default=None)


def _module_item(
    code: str, semester: Semester, status: str, origin: str, attempt: int | None = None
) -> PlanItem:
    return PlanItem(
        module_code=code,
        target_semester=semester,
        status=status,
        origin=origin,
        attempt=attempt,
    )


def plan_status_label(language: str, status: str) -> str:
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
    return labels.get(language, labels["en"]).get(status, status)


def condition_text(
    language: str,
    item: PlanItem,
    program: Program,
    credits: CreditsFile,
    plan: PlanFile,
) -> str:
    if item.status == "passed":
        return ""

    if item.status == "failed":
        passed_retakes = [
            credit
            for credit in credits.credits
            if credit.module_code == item.module_code
            and credit.passed
            and semester_key(credit.semester) > semester_key(item.target_semester)
        ]
        if passed_retakes:
            earliest = min(
                passed_retakes,
                key=lambda credit: (semester_key(credit.semester), credit.attempt),
            )
            return (
                f"Wiederholung bestanden: {earliest.semester} (Versuch {earliest.attempt})"
                if language == "de"
                else f"Retake passed: {earliest.semester} (attempt {earliest.attempt})"
            )
        retake = next(
            (
                other
                for other in plan.planned_modules
                if other.module_code == item.module_code and other.status == "retake"
            ),
            None,
        )
        if retake:
            return (
                f"Wiederholung geplant: {retake.target_semester}"
                if language == "de"
                else f"Retake planned: {retake.target_semester}"
            )
        return "Wiederholung nicht geplant" if language == "de" else "Retake not planned"

    thesis = _thesis_code(program)
    threshold = _thesis_threshold(program)
    if item.module_code and item.module_code == thesis:
        german = (
            f"Zulassung ab {threshold} ECTS; "
            "programmspezifische Anforderungen gemäss Modulbeschreibung"
        )
        english = (
            f"Admission from {threshold} ECTS; "
            "programme-specific requirements in module description"
        )
        return german if language == "de" else english

    modules = {module.code: module for module in program.modules}
    module = modules.get(item.module_code or "")
    if module and module.prerequisites:
        codes = ", ".join(
            prereq.module_code or prereq.description or "" for prereq in module.prerequisites
        )
        return ("Voraussetzungen: " if language == "de" else "Prerequisites: ") + codes

    if module and module.level == "advanced":
        basic_codes = sorted(
            {m.code for m in program.modules if m.mandatory and m.level == "basic"}
        )
        passed_codes = {c.module_code for c in credits.credits if c.passed} | {
            it.module_code
            for it in plan.planned_modules
            if it.status == "passed" and it.module_code
        }
        open_items: list[str] = []
        conditional_items: list[str] = []
        for code in basic_codes:
            if code in passed_codes:
                continue
            candidates = [
                it
                for it in plan.planned_modules
                if it.module_code == code and it.status in {"planned", "retake", "running"}
            ]
            if candidates:
                latest = max(candidates, key=lambda it: semester_key(it.target_semester))
                state_label = plan_status_label(language, latest.status)
                entry_str = f"{code} ({state_label} {latest.target_semester})"
                if semester_key(latest.target_semester) < semester_key(item.target_semester):
                    conditional_items.append(entry_str)
                else:
                    open_items.append(entry_str)
            else:
                failed = _last_failed(credits, code)
                if failed:
                    failed_label = plan_status_label(language, "failed")
                    failed_sem = getattr(failed, "semester", getattr(failed, "target_semester", ""))
                    open_items.append(f"{code} ({failed_label} {failed_sem})")
                else:
                    not_planned = "nicht geplant" if language == "de" else "not planned"
                    open_items.append(f"{code} ({not_planned})")

        if open_items:
            codes_str = ", ".join(open_items)
            return (
                f"Verletzt: Basic-Pflichtmodule nicht vor {item.target_semester} bestanden: "
                f"{codes_str}"
                if language == "de"
                else (
                    f"Violated: Basic mandatory modules not passed before {item.target_semester}: "
                    f"{codes_str}"
                )
            )
        if conditional_items:
            codes_str = ", ".join(conditional_items)
            return (
                "Erst nach allen Basic-Pflichtmodulen (Art. 20 Abs. 2); "
                f"erfüllt, sofern bestanden: {codes_str}"
                if language == "de"
                else (
                    "Only after all Basic mandatory modules (Art. 20 para. 2); met if passed: "
                    f"{codes_str}"
                )
            )
        return (
            "Erfüllt: alle Basic-Pflichtmodule bestanden (Art. 20 Abs. 2)"
            if language == "de"
            else "Met: all Basic mandatory modules passed (Art. 20 para. 2)"
        )

    if item.status in {"planned", "retake", "running"}:
        return (
            "Voraussetzungen unbekannt, Modulbeschreibung fehlt"
            if language == "de"
            else "prerequisites unknown, module description missing"
        )

    return ""


def generate_plan(
    program: Program,
    student: StudentProfile,
    credits: CreditsFile,
    existing: PlanFile,
    checklist: ChecklistFile,
    now: Semester,
    force: bool = False,
) -> tuple[PlanFile, list[str]]:
    """Build a forecast plan while preserving student-controlled entries."""
    entries = _entries(program, student)
    warnings: list[str] = []
    protected = [
        item
        for item in existing.planned_modules
        if item.origin == "manual" or item.status == "running" or item.origin == "credits"
    ]
    manual_placeholders = [item for item in existing.placeholders if item.origin == "manual"]
    result = PlanFile(planned_modules=protected.copy(), placeholders=manual_placeholders.copy())
    occupied = {item.module_code for item in result.planned_modules if item.module_code}
    passed = _passed_codes(credits)
    last_allowed = _last_allowed_semester(program, student)

    for credit in sorted(
        credits.credits, key=lambda value: (semester_key(value.semester), value.attempt)
    ):
        if credit.module_code in occupied:
            continue
        status = "passed" if credit.passed else "failed"
        result.planned_modules.append(
            _module_item(credit.module_code, credit.semester, status, "credits", credit.attempt)
        )
        if credit.passed:
            occupied.add(credit.module_code)

    for code in sorted({item.module_code for item in credits.credits if not item.passed} - passed):
        failure = _last_failed(credits, code)
        assert failure is not None
        entry = entries.get(code)
        terms = entry.offered_terms if entry else [_term(failure.semester)]
        target = next_offering(next_semester(failure.semester), terms, now)
        if semester_key(target) > semester_key(last_allowed):
            warnings.append(f"Retake cannot be scheduled within the maximum duration: {code}")
            continue
        result.planned_modules.append(
            _module_item(code, target, "retake", "generated", failure.attempt + 1)
        )
        occupied.add(code)

    modules = {module.code: module for module in program.modules}
    thesis = _thesis_code(program)
    for code, entry in sorted(
        entries.items(), key=lambda value: (value[1].relative_semester, value[0])
    ):
        module = modules.get(code)
        if not module or not module.mandatory or code in occupied or code == thesis:
            continue
        recommended = semester_for_relative(student.start_semester, entry.relative_semester)
        target = next_offering(recommended, entry.offered_terms, now)
        if semester_key(target) > semester_key(last_allowed):
            warnings.append(f"Module cannot be scheduled within the maximum duration: {code}")
            continue
        result.planned_modules.append(_module_item(code, target, "planned", "generated"))
        occupied.add(code)

    for module in program.modules:
        if module.mandatory and module.code not in occupied and module.code != thesis:
            warnings.append(f"No model timetable placement for mandatory module: {module.code}")

    basics = [
        item
        for item in result.planned_modules
        if item.module_code in modules
        and modules[item.module_code].mandatory
        and modules[item.module_code].level == "basic"
        and item.status in {"planned", "retake", "running", "passed"}
    ]
    last_basic = max((item.target_semester for item in basics), key=semester_key, default=None)
    for item in result.planned_modules:
        module = modules.get(item.module_code or "")
        if not module or module.level != "advanced" or item.origin == "manual" or not last_basic:
            continue
        minimum = next_semester(last_basic)
        entry = entries.get(module.code)
        terms = entry.offered_terms if entry else module.semesters_offered or ["HS", "FS"]
        if semester_key(item.target_semester) < semester_key(minimum):
            shifted = next_offering(minimum, terms, minimum)
            if semester_key(shifted) > semester_key(last_allowed):
                warnings.append(
                    f"Level gate cannot be met within the maximum duration: {module.code}"
                )
            else:
                item.target_semester = shifted

    for rule in program.rules:
        if rule.parameters.type != "level_deadline":
            continue
        deadline = semester_for_relative(
            student.start_semester, rule.parameters.completed_semesters
        )
        for item in result.planned_modules:
            module = modules.get(item.module_code or "")
            if (
                module
                and module.mandatory
                and module.level == rule.parameters.level
                and semester_key(item.target_semester) > semester_key(deadline)
            ):
                warnings.append(f"Basic deadline violated by: {module.code}")

    if thesis and thesis not in occupied:
        entry = entries.get(thesis)
        if entry:
            target = next_offering(
                semester_for_relative(student.start_semester, entry.relative_semester),
                entry.offered_terms,
                now,
            )
            threshold = _thesis_threshold(program)
            missing = threshold - _forecast_ects_at_start(program, result, credits, target)
            while missing > 0 and semester_key(target) < semester_key(last_allowed):
                target = next_offering(
                    next_semester(target), entry.offered_terms, next_semester(target)
                )
                missing = threshold - _forecast_ects_at_start(program, result, credits, target)
            if last_basic:
                gated_target = next_offering(
                    max(target, next_semester(last_basic), key=semester_key),
                    entry.offered_terms,
                    next_semester(last_basic),
                )
                if semester_key(gated_target) <= semester_key(last_allowed):
                    target = gated_target
            if semester_key(target) > semester_key(last_allowed):
                target = semester_for_relative(student.start_semester, entry.relative_semester)
            missing = max(0, threshold - _forecast_ects_at_start(program, result, credits, target))
            note = (
                f"thesis admission threshold not reached by {target}: {missing} ECTS missing"
                if missing
                else None
            )
            if note:
                warnings.append(note)
            result.planned_modules.append(
                PlanItem(
                    module_code=thesis,
                    target_semester=target,
                    status="planned",
                    origin="generated",
                    note=note,
                )
            )

    _add_placeholders(program, student, credits, result, checklist, entries, now)
    result.planned_modules.sort(
        key=lambda item: (semester_key(item.target_semester), item.module_code or "")
    )
    result.placeholders.sort(
        key=lambda item: (semester_key(item.target_semester), item.category_id)
    )
    return result, warnings


def _forecast_ects_at_start(
    program: Program, plan: PlanFile, credits: CreditsFile, semester: Semester
) -> int:
    credits_ects = sum(
        item.ects
        for item in credits.credits
        if item.passed and semester_key(item.semester) < semester_key(semester)
    )
    recognized_ects = sum(item.ects for item in credits.recognized_credits)
    module_ects = {module.code: module.ects for module in program.modules}
    return (
        credits_ects
        + recognized_ects
        + sum(
            module_ects.get(item.module_code or "", 0)
            for item in plan.planned_modules
            if item.status in {"planned", "running", "retake"}
            and semester_key(item.target_semester) < semester_key(semester)
        )
    )


def _add_placeholders(
    program: Program,
    student: StudentProfile,
    credits: CreditsFile,
    plan: PlanFile,
    checklist: ChecklistFile,
    entries: dict[str, ModelTimetableEntry],
    now: Semester,
) -> None:
    result = evaluate(program, student, credits, plan, checklist, "forecast")
    targets = {
        rule.parameters.category_id: rule.parameters.ects
        for rule in program.rules
        if rule.parameters.type == "min_ects_in_category"
    }
    planned_codes = {item.module_code for item in plan.planned_modules if item.module_code}
    semester_ects: defaultdict[str, int] = defaultdict(int)
    modules = {module.code: module for module in program.modules}
    for item in plan.planned_modules:
        if item.module_code in modules and item.status not in {"failed"}:
            semester_ects[str(item.target_semester)] += modules[item.module_code].ects
    thesis = _thesis_code(program)
    thesis_semester = next(
        (
            item.target_semester
            for item in plan.planned_modules
            if item.module_code == thesis and item.status in {"planned", "retake"}
        ),
        _last_allowed_semester(program, student),
    )
    last_allowed = _last_allowed_semester(program, student)
    eligible_semesters: list[Semester] = []
    candidate = next_semester(now)
    while semester_key(candidate) < semester_key(thesis_semester) and semester_key(
        candidate
    ) <= semester_key(last_allowed):
        eligible_semesters.append(candidate)
        candidate = next_semester(candidate)

    if not eligible_semesters:
        return

    model_loads: defaultdict[int, int] = defaultdict(int)
    for entry in entries.values():
        module = modules.get(entry.module_code)
        if module:
            model_loads[entry.relative_semester] += module.ects
    load_limit = max(model_loads.values(), default=999)
    for category, target in targets.items():
        missing = max(0, target - result.category_ects.get(category, 0))
        if not missing:
            continue

        def candidates_for(
            semester: Semester, category_id: str = category
        ) -> list[tuple[bool, str]]:
            choices = []
            for module in program.modules:
                if (
                    module.mandatory
                    or category_id not in module.eligible_category_ids
                    or module.code in planned_codes
                ):
                    continue
                entry = entries.get(module.code)
                terms = entry.offered_terms if entry else module.semesters_offered
                if terms and _term(semester) not in terms:
                    continue
                choices.append((not entry.recommended if entry else True, module.code))
            return choices

        possible = [semester for semester in eligible_semesters if candidates_for(semester)]
        target_semester = min(
            possible or eligible_semesters,
            key=lambda value: (semester_ects[str(value)], semester_key(value)),
        )
        candidates = candidates_for(target_semester)
        suggestions = [code for _, code in sorted(candidates)]
        sizes = [modules[code].ects for code in suggestions if code in modules]
        chunk_size = min(sizes, default=3)
        remaining = missing
        while remaining:
            chunk = min(chunk_size, remaining)
            offered = [semester for semester in eligible_semesters if candidates_for(semester)]
            current_pool = offered or eligible_semesters
            allowed = [
                semester
                for semester in current_pool
                if semester_ects[str(semester)] + chunk <= load_limit
            ]
            if allowed:
                selected = min(allowed, key=semester_key)
            else:
                selected = min(
                    current_pool,
                    key=lambda value: (semester_ects[str(value)], semester_key(value)),
                )
            plan.placeholders.append(
                PlanPlaceholder(
                    category_id=category,
                    ects_needed=chunk,
                    suggested_module_codes=[code for _, code in sorted(candidates_for(selected))],
                    target_semester=selected,
                )
            )
            semester_ects[str(selected)] += chunk
            remaining -= chunk


def plan_report(
    program: Program,
    student: StudentProfile,
    credits: CreditsFile,
    plan: PlanFile,
    checklist: ChecklistFile,
    language: str | None = None,
) -> dict[str, Any]:
    modules = {module.code: module for module in program.modules}
    entries = _entries(program, student)
    lang = language or (student.language if student and student.language else "en")
    semesters: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "planned_ects": 0,
            "passed_ects": 0,
            "cumulative_ects": 0,
            "violations": [],
            "items": [],
        }
    )
    violations: list[str] = []
    attempts = {
        (item.module_code, str(item.semester), item.attempt): item for item in credits.credits
    }
    recognized_semester = str(student.start_semester)
    for recognition in credits.recognized_credits:
        row = semesters[recognized_semester]
        row["planned_ects"] += recognition.ects
        row["passed_ects"] += recognition.ects
        row["items"].append(
            {
                "code": recognition.module_code,
                "placeholder": None,
                "status": "recognized",
                "origin": "credits",
                "ects": recognition.ects,
                "condition": "provisional recognized credit"
                if recognition.status == "provisional"
                else "",
                "grade": "",
                "attempt": None,
                "passed": True,
                "title": f"Recognition: {recognition.basis}",
                "category": recognition.category_id or "open",
            }
        )
    for item in plan.planned_modules:
        module = modules.get(item.module_code or "")
        if not module:
            continue
        row = semesters[str(item.target_semester)]
        attempt = attempts.get((module.code, str(item.target_semester), item.attempt or 1))
        if item.status != "failed":
            row["planned_ects"] += module.ects
        if item.status == "passed":
            row["passed_ects"] += module.ects
        cond = condition_text(lang, item, program, credits, plan)
        row["items"].append(
            {
                "code": module.code,
                "placeholder": None,
                "status": item.status,
                "origin": item.origin,
                "ects": module.ects,
                "condition": cond if cond else (item.note or ""),
                "grade": attempt.grade if attempt else "",
                "attempt": attempt.attempt if attempt else item.attempt,
                "passed": attempt.passed if attempt else item.status == "passed",
                "title": module.title,
                "category": module.eligible_category_ids[0] if module.eligible_category_ids else "",
            }
        )
        entry = entries.get(module.code)
        terms = entry.offered_terms if entry else module.semesters_offered
        if (
            item.status in {"planned", "retake"}
            and terms
            and _term(item.target_semester) not in terms
        ):
            message = f"{module.code} is not offered in {item.target_semester}."
            row["violations"].append(message)
            violations.append(message)
        if item.note:
            row["violations"].append(item.note)
            violations.append(item.note)
    for placeholder in plan.placeholders:
        row = semesters[str(placeholder.target_semester)]
        row["planned_ects"] += placeholder.ects_needed
        row["items"].append(
            {
                "code": None,
                "placeholder": placeholder.category_id,
                "status": "placeholder",
                "origin": placeholder.origin,
                "ects": placeholder.ects_needed,
                "condition": ", ".join(placeholder.suggested_module_codes),
                "grade": "",
                "attempt": None,
                "passed": False,
                "title": "Elective placeholder",
                "category": placeholder.category_id,
            }
        )
    cumulative = 0
    for semester in sorted(semesters, key=semester_key):
        cumulative += semesters[semester]["planned_ects"]
        semesters[semester]["cumulative_ects"] = cumulative
    thesis = _thesis_code(program)
    threshold = _thesis_threshold(program)
    earliest_admission = None
    previous = 0
    for semester, row in sorted(semesters.items(), key=lambda value: semester_key(value[0])):
        if previous >= threshold:
            earliest_admission = semester
            break
        previous = row["cumulative_ects"]
    engine = evaluate(program, student, credits, plan, checklist, "forecast")
    return {
        "semesters": dict(sorted(semesters.items(), key=lambda value: semester_key(value[0]))),
        "violations": violations,
        "earliest_thesis_admission_semester": earliest_admission,
        "thesis_admission_reached_end_semester": previous if earliest_admission else None,
        "thesis_admission_threshold": threshold,
        "earliest_graduation_semester": next(
            (
                semester
                for semester, row in semesters.items()
                if row["cumulative_ects"] >= program.total_ects
            ),
            None,
        ),
        "thesis_module_code": thesis,
        "forecast_verdict": engine.verdict,
        "placeholders": [item.model_dump(mode="json") for item in plan.placeholders],
    }

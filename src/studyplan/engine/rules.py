"""Pure deterministic rule evaluation backed by a CP-SAT allocation model."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from ortools.sat.python import cp_model
from pydantic import BaseModel, ConfigDict, Field

from studyplan.models import (
    ChecklistFile,
    CreditsFile,
    PlanFile,
    Program,
    StudentProfile,
)

DISCLAIMER = (
    "Not legally binding. The official study regulations and the program management decide."
)


class ResultModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Gap(ResultModel):
    kind: str
    value: int | str | list[str] | None = None
    text: str


class RuleResult(ResultModel):
    id: str
    type: str
    status: Literal["fulfilled", "not_fulfilled", "provisional", "manual"]
    current_value: Any = None
    target_value: Any = None
    gap: Gap | None = None
    source: dict[str, Any] | None = None
    verification_status: str
    provisional_reasons: list[str] = Field(default_factory=list)


class AllocationResult(ResultModel):
    module_code: str | None = None
    recognized_credit_id: str | None = None
    allocated_category_id: str | None = None
    ects_counted: int
    reason: str


class GoalResult(ResultModel):
    id: str
    verdict: Literal["eligible", "not_eligible", "provisional"]
    rule_ids: list[str]


class ManualChecklistResult(ResultModel):
    rule_id: str
    checked: bool


class OpenIssue(ResultModel):
    id: str
    severity: Literal["warning", "info"]
    text: str


class CheckResult(ResultModel):
    schema_version: Literal["1.0"] = "1.0"
    mode: Literal["current", "forecast"]
    disclaimer: str = DISCLAIMER
    verdict: Literal["eligible", "not_eligible", "provisional"]
    goals: list[GoalResult]
    rules: list[RuleResult]
    allocation: list[AllocationResult]
    gaps: list[dict[str, str]]
    manual_checklist: list[ManualChecklistResult]
    open_issues: list[OpenIssue]
    category_ects: dict[str, int]
    total_ects: int


@dataclass(frozen=True)
class _Candidate:
    key: str
    module_code: str | None
    recognized_credit_id: str | None
    ects: int
    eligible_categories: tuple[str, ...]
    forced_category: str | None
    provisional_reason: str | None
    recognized: bool
    semester: str | None


def _semester_count(start: str, end: str, interruptions: set[str]) -> int:
    start_key, end_key = _semester_key(start), _semester_key(end)
    count = 0
    year, term = start_key
    while (year, term) <= end_key:
        current = f"{'FS' if term == 0 else 'HS'}{year % 100:02d}"
        if current not in interruptions:
            count += 1
        if term == 0:
            term = 1
        else:
            year, term = year + 1, 0
    return count


def _semester_key(value: str) -> tuple[int, int]:
    """Order two-digit semester years across a century boundary deterministically."""
    from studyplan.models import Semester

    year, term = Semester(value).sort_key
    return (year + 100 if year < 50 else year, term)


def _candidates(
    program: Program, credits: CreditsFile, plan: PlanFile, mode: str
) -> list[_Candidate]:
    modules = {module.code: module for module in program.modules}
    passed: dict[str, Any] = {}
    for credit in credits.credits:
        canonical_code = (
            credit.module_code
            if credit.module_code in modules
            else next(
                (
                    module.code
                    for module in program.modules
                    if credit.module_code in module.predecessor_codes
                ),
                None,
            )
        )
        if credit.passed and canonical_code:
            previous = passed.get(canonical_code)
            if previous is None or (_semester_key(str(credit.semester)), credit.attempt) > (
                _semester_key(str(previous.semester)),
                previous.attempt,
            ):
                passed[canonical_code] = credit
    items: list[_Candidate] = []
    for code, credit in sorted(passed.items()):
        module = modules[code]
        reason = (
            "Uses an unverified code mapping."
            if credit.mapping_verification_status == "unverified"
            else None
        )
        items.append(
            _Candidate(
                f"module:{code}",
                code,
                None,
                credit.ects,
                tuple(module.eligible_category_ids),
                credit.forced_category_id,
                reason,
                credit.recognized_external,
                str(credit.semester),
            )
        )
    if mode == "forecast":
        for item in sorted(plan.planned_modules, key=lambda value: value.module_code):
            if item.module_code in passed or item.module_code not in modules:
                continue
            module = modules[item.module_code]
            reason = (
                "Uses an unverified code mapping."
                if item.mapping_verification_status == "unverified"
                else None
            )
            items.append(
                _Candidate(
                    f"module:{item.module_code}",
                    item.module_code,
                    None,
                    module.ects,
                    tuple(module.eligible_category_ids),
                    None,
                    reason,
                    False,
                    str(item.target_semester),
                )
            )
    for recognition in sorted(credits.recognized_credits, key=lambda value: value.id):
        module = modules.get(recognition.module_code or "")
        eligible = tuple(module.eligible_category_ids) if module else ()
        reason = (
            "Recognized credit is provisional." if recognition.status == "provisional" else None
        )
        items.append(
            _Candidate(
                f"recognition:{recognition.id}",
                recognition.module_code,
                recognition.id,
                recognition.ects,
                eligible,
                recognition.category_id,
                reason,
                True,
                None,
            )
        )
    return items


def _allocation(
    program: Program, candidates: list[_Candidate]
) -> tuple[list[AllocationResult], dict[str, int], dict[str, list[str]]]:
    category_ids = [category.id for category in program.categories]
    caps: dict[str, int] = {}
    targets: dict[str, int] = {}
    module_targets: dict[str, int] = {}
    for rule in program.rules:
        params = rule.parameters
        if params.type == "max_ects_in_category":
            caps[params.category_id] = min(caps.get(params.category_id, params.ects), params.ects)
        if params.type == "min_ects_in_category":
            targets[params.category_id] = max(targets.get(params.category_id, 0), params.ects)
        if params.type == "min_modules_in_category":
            module_targets[params.category_id] = max(
                module_targets.get(params.category_id, 0), params.minimum_modules
            )

    model = cp_model.CpModel()
    variables: dict[tuple[str, str], Any] = {}
    for item in candidates:
        allowed = (item.forced_category,) if item.forced_category else item.eligible_categories
        allowed = tuple(category for category in allowed if category in category_ids)
        if not allowed:
            continue
        for category in allowed:
            variables[item.key, category] = model.NewBoolVar(f"{item.key}_{category}")
        model.Add(sum(variables[item.key, category] for category in allowed) == 1)

    totals: dict[str, Any] = {}
    counted: dict[str, Any] = {}
    module_counts: dict[str, Any] = {}
    for category in category_ids:
        total = sum(
            item.ects * variables[item.key, category]
            for item in candidates
            if (item.key, category) in variables
        )
        totals[category] = total
        if category in caps:
            capped = model.NewIntVar(0, caps[category], f"counted_{category}")
            model.AddMinEquality(capped, [total, caps[category]])
            counted[category] = capped
        else:
            counted[category] = total
        module_counts[category] = sum(
            variables[item.key, category]
            for item in candidates
            if item.module_code is not None and (item.key, category) in variables
        )

    objective_terms: list[Any] = []
    for category, target in targets.items():
        fulfilled = model.NewBoolVar(f"fulfilled_{category}")
        model.Add(counted[category] >= target).OnlyEnforceIf(fulfilled)
        model.Add(counted[category] < target).OnlyEnforceIf(fulfilled.Not())
        objective_terms.append(fulfilled * 1_000_000)
        objective_terms.append(counted[category] * 100)
    for category, target in module_targets.items():
        fulfilled = model.NewBoolVar(f"module_count_fulfilled_{category}")
        model.Add(module_counts[category] >= target).OnlyEnforceIf(fulfilled)
        model.Add(module_counts[category] < target).OnlyEnforceIf(fulfilled.Not())
        objective_terms.append(fulfilled * 1_000_000)
        objective_terms.append(module_counts[category])
    if objective_terms:
        model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.search_branching = cp_model.FIXED_SEARCH
    status = solver.Solve(model)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        raise ValueError("No valid category allocation exists.")

    assigned: dict[str, str | None] = {}
    for item in candidates:
        assigned[item.key] = next(
            (
                category
                for category in category_ids
                if (item.key, category) in variables and solver.Value(variables[item.key, category])
            ),
            None,
        )
    raw_totals: dict[str, int] = defaultdict(int)
    for item in candidates:
        if assigned[item.key]:
            raw_totals[assigned[item.key]] += item.ects
    used: dict[str, int] = defaultdict(int)
    output: list[AllocationResult] = []
    reasons: dict[str, list[str]] = defaultdict(list)
    for item in sorted(candidates, key=lambda value: value.key):
        category = assigned[item.key]
        if category is None:
            counted_ects = 0
            reason = "No eligible category is available."
        else:
            cap = caps.get(category)
            remaining = max(0, cap - used[category]) if cap is not None else item.ects
            counted_ects = min(item.ects, remaining)
            used[category] += counted_ects
            if item.forced_category:
                reason = "Forced category assignment."
            elif cap is not None and counted_ects < item.ects:
                reason = "Category cap limits counted ECTS."
            else:
                reason = "Best deterministic allocation."
        if item.provisional_reason:
            reasons[category or "total"].append(item.provisional_reason)
        output.append(
            AllocationResult(
                module_code=item.module_code,
                recognized_credit_id=item.recognized_credit_id,
                allocated_category_id=category,
                ects_counted=counted_ects,
                reason=reason,
            )
        )
    return output, {category: used.get(category, 0) for category in category_ids}, dict(reasons)


def _gap(kind: str, value: int | str | list[str], text: str) -> Gap:
    return Gap(kind=kind, value=value, text=text)


def evaluate(
    program: Program,
    student: StudentProfile,
    credits: CreditsFile,
    plan: PlanFile,
    checklist: ChecklistFile,
    mode: Literal["current", "forecast"],
) -> CheckResult:
    """Evaluate all program rules without reading files or accessing external state."""
    program = Program.model_validate(program.model_dump())
    candidates = _candidates(program, credits, plan, mode)
    allocation, category_ects, provisional_by_category = _allocation(program, candidates)
    modules = {module.code: module for module in program.modules}
    category_names = {category.id: category.official_name for category in program.categories}
    candidate_by_code = {item.module_code: item for item in candidates if item.module_code}
    passed_codes = set(candidate_by_code)
    total_ects = sum(item.ects for item in candidates)
    checklist_state = {item.rule_id: item.checked for item in checklist.items}
    category_status = {category.id: category.verification_status for category in program.categories}
    all_provisional = [item.provisional_reason for item in candidates if item.provisional_reason]

    def module_passed(code: str) -> bool:
        if code in passed_codes:
            return True
        target = modules.get(code)
        if target and any(old in passed_codes for old in target.predecessor_codes):
            return True
        return any(
            code in modules[item].successor_codes for item in passed_codes if item in modules
        )

    def reasons_for(rule: Any) -> list[str]:
        reasons: list[str] = []
        if rule.verification_status == "unverified":
            reasons.append("Rule source is unverified.")
        params = rule.parameters
        categories: list[str] = []
        if hasattr(params, "category_id"):
            categories.append(params.category_id)
        if params.type == "required_all_mandatory":
            categories.extend(params.category_ids)
        for category in categories:
            if category_status.get(category) == "unverified":
                reasons.append(f"Category '{category}' is unverified.")
            reasons.extend(provisional_by_category.get(category, []))
        if params.type in {"min_ects_total", "min_ects_at_institution", "max_recognized_ects"}:
            reasons.extend(reason for reason in all_provisional if reason)
        return list(dict.fromkeys(reasons))

    results: list[RuleResult] = []
    result_by_id: dict[str, RuleResult] = {}

    def add(
        rule: Any,
        fulfilled: bool,
        current: Any,
        target: Any,
        gap: Gap | None = None,
        manual: bool = False,
    ) -> None:
        reasons = reasons_for(rule)
        status: Literal["fulfilled", "not_fulfilled", "provisional", "manual"]
        if manual:
            status = "manual"
        elif not fulfilled:
            status = "not_fulfilled"
        elif reasons:
            status = "provisional"
        else:
            status = "fulfilled"
        result = RuleResult(
            id=rule.id,
            type=rule.type,
            status=status,
            current_value=current,
            target_value=target,
            gap=gap,
            source=rule.source.model_dump(mode="json") if rule.source else None,
            verification_status=rule.verification_status,
            provisional_reasons=reasons,
        )
        results.append(result)
        result_by_id[rule.id] = result

    for rule in program.rules:
        if rule.type == "composite":
            continue
        params = rule.parameters
        if params.type == "min_ects_total":
            missing = max(0, params.minimum_ects - total_ects)
            add(
                rule,
                not missing,
                total_ects,
                params.minimum_ects,
                _gap(
                    "ects",
                    missing,
                    f"{missing} ECTS missing ({params.minimum_ects} required)",
                )
                if missing
                else None,
            )
        elif params.type == "min_ects_in_category":
            current = category_ects.get(params.category_id, 0)
            missing = max(0, params.ects - current)
            add(
                rule,
                not missing,
                current,
                params.ects,
                _gap(
                    "ects",
                    missing,
                    f"Category {category_names.get(params.category_id, params.category_id)}: "
                    f"{missing} ECTS missing ({params.ects} required)",
                )
                if missing
                else None,
            )
        elif params.type == "max_ects_in_category":
            current = category_ects.get(params.category_id, 0)
            add(rule, True, current, params.ects)
        elif params.type == "required_module":
            fulfilled = module_passed(params.module_code)
            add(
                rule,
                fulfilled,
                params.module_code if fulfilled else None,
                params.module_code,
                None
                if fulfilled
                else _gap(
                    "module", params.module_code, f"Required module {params.module_code} not passed"
                ),
            )
        elif params.type == "required_all_mandatory":
            required = [
                module.code
                for module in program.modules
                if module.mandatory and set(module.eligible_category_ids) & set(params.category_ids)
            ]
            missing = [code for code in required if not module_passed(code)]
            add(
                rule,
                not missing,
                len(required) - len(missing),
                len(required),
                None
                if not missing
                else _gap(
                    "modules", missing, f"Mandatory modules not passed: {', '.join(missing)}"
                ),
            )
        elif params.type == "required_one_of":
            found = next((code for code in params.module_codes if module_passed(code)), None)
            add(
                rule,
                found is not None,
                found,
                params.module_codes,
                None
                if found
                else _gap(
                    "modules",
                    params.module_codes,
                    f"One of these modules is required: {', '.join(params.module_codes)}",
                ),
            )
        elif params.type == "min_modules_in_category":
            current = sum(
                item.allocated_category_id == params.category_id and item.ects_counted > 0
                for item in allocation
                if item.module_code is not None
            )
            missing = max(0, params.minimum_modules - current)
            add(
                rule,
                not missing,
                current,
                params.minimum_modules,
                _gap(
                    "modules",
                    missing,
                    f"{missing} modules missing in category {params.category_id}",
                )
                if missing
                else None,
            )
        elif params.type == "prerequisite":
            target = candidate_by_code.get(params.module_code)
            missing = []
            if target:
                missing = [
                    code
                    for code in params.prerequisite_module_codes
                    if not module_passed(code)
                    or (
                        target.semester is not None
                        and (
                            candidate_by_code.get(code) is None
                            or candidate_by_code[code].semester is None
                            or _semester_key(candidate_by_code[code].semester)
                            > _semester_key(target.semester)
                        )
                    )
                ]
            add(
                rule,
                not missing,
                len(params.prerequisite_module_codes) - len(missing),
                len(params.prerequisite_module_codes),
                None
                if not missing
                else _gap("modules", missing, f"Prerequisites missing: {', '.join(missing)}"),
            )
        elif params.type == "max_attempts":
            failures: dict[str, int] = defaultdict(int)
            for credit in credits.credits:
                if not credit.passed:
                    failures[credit.module_code] += 1
            blocked = sorted(
                code for code, count in failures.items() if count >= params.maximum_attempts
            )
            add(
                rule,
                not blocked,
                blocked,
                params.maximum_attempts,
                None
                if not blocked
                else _gap("modules", blocked, f"Maximum attempts reached: {', '.join(blocked)}"),
            )
        elif params.type == "retake_budget":
            third = sorted(
                {credit.module_code for credit in credits.credits if credit.attempt >= 3}
            )
            excluded = sorted(set(third) & set(params.excluded_module_codes))
            used = sum(modules[code].ects for code in third if code in modules)
            fulfilled = not excluded and used <= params.ects_budget
            text = (
                "Third-attempt budget exceeded"
                if used > params.ects_budget
                else "Third attempt is excluded"
            )
            add(
                rule,
                fulfilled,
                used,
                params.ects_budget,
                None
                if fulfilled
                else _gap(
                    "ects", max(0, used - params.ects_budget), f"{text}: {', '.join(excluded)}"
                ),
            )
        elif params.type == "level_gate":
            required = [
                module.code
                for module in program.modules
                if module.level == params.required_level
                and (module.mandatory or not params.mandatory_only)
            ]
            violations: list[str] = []
            for item in candidates:
                module = modules.get(item.module_code or "")
                if module and module.level == params.gated_level:
                    if any(
                        not module_passed(code)
                        or (
                            item.semester is not None
                            and (
                                candidate_by_code.get(code) is None
                                or candidate_by_code[code].semester is None
                                or _semester_key(candidate_by_code[code].semester)
                                > _semester_key(item.semester)
                            )
                        )
                        for code in required
                    ):
                        violations.append(module.code)
            add(
                rule,
                not violations,
                [],
                required,
                None
                if not violations
                else _gap(
                    "modules", violations, f"Level gate violated by: {', '.join(violations)}"
                ),
            )
        elif params.type == "level_deadline":
            required = [
                module.code
                for module in program.modules
                if module.level == params.level and (module.mandatory or not params.mandatory_only)
            ]
            semesters = [item.semester for item in candidates if item.semester]
            elapsed = _semester_count(
                str(student.start_semester),
                max(semesters) if semesters else str(student.start_semester),
                set(map(str, student.interruption_semesters)),
            )
            missing = (
                [code for code in required if not module_passed(code)]
                if elapsed >= params.completed_semesters
                else []
            )
            add(
                rule,
                not missing,
                elapsed,
                params.completed_semesters,
                None
                if not missing
                else _gap(
                    "modules",
                    missing,
                    f"Level deadline exceeded; modules missing: {', '.join(missing)}",
                ),
            )
        elif params.type == "min_ects_at_institution":
            current = sum(item.ects for item in candidates if not item.recognized)
            missing = max(0, params.minimum_ects - current)
            add(
                rule,
                not missing,
                current,
                params.minimum_ects,
                _gap(
                    "ects",
                    missing,
                    f"At institution: {missing} ECTS missing ({params.minimum_ects} required)",
                )
                if missing
                else None,
            )
        elif params.type == "max_recognized_ects":
            applicable = not params.study_modes or student.study_mode in params.study_modes
            current = (
                sum(item.ects for item in credits.recognized_credits if item.basis == params.basis)
                if applicable
                else 0
            )
            excess = max(0, current - params.maximum_ects)
            add(
                rule,
                not excess,
                current,
                params.maximum_ects,
                _gap("ects", excess, f"{excess} recognized ECTS above cap") if excess else None,
            )
        elif params.type == "max_study_duration":
            applicable = not params.study_modes or student.study_mode in params.study_modes
            semesters = [item.semester for item in candidates if item.semester]
            elapsed = (
                _semester_count(
                    str(student.start_semester),
                    max(semesters) if semesters else str(student.start_semester),
                    set(map(str, student.interruption_semesters)),
                )
                if applicable
                else 0
            )
            too_many_interruptions = (
                len(student.interruption_semesters) > params.maximum_interruptions
            )
            exceeded = elapsed > params.maximum_semesters
            add(
                rule,
                not (exceeded or too_many_interruptions),
                elapsed,
                params.maximum_semesters,
                None
                if not (exceeded or too_many_interruptions)
                else _gap("semesters", elapsed, "Maximum study duration or interruptions exceeded"),
            )
        elif params.type == "custom_note":
            checked = checklist_state.get(rule.id, False)
            add(
                rule,
                checked,
                checked,
                True,
                None if checked else _gap("manual", rule.id, params.note),
                manual=not checked,
            )

    for rule in program.rules:
        if rule.type != "composite":
            continue
        params = rule.parameters
        dependencies = [result_by_id[item] for item in params.rule_ids if item in result_by_id]
        statuses = [item.status for item in dependencies]
        machine_fulfilled = (
            all(item in {"fulfilled", "provisional"} for item in statuses)
            if params.operator == "and"
            else any(item in {"fulfilled", "provisional"} for item in statuses)
        )
        if params.operator == "and":
            has_manual = any(item == "manual" for item in statuses)
        else:
            has_manual = False
        add(
            rule,
            machine_fulfilled and not has_manual,
            statuses,
            params.rule_ids,
            None,
            manual=has_manual,
        )

    goals: list[GoalResult] = []
    for rule in program.rules:
        if rule.type != "composite":
            continue
        result = result_by_id[rule.id]
        if result.status == "fulfilled":
            verdict: Literal["eligible", "not_eligible", "provisional"] = "eligible"
        elif result.status == "provisional":
            verdict = "provisional"
        else:
            verdict = "not_eligible"
        goals.append(GoalResult(id=rule.id, verdict=verdict, rule_ids=rule.parameters.rule_ids))
    verdict = (
        "not_eligible"
        if any(goal.verdict == "not_eligible" for goal in goals)
        else ("provisional" if any(goal.verdict == "provisional" for goal in goals) else "eligible")
    )
    goal_for_rule: dict[str, str] = {}
    for goal in program.rules:
        if goal.type == "composite":
            for rule_id in goal.parameters.rule_ids:
                goal_for_rule[rule_id] = goal.id.replace("_", " ").title()
    gaps = [
        {
            "rule_id": result.id,
            "text": f"{goal_for_rule[result.id]}: {result.gap.text}"
            if result.id in goal_for_rule
            else result.gap.text,
            "status": result.status,
        }
        for result in results
        if result.gap and result.status in {"not_fulfilled", "manual"}
    ]
    manual = [
        ManualChecklistResult(rule_id=result.id, checked=checklist_state.get(result.id, False))
        for result in results
        if result.type == "custom_note"
    ]
    issues = [
        OpenIssue(id=item.id, severity="warning", text=item.open_issue)
        for item in credits.recognized_credits
        if item.open_issue
    ]
    return CheckResult(
        mode=mode,
        verdict=verdict,
        goals=goals,
        rules=results,
        allocation=allocation,
        gaps=gaps,
        manual_checklist=manual,
        open_issues=issues,
        category_ects=category_ects,
        total_ects=total_ects,
    )

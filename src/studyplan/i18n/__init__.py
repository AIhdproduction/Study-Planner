"""Small CLI message catalogue."""

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "overview": "Overview",
        "rules": "Rules",
        "modules": "Modules",
        "credits": "My Credits",
        "allocation": "Allocation",
        "gaps": "Gaps",
        "sources": "Sources",
        "issues": "Open Issues",
        "computed": "computed by rule engine on",
        "overall_verdict": "Overall verdict",
        "goals": "Goals",
        "category_ects": "Category ECTS",
        "total_ects": "Total ECTS",
        "provisional": "Provisional",
        "provisional_reason": "Provisional reason",
        "manual_checklist": "Manual checklist",
        "checked": "checked",
        "open": "open",
        "id": "ID",
        "type": "Type",
        "status": "Status",
        "current": "Current",
        "target": "Target",
        "gap": "Gap",
        "code": "Code",
        "title": "Title",
        "categories": "Categories",
        "mandatory": "Mandatory",
        "module_code": "Module code",
        "semester": "Semester",
        "ects": "ECTS",
        "grade": "Grade",
        "passed": "Passed",
        "category": "Category",
        "recognition_status": "Recognition status",
        "category_formula": "ECTS formula",
        "module": "Module",
        "recognized_credit": "Recognized credit",
        "reason": "Reason",
        "text": "Text",
        "document": "Document",
        "page": "Page",
        "severity": "Severity",
        "thesis_admission": "Thesis admission",
        "graduation": "Graduation",
        "eligible": "eligible",
        "not_eligible": "not eligible",
        "fulfilled": "fulfilled",
        "not_fulfilled": "not fulfilled",
        "manual": "manual",
        "confirmed": "confirmed",
        "disclaimer": (
            "Not legally binding. The official study regulations and the program management decide."
        ),
        "validation_success": "Validation successful.",
        "profile_created": "Study profile created.",
        "environment_ready": "StudyPlan environment is ready.",
        "credit_added": "Credit added.",
        "credit_updated": "Credit updated.",
        "credit_removed": "Credit removed.",
        "recognition_added": "Recognized credit added.",
        "recognition_removed": "Recognized credit removed.",
        "backup_created": "Backup created.",
        "restored": "Backup restored.",
    },
    "de": {
        "overview": "Übersicht",
        "rules": "Regeln",
        "modules": "Module",
        "credits": "Meine Leistungen",
        "allocation": "Zuteilung",
        "gaps": "Lücken",
        "sources": "Quellen",
        "issues": "Offene Punkte",
        "computed": "vom Regelwerk berechnet am",
        "overall_verdict": "Gesamtergebnis",
        "goals": "Ziele",
        "category_ects": "ECTS nach Kategorie",
        "total_ects": "ECTS gesamt",
        "provisional": "Vorläufig",
        "provisional_reason": "Grund für Vorläufigkeit",
        "manual_checklist": "Manuelle Checkliste",
        "checked": "erledigt",
        "open": "offen",
        "id": "ID",
        "type": "Typ",
        "status": "Status",
        "current": "Aktuell",
        "target": "Vorgabe",
        "gap": "Lücke",
        "code": "Code",
        "title": "Titel",
        "categories": "Kategorien",
        "mandatory": "Pflicht",
        "module_code": "Modulcode",
        "semester": "Semester",
        "ects": "ECTS",
        "grade": "Note",
        "passed": "Bestanden",
        "category": "Kategorie",
        "recognition_status": "Anerkennungsstatus",
        "category_formula": "ECTS-Formel",
        "module": "Modul",
        "recognized_credit": "Anerkennung",
        "reason": "Begründung",
        "text": "Text",
        "document": "Dokument",
        "page": "Seite",
        "severity": "Stufe",
        "thesis_admission": "Bachelorarbeitszulassung",
        "graduation": "Abschluss",
        "eligible": "zugelassen",
        "not_eligible": "nicht zugelassen",
        "fulfilled": "erfüllt",
        "not_fulfilled": "nicht erfüllt",
        "manual": "manuell",
        "confirmed": "bestätigt",
        "disclaimer": (
            "Nicht rechtsverbindlich. Es gelten das offizielle Studienreglement und die "
            "Entscheide der Studiengangleitung."
        ),
        "validation_success": "Validierung erfolgreich.",
        "profile_created": "Studienprofil erstellt.",
        "environment_ready": "StudyPlan-Umgebung ist bereit.",
        "credit_added": "Leistung erfasst.",
        "credit_updated": "Leistung aktualisiert.",
        "credit_removed": "Leistung entfernt.",
        "recognition_added": "Anerkennung erfasst.",
        "recognition_removed": "Anerkennung entfernt.",
        "backup_created": "Sicherung erstellt.",
        "restored": "Sicherung wiederhergestellt.",
    },
}


def message(language: str, key: str) -> str:
    """Return a translated user-facing message, with English fallback."""
    return MESSAGES.get(language, MESSAGES["en"]).get(key, MESSAGES["en"].get(key, key))


def status_label(language: str, status: str) -> str:
    """Translate an engine status or verdict for human-readable reports."""
    return message(language, status)


def goal_label(language: str, goal_id: str) -> str:
    """Translate known goals and fall back to a readable identifier."""
    value = message(language, goal_id)
    return value if value != goal_id else goal_id.replace("_", " ").title()


def category_label(language: str, official_name: str) -> str:
    """Return the profile-language display label for the established categories."""
    if language != "de":
        return official_name
    return {
        "Core": "Kern",
        "Core-Project": "Projekt",
        "Project": "Projekt",
        "Related": "Erweiterung",
        "Minor": "Zusatz",
    }.get(official_name, official_name)


def localized_text(language: str, text: str) -> str:
    """Translate engine explanations while leaving unknown profile text intact."""
    if language != "de":
        return text
    replacements = {
        "Graduation: ": "",
        "Thesis Admission: ": "",
        "Thesis admission: ": "",
        "Category ": "Kategorie ",
        "Kategorie Core": "Kategorie Kern",
        "Kategorie Core-Project": "Kategorie Projekt",
        "Kategorie Project": "Kategorie Projekt",
        "Kategorie Related": "Kategorie Erweiterung",
        "Kategorie Minor": "Kategorie Zusatz",
        "At institution": "An der Hochschule",
        "ECTS missing": "ECTS fehlen",
        "required": "erforderlich",
        "Mandatory modules not passed": "Pflichtmodule nicht bestanden",
        "Required module": "Erforderliches Modul",
        "not passed": "nicht bestanden",
        "One of these modules is required:": "Eines dieser Module ist erforderlich:",
        "modules missing in category": "Module fehlen in Kategorie",
        "Prerequisites missing:": "Voraussetzungen fehlen:",
        "Maximum attempts reached:": "Maximale Anzahl Versuche erreicht:",
        "Third-attempt budget exceeded": "Budget für dritte Versuche überschritten",
        "Third attempt is excluded": "Dritter Versuch ist ausgeschlossen",
        "Level gate violated by:": "Stufenvoraussetzung verletzt durch:",
        "Level deadline exceeded; modules missing:": "Stufenfrist überschritten; fehlende Module:",
        "recognized ECTS above cap": "anerkannte ECTS über der Obergrenze",
        "Maximum study duration or interruptions exceeded": (
            "Maximale Studiendauer oder Unterbrüche überschritten"
        ),
        "No eligible category is available.": "Keine anrechenbare Kategorie ist verfügbar.",
        "Forced category assignment.": "Erzwungene Kategoriezuordnung.",
        "Category cap limits counted ECTS.": (
            "Die Kategorieobergrenze begrenzt die angerechneten ECTS."
        ),
        "Best deterministic allocation.": "Beste deterministische Zuordnung.",
        "Rule source is unverified.": "Die Regelquelle ist nicht verifiziert.",
        "Recognized credit is provisional.": "Die Anerkennung ist vorläufig.",
        "Uses an unverified code mapping.": "Verwendet eine nicht verifizierte Codezuordnung.",
        "Programme-specific thesis requirements require the thesis module description.": (
            "Studiengangsspezifische Anforderungen für die Bachelorarbeit benötigen "
            "die Modulbeschreibung der Bachelorarbeit."
        ),
        "Confirm the synthetic requirement.": "Synthetische Anforderung bestätigen.",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def without_goal_prefix(text: str) -> str:
    """Remove the engine's goal prefix when the caller already groups by goal."""
    for prefix in ("Graduation: ", "Thesis Admission: ", "Thesis admission: "):
        if text.startswith(prefix):
            return text.removeprefix(prefix)
    return text

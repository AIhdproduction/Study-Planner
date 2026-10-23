"""Pure rule evaluation and module allocation for StudyPlan."""

from .matching import CodeMatch, extract_code_stem, match_code
from .rules import CheckResult, evaluate

__all__ = ["CheckResult", "CodeMatch", "evaluate", "extract_code_stem", "match_code"]

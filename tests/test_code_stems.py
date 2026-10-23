from studyplan.engine import extract_code_stem, match_code
from studyplan.io import ProfileRepository
from tests.engine_support import PROFILES, program


def test_mycampus_stem_strips_only_run_suffix() -> None:
    assert extract_code_stem("mycampus", "TA.BA_WST+BAS_K.H2501") == "TA.BA_WST+BAS_K"


def test_mycampus_event_does_not_lose_its_suffix() -> None:
    assert extract_code_stem("mycampus", "TA.EINFTAGH25_DCA.2501") == "TA.EINFTAGH25_DCA.2501"


def test_timetable_stem_strips_department_and_type_prefix() -> None:
    assert extract_code_stem("timetable", "DCA-K-TA.BA_DT_PARAM") == "TA.BA_DT_PARAM"


def test_module_directory_stem_strips_version_suffix_only() -> None:
    assert extract_code_stem("module_directory", "TA.BA_PRAX_DCA_3F26.26") == "TA.BA_PRAX_DCA_3F26"


def test_identical_stem_matches_directly() -> None:
    result = match_code(program(), [], "mycampus", "SYN.CORE1.H9901")
    assert result.status == "direct" and result.curriculum_code == "SYN.CORE1"


def test_explicit_source_mapping_is_used() -> None:
    mappings = ProfileRepository(PROFILES).mappings("synthetic_u").mappings
    result = match_code(program(), mappings, "mycampus", "SYN.CORE1_K.H9901")
    assert result.status == "mapped" and result.curriculum_code == "SYN.CORE1"


def test_unknown_stem_is_unmapped() -> None:
    result = match_code(program(), [], "mycampus", "SYN.UNKNOWN.H9901")
    assert result.status == "unmapped" and result.curriculum_code is None


def test_explicit_null_mapping_is_not_in_curriculum() -> None:
    mappings = ProfileRepository(PROFILES).mappings("synthetic_u").mappings
    result = match_code(program(), mappings, "mycampus", "SYN.OUTSIDE.H9901")
    assert result.status == "not_in_curriculum" and result.curriculum_code is None

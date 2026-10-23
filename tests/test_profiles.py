from pathlib import Path

from studyplan.io import ProfileRepository


def test_hslu_profile_loads_with_all_modules() -> None:
    program = ProfileRepository(Path("profiles")).program(
        "hslu_ta", "digital_construction_architecture_2025"
    )
    assert len(program.modules) == 101
    assert (
        sum(
            module.ects
            for module in program.modules
            if module.mandatory and "core" in module.eligible_category_ids
        )
        == 84
    )
    assert (
        sum(
            module.ects
            for module in program.modules
            if module.mandatory and "core_project" in module.eligible_category_ids
        )
        == 54
    )


def test_every_mapping_target_exists_in_the_curriculum() -> None:
    repository = ProfileRepository(Path("profiles"))
    program = repository.program("hslu_ta", "digital_construction_architecture_2025")
    module_codes = {module.code for module in program.modules}
    assert all(
        mapping.curriculum_code is None or mapping.curriculum_code in module_codes
        for mapping in repository.mappings("hslu_ta").mappings
    )

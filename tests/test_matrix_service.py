import sqlite3

import pytest

from skills_matrix.domain.models import Engineer, Skill
from skills_matrix.persistence.database import (
    CompetencyRepository,
    EngineerRepository,
    SkillRepository,
    initialize_database,
)
from skills_matrix.services.matrix_service import MatrixService


@pytest.fixture()
def service() -> MatrixService:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    initialize_database(connection)
    return MatrixService(
        SkillRepository(connection),
        EngineerRepository(connection),
        CompetencyRepository(connection),
    )


def test_create_skill_validates_target_level(service: MatrixService) -> None:
    with pytest.raises(ValueError, match="target level"):
        service.create_skill("Python", "Backend", 6)


def test_profile_defaults_missing_competencies_to_zero(service: MatrixService) -> None:
    skill = service.create_skill("Python", "Backend", 4)
    engineer = service.create_engineer("Ava Patel", "Platform", "Senior Engineer")

    profile_engineer, profile = service.get_profile(engineer.id or 0)

    assert profile_engineer == engineer
    assert profile[0].skill == skill
    assert profile[0].level == 0
    assert profile[0].gap == 4


def test_set_competency_updates_profile_gap(service: MatrixService) -> None:
    skill = service.create_skill("Testing", "Quality", 4)
    engineer = service.create_engineer("Ben Morgan", "Platform", "Engineer")

    service.set_competency_level(engineer.id or 0, skill.id or 0, 3)
    _, profile = service.get_profile(engineer.id or 0)

    assert profile[0].level == 3
    assert profile[0].gap == 1


def test_gap_analysis_orders_largest_gap_first(service: MatrixService) -> None:
    python = service.create_skill("Python", "Backend", 5)
    sqlite = service.create_skill("SQLite", "Data", 3)
    ava = service.create_engineer("Ava Patel", "Platform", "Senior Engineer")
    ben = service.create_engineer("Ben Morgan", "Platform", "Engineer")
    service.set_competency_level(ava.id or 0, python.id or 0, 4)
    service.set_competency_level(ben.id or 0, python.id or 0, 2)
    service.set_competency_level(ava.id or 0, sqlite.id or 0, 3)
    service.set_competency_level(ben.id or 0, sqlite.id or 0, 3)

    gaps = service.calculate_skill_gaps("Platform")

    assert [gap.skill.name for gap in gaps] == ["Python", "SQLite"]
    assert gaps[0].average_level == 3
    assert gaps[0].gap == 2
    assert gaps[1].gap == 0


def test_training_recommendations_prioritize_largest_gaps(service: MatrixService) -> None:
    python = service.create_skill("Python", "Backend", 5)
    testing = service.create_skill("Testing", "Quality", 4)
    engineer = service.create_engineer("Diego Ramos", "Product", "Engineer")
    service.set_competency_level(engineer.id or 0, python.id or 0, 2)
    service.set_competency_level(engineer.id or 0, testing.id or 0, 3)

    recommendations = service.recommend_training(engineer.id or 0)

    assert [item.skill.name for item in recommendations] == ["Python", "Testing"]
    assert recommendations[0].current_level == 2
    assert recommendations[0].target_level == 5


def test_domain_models_reject_blank_required_fields() -> None:
    with pytest.raises(ValueError, match="skill name"):
        Skill(None, " ", "Backend", 3)
    with pytest.raises(ValueError, match="engineer name"):
        Engineer(None, "", "Platform", "Engineer")


def test_skill_and_engineer_update_delete(service: MatrixService) -> None:
    skill = service.create_skill("Python", "Backend", 3)
    engineer = service.create_engineer("Ava Patel", "Platform", "Engineer")

    service.update_skill(skill.id or 0, "Python", "Backend", 4, "Updated")
    service.update_engineer(engineer.id or 0, "Ava Patel", "Enablement", "Senior Engineer")

    assert service.list_skills()[0].target_level == 4
    assert service.list_engineers()[0].team == "Enablement"

    service.delete_skill(skill.id or 0)
    service.delete_engineer(engineer.id or 0)

    assert service.list_skills() == []
    assert service.list_engineers() == []

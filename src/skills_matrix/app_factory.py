from __future__ import annotations

from pathlib import Path

from skills_matrix.persistence.database import (
    CompetencyRepository,
    EngineerRepository,
    SkillRepository,
    connect,
    initialize_database,
    seed_demo_data,
)
from skills_matrix.services.matrix_service import MatrixService


def create_service(db_path: Path | str | None = None, seed: bool = True) -> MatrixService:
    connection = connect(db_path) if db_path is not None else connect()
    initialize_database(connection)
    if seed:
        seed_demo_data(connection)
    return MatrixService(
        SkillRepository(connection),
        EngineerRepository(connection),
        CompetencyRepository(connection),
    )


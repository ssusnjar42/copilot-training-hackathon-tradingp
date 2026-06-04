from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from skills_matrix.domain.models import Competency, Engineer, Skill


DEFAULT_DB_PATH = Path("data") / "skills_matrix.db"


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    target_level INTEGER NOT NULL CHECK (target_level BETWEEN 0 AND 5),
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS engineers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competencies (
    engineer_id INTEGER NOT NULL REFERENCES engineers(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 5),
    PRIMARY KEY (engineer_id, skill_id)
);
"""


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    if path != Path(":memory:"):
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


class SkillRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list(self) -> list[Skill]:
        rows = self.connection.execute(
            "SELECT id, name, category, target_level, description FROM skills ORDER BY category, name"
        ).fetchall()
        return [_skill_from_row(row) for row in rows]

    def get(self, skill_id: int) -> Skill | None:
        row = self.connection.execute(
            "SELECT id, name, category, target_level, description FROM skills WHERE id = ?",
            (skill_id,),
        ).fetchone()
        return _skill_from_row(row) if row else None

    def create(self, skill: Skill) -> Skill:
        cursor = self.connection.execute(
            """
            INSERT INTO skills (name, category, target_level, description)
            VALUES (?, ?, ?, ?)
            """,
            (skill.name, skill.category, skill.target_level, skill.description),
        )
        self.connection.commit()
        return Skill(cursor.lastrowid, skill.name, skill.category, skill.target_level, skill.description)

    def update(self, skill: Skill) -> Skill:
        if skill.id is None:
            raise ValueError("skill id is required for update")
        cursor = self.connection.execute(
            """
            UPDATE skills
            SET name = ?, category = ?, target_level = ?, description = ?
            WHERE id = ?
            """,
            (skill.name, skill.category, skill.target_level, skill.description, skill.id),
        )
        self.connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"skill {skill.id} does not exist")
        return skill

    def delete(self, skill_id: int) -> None:
        self.connection.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        self.connection.commit()


class EngineerRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list(self) -> list[Engineer]:
        rows = self.connection.execute(
            "SELECT id, name, team, role FROM engineers ORDER BY team, name"
        ).fetchall()
        return [_engineer_from_row(row) for row in rows]

    def list_teams(self) -> list[str]:
        rows = self.connection.execute("SELECT DISTINCT team FROM engineers ORDER BY team").fetchall()
        return [row["team"] for row in rows]

    def get(self, engineer_id: int) -> Engineer | None:
        row = self.connection.execute(
            "SELECT id, name, team, role FROM engineers WHERE id = ?",
            (engineer_id,),
        ).fetchone()
        return _engineer_from_row(row) if row else None

    def create(self, engineer: Engineer) -> Engineer:
        cursor = self.connection.execute(
            "INSERT INTO engineers (name, team, role) VALUES (?, ?, ?)",
            (engineer.name, engineer.team, engineer.role),
        )
        self.connection.commit()
        return Engineer(cursor.lastrowid, engineer.name, engineer.team, engineer.role)

    def update(self, engineer: Engineer) -> Engineer:
        if engineer.id is None:
            raise ValueError("engineer id is required for update")
        cursor = self.connection.execute(
            "UPDATE engineers SET name = ?, team = ?, role = ? WHERE id = ?",
            (engineer.name, engineer.team, engineer.role, engineer.id),
        )
        self.connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"engineer {engineer.id} does not exist")
        return engineer

    def delete(self, engineer_id: int) -> None:
        self.connection.execute("DELETE FROM engineers WHERE id = ?", (engineer_id,))
        self.connection.commit()


class CompetencyRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_for_engineer(self, engineer_id: int) -> list[Competency]:
        rows = self.connection.execute(
            "SELECT engineer_id, skill_id, level FROM competencies WHERE engineer_id = ?",
            (engineer_id,),
        ).fetchall()
        return [_competency_from_row(row) for row in rows]

    def list_all(self) -> list[Competency]:
        rows = self.connection.execute("SELECT engineer_id, skill_id, level FROM competencies").fetchall()
        return [_competency_from_row(row) for row in rows]

    def set_level(self, competency: Competency) -> Competency:
        self.connection.execute(
            """
            INSERT INTO competencies (engineer_id, skill_id, level)
            VALUES (?, ?, ?)
            ON CONFLICT(engineer_id, skill_id) DO UPDATE SET level = excluded.level
            """,
            (competency.engineer_id, competency.skill_id, competency.level),
        )
        self.connection.commit()
        return competency

    def replace_for_engineer(self, engineer_id: int, competencies: Iterable[Competency]) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM competencies WHERE engineer_id = ?", (engineer_id,))
            self.connection.executemany(
                "INSERT INTO competencies (engineer_id, skill_id, level) VALUES (?, ?, ?)",
                [(item.engineer_id, item.skill_id, item.level) for item in competencies],
            )


def seed_demo_data(connection: sqlite3.Connection) -> None:
    existing_skills = connection.execute("SELECT COUNT(*) AS count FROM skills").fetchone()["count"]
    existing_engineers = connection.execute("SELECT COUNT(*) AS count FROM engineers").fetchone()["count"]
    if existing_skills or existing_engineers:
        return

    skills = [
        ("Python", "Backend", 4, "Build maintainable services and automation with Python."),
        ("SQLite", "Data", 3, "Design local relational persistence and queries."),
        ("NiceGUI", "Frontend", 3, "Build productive Python web interfaces."),
        ("Testing", "Quality", 4, "Create reliable automated tests around business behavior."),
        ("Cloud Fundamentals", "Platform", 3, "Understand deployment and runtime fundamentals."),
    ]
    engineers = [
        ("Ava Patel", "Platform", "Senior Engineer"),
        ("Ben Morgan", "Platform", "Engineer"),
        ("Chloe Smith", "Product", "Tech Lead"),
        ("Diego Ramos", "Product", "Engineer"),
        ("Elena Novak", "Data", "Engineer"),
    ]

    with connection:
        connection.executemany(
            "INSERT INTO skills (name, category, target_level, description) VALUES (?, ?, ?, ?)",
            skills,
        )
        connection.executemany("INSERT INTO engineers (name, team, role) VALUES (?, ?, ?)", engineers)

        skill_rows = connection.execute("SELECT id, name FROM skills").fetchall()
        engineer_rows = connection.execute("SELECT id, name FROM engineers").fetchall()
        skill_ids = {row["name"]: row["id"] for row in skill_rows}
        engineer_ids = {row["name"]: row["id"] for row in engineer_rows}
        levels = {
            "Ava Patel": {"Python": 5, "SQLite": 3, "NiceGUI": 2, "Testing": 4, "Cloud Fundamentals": 4},
            "Ben Morgan": {"Python": 3, "SQLite": 2, "NiceGUI": 3, "Testing": 3, "Cloud Fundamentals": 2},
            "Chloe Smith": {"Python": 4, "SQLite": 3, "NiceGUI": 4, "Testing": 4, "Cloud Fundamentals": 3},
            "Diego Ramos": {"Python": 2, "SQLite": 2, "NiceGUI": 3, "Testing": 2, "Cloud Fundamentals": 1},
            "Elena Novak": {"Python": 3, "SQLite": 5, "NiceGUI": 1, "Testing": 3, "Cloud Fundamentals": 2},
        }
        connection.executemany(
            "INSERT INTO competencies (engineer_id, skill_id, level) VALUES (?, ?, ?)",
            [
                (engineer_ids[engineer_name], skill_ids[skill_name], level)
                for engineer_name, skill_levels in levels.items()
                for skill_name, level in skill_levels.items()
            ],
        )


def _skill_from_row(row: sqlite3.Row) -> Skill:
    return Skill(row["id"], row["name"], row["category"], row["target_level"], row["description"])


def _engineer_from_row(row: sqlite3.Row) -> Engineer:
    return Engineer(row["id"], row["name"], row["team"], row["role"])


def _competency_from_row(row: sqlite3.Row) -> Competency:
    return Competency(row["engineer_id"], row["skill_id"], row["level"])


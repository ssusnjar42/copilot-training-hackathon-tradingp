from __future__ import annotations

from dataclasses import dataclass


MIN_LEVEL = 0
MAX_LEVEL = 5


def validate_level(level: int, field_name: str = "level") -> int:
    if not isinstance(level, int):
        raise TypeError(f"{field_name} must be an integer")
    if level < MIN_LEVEL or level > MAX_LEVEL:
        raise ValueError(f"{field_name} must be between {MIN_LEVEL} and {MAX_LEVEL}")
    return level


def validate_required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


@dataclass(frozen=True)
class Skill:
    id: int | None
    name: str
    category: str
    target_level: int
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", validate_required(self.name, "skill name"))
        object.__setattr__(self, "category", validate_required(self.category, "skill category"))
        validate_level(self.target_level, "target level")


@dataclass(frozen=True)
class Engineer:
    id: int | None
    name: str
    team: str
    role: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", validate_required(self.name, "engineer name"))
        object.__setattr__(self, "team", validate_required(self.team, "team"))
        object.__setattr__(self, "role", validate_required(self.role, "role"))


@dataclass(frozen=True)
class Competency:
    engineer_id: int
    skill_id: int
    level: int

    def __post_init__(self) -> None:
        validate_level(self.level, "competency level")


@dataclass(frozen=True)
class ProfileSkill:
    skill: Skill
    level: int
    gap: int


@dataclass(frozen=True)
class HeatmapRow:
    engineer: Engineer
    levels_by_skill_id: dict[int, int]


@dataclass(frozen=True)
class SkillGap:
    skill: Skill
    average_level: float
    gap: float


@dataclass(frozen=True)
class TrainingRecommendation:
    engineer: Engineer
    skill: Skill
    current_level: int
    target_level: int
    recommendation: str


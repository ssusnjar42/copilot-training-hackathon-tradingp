from __future__ import annotations

from skills_matrix.domain.models import (
    Competency,
    Engineer,
    HeatmapRow,
    ProfileSkill,
    Skill,
    SkillGap,
    TrainingRecommendation,
)
from skills_matrix.persistence.database import CompetencyRepository, EngineerRepository, SkillRepository


class MatrixService:
    def __init__(
        self,
        skills: SkillRepository,
        engineers: EngineerRepository,
        competencies: CompetencyRepository,
    ) -> None:
        self.skills = skills
        self.engineers = engineers
        self.competencies = competencies

    def list_skills(self) -> list[Skill]:
        return self.skills.list()

    def create_skill(self, name: str, category: str, target_level: int, description: str = "") -> Skill:
        return self.skills.create(Skill(None, name, category, target_level, description.strip()))

    def update_skill(
        self,
        skill_id: int,
        name: str,
        category: str,
        target_level: int,
        description: str = "",
    ) -> Skill:
        return self.skills.update(Skill(skill_id, name, category, target_level, description.strip()))

    def delete_skill(self, skill_id: int) -> None:
        self.skills.delete(skill_id)

    def list_engineers(self) -> list[Engineer]:
        return self.engineers.list()

    def list_teams(self) -> list[str]:
        return self.engineers.list_teams()

    def create_engineer(self, name: str, team: str, role: str) -> Engineer:
        return self.engineers.create(Engineer(None, name, team, role))

    def update_engineer(self, engineer_id: int, name: str, team: str, role: str) -> Engineer:
        return self.engineers.update(Engineer(engineer_id, name, team, role))

    def delete_engineer(self, engineer_id: int) -> None:
        self.engineers.delete(engineer_id)

    def get_profile(self, engineer_id: int) -> tuple[Engineer, list[ProfileSkill]]:
        engineer = self.engineers.get(engineer_id)
        if engineer is None:
            raise ValueError(f"engineer {engineer_id} does not exist")

        competencies = {item.skill_id: item.level for item in self.competencies.list_for_engineer(engineer_id)}
        profile = [
            ProfileSkill(skill, competencies.get(skill.id or 0, 0), max(skill.target_level - competencies.get(skill.id or 0, 0), 0))
            for skill in self.skills.list()
        ]
        return engineer, profile

    def set_competency_level(self, engineer_id: int, skill_id: int, level: int) -> Competency:
        if self.engineers.get(engineer_id) is None:
            raise ValueError(f"engineer {engineer_id} does not exist")
        if self.skills.get(skill_id) is None:
            raise ValueError(f"skill {skill_id} does not exist")
        return self.competencies.set_level(Competency(engineer_id, skill_id, level))

    def build_heatmap(self, team: str | None = None) -> tuple[list[Skill], list[HeatmapRow]]:
        skills = self.skills.list()
        skill_ids = [skill.id for skill in skills if skill.id is not None]
        engineers = [
            engineer for engineer in self.engineers.list()
            if team is None or engineer.team == team
        ]
        all_competencies = self.competencies.list_all()
        level_lookup = {
            (item.engineer_id, item.skill_id): item.level
            for item in all_competencies
        }
        rows = [
            HeatmapRow(
                engineer,
                {skill_id: level_lookup.get((engineer.id or 0, skill_id), 0) for skill_id in skill_ids},
            )
            for engineer in engineers
        ]
        return skills, rows

    def calculate_skill_gaps(self, team: str | None = None) -> list[SkillGap]:
        skills, heatmap_rows = self.build_heatmap(team)
        if not heatmap_rows:
            return [SkillGap(skill, 0.0, float(skill.target_level)) for skill in skills]

        gaps: list[SkillGap] = []
        for skill in skills:
            if skill.id is None:
                continue
            average = sum(row.levels_by_skill_id.get(skill.id, 0) for row in heatmap_rows) / len(heatmap_rows)
            gaps.append(SkillGap(skill, round(average, 2), round(max(skill.target_level - average, 0), 2)))
        return sorted(gaps, key=lambda item: (-item.gap, item.skill.name))

    def recommend_training(self, engineer_id: int) -> list[TrainingRecommendation]:
        engineer, profile = self.get_profile(engineer_id)
        recommendations = [
            TrainingRecommendation(
                engineer=engineer,
                skill=item.skill,
                current_level=item.level,
                target_level=item.skill.target_level,
                recommendation=_recommendation_text(item.skill.name, item.level, item.skill.target_level),
            )
            for item in profile
            if item.gap > 0
        ]
        return sorted(recommendations, key=lambda item: (-(item.target_level - item.current_level), item.skill.name))


def _recommendation_text(skill_name: str, current_level: int, target_level: int) -> str:
    if current_level == 0:
        return f"Start with an introductory {skill_name} course and pair with a mentor."
    if target_level - current_level >= 2:
        return f"Prioritize a structured {skill_name} learning path and apply it in a project."
    return f"Close the remaining {skill_name} gap with focused practice and review."


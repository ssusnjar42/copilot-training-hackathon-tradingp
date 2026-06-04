from __future__ import annotations

import os
from typing import Any

from nicegui import app, ui
from nicegui.elements.dark_mode import DarkMode

from skills_matrix.app_factory import create_service
from skills_matrix.domain.models import MAX_LEVEL, MIN_LEVEL
from skills_matrix.services.matrix_service import MatrixService


class LazyMatrixService:
    _service: MatrixService | None = None

    def _get(self) -> MatrixService:
        if self._service is None:
            self._service = create_service()
        return self._service

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)


service = LazyMatrixService()
THEME_STORAGE_KEY = "theme"
DARK_THEME = "dark"
LIGHT_THEME = "light"
STORAGE_SECRET_ENV = "SKILLS_MATRIX_STORAGE_SECRET"


def run() -> None:
    build_pages()
    ui.run(
        title="Team Skills Matrix",
        storage_secret=os.environ.get(STORAGE_SECRET_ENV, "skills-matrix-development-secret"),
    )


def build_pages() -> None:
    @ui.page("/")
    def dashboard() -> None:
        page_frame("Dashboard")
        skills = service.list_skills()
        engineers = service.list_engineers()
        gaps = service.calculate_skill_gaps()
        with ui.row().classes("gap-4"):
            metric_card("Engineers", str(len(engineers)))
            metric_card("Skills", str(len(skills)))
            metric_card("Largest gap", f"{gaps[0].skill.name}: {gaps[0].gap}" if gaps else "None")
        ui.label("Team Skills Matrix").classes("text-2xl font-bold mt-6")
        ui.label("Manage engineering skills, profiles, heatmaps, gaps, and training recommendations.")

    @ui.page("/skills")
    def skills_page() -> None:
        page_frame("Skills inventory")
        render_skill_form()
        render_skills_table()

    @ui.page("/engineers")
    def engineers_page() -> None:
        page_frame("Engineers inventory")
        render_engineer_form()
        render_engineers_table()

    @ui.page("/profile/{engineer_id}")
    def profile_page(engineer_id: int) -> None:
        engineer, profile = service.get_profile(engineer_id)
        page_frame(f"{engineer.name} profile")
        ui.label(f"{engineer.team} - {engineer.role}").classes("text-lg text-gray-600")
        for item in profile:
            with ui.row().classes("items-center gap-4 w-full"):
                ui.label(item.skill.name).classes("w-48 font-medium")
                ui.label(f"Target {item.skill.target_level}").classes("w-24")
                ui.select(
                    options=list(range(MIN_LEVEL, MAX_LEVEL + 1)),
                    value=item.level,
                    on_change=lambda event, skill_id=item.skill.id: update_competency(engineer_id, skill_id, event.value),
                ).classes("w-32")
                ui.label(f"Gap {item.gap}").classes("w-20")

        ui.separator().classes("my-4")
        ui.label("Training recommendations").classes("text-xl font-bold")
        recommendations = service.recommend_training(engineer_id)
        if not recommendations:
            ui.label("No recommendations: this engineer meets all current target levels.")
        for recommendation in recommendations:
            with ui.card().classes("w-full"):
                ui.label(recommendation.skill.name).classes("font-bold")
                ui.label(recommendation.recommendation)

    @ui.page("/heatmap")
    def heatmap_page() -> None:
        page_frame("Team heatmap")
        selected_team = ui.select(options=["All teams", *service.list_teams()], value="All teams", label="Team").classes("w-64")
        container = ui.column().classes("w-full")

        def refresh() -> None:
            container.clear()
            team = None if selected_team.value == "All teams" else selected_team.value
            with container:
                render_heatmap(team)

        selected_team.on("update:model-value", lambda _: refresh())
        refresh()

    @ui.page("/gaps")
    def gaps_page() -> None:
        page_frame("Skill gap analysis")
        render_gap_analysis()

    @ui.page("/recommendations")
    def recommendations_page() -> None:
        page_frame("Training recommendations")
        for engineer in service.list_engineers():
            recommendations = service.recommend_training(engineer.id or 0)
            with ui.card().classes("w-full"):
                ui.label(f"{engineer.name} ({engineer.team})").classes("font-bold")
                if not recommendations:
                    ui.label("Meets all current targets.")
                for recommendation in recommendations[:3]:
                    ui.label(f"{recommendation.skill.name}: {recommendation.recommendation}")


def page_frame(title: str) -> None:
    dark_mode = ui.dark_mode()
    is_dark = app_storage_theme() == DARK_THEME
    dark_mode.set_value(is_dark)
    ui.page_title(title)
    with ui.header().classes("items-center justify-between"):
        ui.label("Team Skills Matrix").classes("text-xl font-bold")
        with ui.row().classes("items-center gap-3"):
            for label, target in [
                ("Dashboard", "/"),
                ("Skills", "/skills"),
                ("Engineers", "/engineers"),
                ("Heatmap", "/heatmap"),
                ("Gaps", "/gaps"),
                ("Recommendations", "/recommendations"),
            ]:
                ui.link(label, target).classes("text-white")
            render_theme_toggle(dark_mode, is_dark)
    ui.label(title).classes("text-3xl font-bold my-4")


def render_theme_toggle(dark_mode: DarkMode, is_dark: bool) -> None:
    def toggle_theme() -> None:
        next_is_dark = not dark_mode.value
        dark_mode.set_value(next_is_dark)
        app.storage.user[THEME_STORAGE_KEY] = DARK_THEME if next_is_dark else LIGHT_THEME
        ui.notify(f"{'Dark' if next_is_dark else 'Light'} theme selected")
        ui.navigate.reload()

    ui.button(
        "Dark theme" if not is_dark else "Light theme",
        icon="dark_mode" if not is_dark else "light_mode",
        on_click=toggle_theme,
    )


def app_storage_theme() -> str:
    theme = app.storage.user.get(THEME_STORAGE_KEY, LIGHT_THEME)
    return DARK_THEME if theme == DARK_THEME else LIGHT_THEME


def metric_card(label: str, value: str) -> None:
    with ui.card().classes("w-56"):
        ui.label(label).classes("text-gray-600")
        ui.label(value).classes("text-3xl font-bold")


def render_skill_form() -> None:
    with ui.card().classes("w-full"):
        ui.label("Add skill").classes("text-xl font-bold")
        name = ui.input("Name").classes("w-full")
        category = ui.input("Category").classes("w-full")
        target_level = ui.select(options=list(range(MIN_LEVEL, MAX_LEVEL + 1)), value=3, label="Target level").classes("w-48")
        description = ui.textarea("Description").classes("w-full")

        def save() -> None:
            service.create_skill(name.value, category.value, int(target_level.value), description.value or "")
            ui.notify("Skill added")
            ui.navigate.reload()

        ui.button("Add skill", on_click=save)


def render_skills_table() -> None:
    ui.label("Existing skills").classes("text-xl font-bold mt-4")
    for skill in service.list_skills():
        with ui.card().classes("w-full"):
            name = ui.input("Name", value=skill.name).classes("w-full")
            category = ui.input("Category", value=skill.category).classes("w-full")
            target_level = ui.select(
                options=list(range(MIN_LEVEL, MAX_LEVEL + 1)),
                value=skill.target_level,
                label="Target level",
            ).classes("w-48")
            description = ui.textarea("Description", value=skill.description).classes("w-full")

            def save(
                skill_id: int | None = skill.id,
                name_input=name,
                category_input=category,
                target_input=target_level,
                description_input=description,
            ) -> None:
                if skill_id is None:
                    raise ValueError("skill id is required")
                service.update_skill(
                    skill_id,
                    name_input.value,
                    category_input.value,
                    int(target_input.value),
                    description_input.value or "",
                )
                ui.notify("Skill updated")
                ui.navigate.reload()

            def delete(skill_id: int | None = skill.id) -> None:
                if skill_id is None:
                    raise ValueError("skill id is required")
                service.delete_skill(skill_id)
                ui.notify("Skill deleted")
                ui.navigate.reload()

            with ui.row().classes("gap-2"):
                ui.button("Save", on_click=save)
                ui.button("Delete", on_click=delete).props("color=negative")


def render_engineer_form() -> None:
    with ui.card().classes("w-full"):
        ui.label("Add engineer").classes("text-xl font-bold")
        name = ui.input("Name").classes("w-full")
        team = ui.input("Team").classes("w-full")
        role = ui.input("Role").classes("w-full")

        def save() -> None:
            service.create_engineer(name.value, team.value, role.value)
            ui.notify("Engineer added")
            ui.navigate.reload()

        ui.button("Add engineer", on_click=save)


def render_engineers_table() -> None:
    ui.label("Existing engineers").classes("text-xl font-bold mt-4")
    for engineer in service.list_engineers():
        with ui.card().classes("w-full"):
            name = ui.input("Name", value=engineer.name).classes("w-full")
            team = ui.input("Team", value=engineer.team).classes("w-full")
            role = ui.input("Role", value=engineer.role).classes("w-full")

            def save(engineer_id: int | None = engineer.id, name_input=name, team_input=team, role_input=role) -> None:
                if engineer_id is None:
                    raise ValueError("engineer id is required")
                service.update_engineer(engineer_id, name_input.value, team_input.value, role_input.value)
                ui.notify("Engineer updated")
                ui.navigate.reload()

            def delete(engineer_id: int | None = engineer.id) -> None:
                if engineer_id is None:
                    raise ValueError("engineer id is required")
                service.delete_engineer(engineer_id)
                ui.notify("Engineer deleted")
                ui.navigate.reload()

            with ui.row().classes("items-center gap-2"):
                ui.link("Open profile", f"/profile/{engineer.id}")
                ui.button("Save", on_click=save)
                ui.button("Delete", on_click=delete).props("color=negative")


def render_heatmap(team: str | None = None) -> None:
    skills, rows = service.build_heatmap(team)
    if not skills or not rows:
        ui.label("No heatmap data available.")
        return

    with ui.row().classes("items-center gap-2 font-bold"):
        ui.label("Engineer").classes("w-48")
        for skill in skills:
            ui.label(skill.name).classes("w-32 text-center")

    for row in rows:
        with ui.row().classes("items-center gap-2"):
            ui.label(row.engineer.name).classes("w-48 font-medium")
            for skill in skills:
                ui.select(
                    options=list(range(MIN_LEVEL, MAX_LEVEL + 1)),
                    value=row.levels_by_skill_id.get(skill.id or 0, 0),
                    on_change=lambda event, engineer_id=row.engineer.id, skill_id=skill.id: update_competency(
                        engineer_id or 0,
                        skill_id,
                        event.value,
                    ),
                ).classes("w-32")


def render_gap_analysis() -> None:
    for gap in service.calculate_skill_gaps():
        with ui.card().classes("w-full"):
            ui.label(gap.skill.name).classes("font-bold")
            ui.label(f"Target {gap.skill.target_level}, average {gap.average_level}, gap {gap.gap}")


def update_competency(engineer_id: int, skill_id: int | None, value: int) -> None:
    if skill_id is None:
        raise ValueError("skill id is required")
    service.set_competency_level(engineer_id, skill_id, int(value))
    ui.notify("Competency updated")


if __name__ in {"__main__", "__mp_main__"}:
    run()

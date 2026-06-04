# Repository instructions for Copilot

This repository implements the advanced GitHub Copilot hackathon assignment as a Team Skills Matrix Platform: a Python-backed web application where engineers maintain skill competency profiles, leads browse engineers and teams, the organization maintains a skills inventory with target levels, and heatmaps, skill gaps, and training recommendations guide development.

## Build, test, and lint commands

- Install dependencies: `python -m pip install -e .[dev]`
- Run the app: `python -m skills_matrix.main` or `skills-matrix`
- Optional persisted user preference secret: set `SKILLS_MATRIX_STORAGE_SECRET` before running the app; otherwise a development default is used.
- Run all tests: `python -m pytest`
- Run a single test: `python -m pytest tests\test_matrix_service.py::test_gap_analysis_orders_largest_gap_first`
- Compile check: `python -m compileall src tests`
- No linter is configured yet.

## High-level architecture

- Use Python for the backend.
- Use the `nicegui` pip package for the frontend UI.
- Use SQLite as the datastore.
- The app is a single Python process with separated packages: NiceGUI pages in `src\skills_matrix\main.py`, domain validation/models in `src\skills_matrix\domain`, business use cases in `src\skills_matrix\services`, and SQLite schema/repositories/seed data in `src\skills_matrix\persistence`.
- Local development data is created in `data\skills_matrix.db` and seeded with demo teams, engineers, skills, competency levels, and targets when empty.
- Model the product around these core areas:
  - Skills inventory: shared skill definitions with target levels and create/update/delete workflows.
  - Engineers inventory: engineer records with name, team, role, and navigation to profiles.
  - Engineer profile: each engineer's competency levels across the shared skills inventory.
  - Team heatmaps: team-level proficiency visualization with inline level adjustment.
  - Skill gap analysis: skills ranked by the delta between organization target and team average.
  - Training recommendations: per-engineer next learning steps derived from gaps.
- Implemented feature areas include skills inventory, engineers inventory, engineer profiles, team heatmap editing, skill gap analysis, and training recommendations.

## Key conventions

- Keep project-level guidance in `.github/copilot-instructions.md`; as the codebase grows, add focused instructions for backend, frontend, and path-specific areas rather than overloading this file.
- Use spec-driven development with OpenSpec for the later features named in the README, with one proposal per requirement: team heatmaps, skill gap analysis, and training recommendations.
- Backend/domain behavior is covered with pytest tests in `tests\`, using isolated in-memory SQLite databases.
- Add browser tests for major user flows once the NiceGUI UI stabilizes further.
- Prefer agentic workflows from the assignment: use planning before substantial feature implementation, maintain custom skills for repeated QA workflows, and verify behavior after each implementation iteration.

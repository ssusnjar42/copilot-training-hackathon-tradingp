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

- The app is a single Python process using NiceGUI for UI and SQLite for persistence.
- `src\skills_matrix\main.py` defines all NiceGUI pages and UI helpers. It lazy-loads the service so importing the module does not create or lock `data\skills_matrix.db`.
- `src\skills_matrix\domain\models.py` owns the immutable dataclasses and shared level validation. Skill and competency levels are always integers from `0` to `5`.
- `src\skills_matrix\services\matrix_service.py` is the business/use-case layer for CRUD, profiles, heatmaps, skill gaps, and training recommendations. Keep business calculations here rather than in NiceGUI event handlers.
- `src\skills_matrix\persistence\database.py` owns SQLite connection setup, schema creation, repository classes, transactions, and demo seed data. `create_service()` wires repositories into the service.
- Local app data is stored in `data\skills_matrix.db` and is seeded only when both skills and engineers are empty. User UI preferences such as theme are persisted via NiceGUI `app.storage.user`.
- Pytest tests in `tests\` exercise domain/service behavior using isolated in-memory SQLite databases.

## Tech stack and packaging

- Python package source lives under `src\`; pytest is configured with `pythonpath = ["src"]` in `pyproject.toml`.
- Runtime dependency: `nicegui>=2.0`.
- Dev dependency: `pytest>=8.0`.
- Console script entry point: `skills-matrix = "skills_matrix.main:run"`.
- Package discovery uses setuptools with `where = ["src"]`.

## Program structure

- `src\skills_matrix\app_factory.py`
  - `create_service(db_path=None, seed=True)` opens SQLite, initializes schema, optionally seeds demo data, and returns `MatrixService`.
  - Tests can pass `":memory:"` or construct repositories directly around an in-memory connection.
- `src\skills_matrix\main.py`
  - `run()` registers pages via `build_pages()` and starts NiceGUI with `storage_secret` from `SKILLS_MATRIX_STORAGE_SECRET` or a development default.
  - `LazyMatrixService` defers `create_service()` until a page needs data, preventing import-time database creation/locking.
  - Pages: `/`, `/skills`, `/engineers`, `/profile/{engineer_id}`, `/heatmap`, `/gaps`, `/recommendations`.
  - Shared UI helpers include `page_frame`, `render_theme_toggle`, `render_level_picker`, `render_skill_score_button`, `skill_score_button_style`, and `update_competency`.
- `src\skills_matrix\domain\models.py`
  - `Skill(id, name, category, target_level, description="")`
  - `Engineer(id, name, team, role)`
  - `Competency(engineer_id, skill_id, level)`
  - View/result models: `ProfileSkill`, `HeatmapRow`, `SkillGap`, `TrainingRecommendation`.
  - `validate_required` trims and rejects blank required strings. `validate_level` enforces integer levels from `MIN_LEVEL = 0` through `MAX_LEVEL = 5`.
- `src\skills_matrix\services\matrix_service.py`
  - `MatrixService` composes `SkillRepository`, `EngineerRepository`, and `CompetencyRepository`.
  - Provides CRUD wrappers for skills/engineers, `get_profile`, `set_competency_level`, `build_heatmap`, `calculate_skill_gaps`, and `recommend_training`.
  - Missing competencies render as level `0`; profile gaps and skill gaps never go below `0`.
  - Skill gaps are sorted by largest gap descending, then skill name. Recommendations are sorted by largest individual gap descending, then skill name.
- `src\skills_matrix\persistence\database.py`
  - `connect()` creates parent directories for file-backed DBs, sets `sqlite3.Row`, and enables foreign keys.
  - Repository classes return domain dataclasses rather than raw SQLite rows.
  - `seed_demo_data()` exits if either skills or engineers already exist; it does not merge seed data into an existing DB.

## Database schema

- `skills`
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `name TEXT NOT NULL UNIQUE`
  - `category TEXT NOT NULL`
  - `target_level INTEGER NOT NULL CHECK (target_level BETWEEN 0 AND 5)`
  - `description TEXT NOT NULL DEFAULT ''`
- `engineers`
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `name TEXT NOT NULL`
  - `team TEXT NOT NULL`
  - `role TEXT NOT NULL`
- `competencies`
  - `engineer_id INTEGER NOT NULL REFERENCES engineers(id) ON DELETE CASCADE`
  - `skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE`
  - `level INTEGER NOT NULL CHECK (level BETWEEN 0 AND 5)`
  - Primary key: `(engineer_id, skill_id)`
- Competency updates use SQLite upsert: `ON CONFLICT(engineer_id, skill_id) DO UPDATE SET level = excluded.level`.

## Tests

- `tests\test_matrix_service.py` builds a fresh in-memory SQLite database per test with `initialize_database`.
- Existing tests cover level validation, blank required fields, profile defaults, competency updates, skill-gap ordering, recommendation ordering, and skill/engineer update/delete behavior.
- Prefer testing service/domain behavior through `MatrixService` and repositories over testing NiceGUI rendering directly.
- Use the single-test command above for focused iteration, e.g. `python -m pytest tests\test_matrix_service.py::test_training_recommendations_prioritize_largest_gaps`.

## Key conventions

- Keep UI event handlers thin: validate through domain models, call `MatrixService`, and let repositories handle SQL.
- Do not write to `app.storage.browser` from click handlers; use `app.storage.user` for persisted preferences after the response has been built.
- The shared blue score buttons are used for heatmap cells, engineer profile competency levels, and skill target levels. Normal click increases with wraparound; Shift-click decreases with wraparound.
- Heatmap skill headers have tooltips for category/description; engineer labels have tooltips for team/role.
- Score button colors are controlled by `HEATMAP_LEVEL_COLORS` and `skill_score_button_style()` in `main.py`; keep the darkest color for low scores and lightest blue for high scores.
- Use `events.GenericEventArguments` with `args=["shiftKey"]` when implementing click/Shift-click behavior in NiceGUI controls.
- Keep local/generated artifacts out of commits: `.nicegui\`, `.pytest_cache\`, `__pycache__\`, `*.egg-info\`, and local SQLite data are development artifacts.
- Add or update pytest coverage when changing validation, repository behavior, service calculations, or recommendation ordering.

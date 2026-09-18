# Current Repository Architecture

## Core Directories

- `app/`
  - `bridge/`: Connects UI layer to Python core (QWebChannel/PySide6 bridges).
  - `ui/`: Frontend assets and HTML.
  - `windows/`: GUI Window implementations.
  - `main.py`: Entrypoint for the application.

- `core/`
  - `agents/`: Contains agent abstractions (`default_agents.py`, `prompt_agents.py`, `registry.py`, `runtime.py`). This is the current hub for dynamic agent routing.
  - `providers/`: Inference provider wrappers (`base.py`, `local.py`, `openai_compat.py`, `anthropic.py`, `google.py`, `registry.py`).
  - `tutor/` & `tutor_engine.py`: Specialized components for tutoring.
  - `courses/`, `curriculum/`: Structured learning content.
  - `orchestrator.py`: The central orchestrator routing tasks.
  - `knowledge_graph.py`, `session.py`, `db.py`: Persistence and memory layers.

- `training/`
  - Scripts and tools for local fine-tuning/dataset generation (e.g., `generate_data.py`, `colab_notebook.py`).

- `tests/`
  - Extensive `pytest` test suite covering curriculum resilience, UI bridges, concurrency, dataset validation, etc.

- `docs/`
  - Various project documentation and plans.

- `scripts/`
  - Helper scripts.

## Important Key Concepts Identified

- **Agents & Orchestrator**: The application is structured around a central `orchestrator.py` that dispatches to various specialized agents stored in `core/agents/`.
- **Local Providers**: LLM capabilities are exposed via `core/providers/local.py` (likely llama-cpp-python).
- **Frontend Bridge**: Web-based frontend communicating through `app/bridge/facade.py` or similar to the Qt runtime.

*(Note: The above components will undergo significant restructuring during the transition to a rigid two-mode architecture without a central specialized-agent orchestrator.)*

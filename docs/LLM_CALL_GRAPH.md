# LLM Call Graph

| Component | Function | Provider | Blocking | Streaming | User visible | Mode |
|---|---|---|---|---|---|---|
| `core/providers/local.py` | `chat` | Local | Yes | No | Sometimes | `Global` |
| `core/providers/local.py` | `chat_stream` | Local | No | Yes | Yes | `Global` |
| `core/providers/anthropic.py` | `chat` | Anthropic | Yes | No | Sometimes | `Global` |
| `core/providers/anthropic.py` | `stream` | Anthropic | No | Yes | Yes | `Global` |
| `core/providers/google.py` | `chat` | Google | Yes | No | Sometimes | `Global` |
| `core/providers/google.py` | `stream` | Google | No | Yes | Yes | `Global` |
| `core/providers/openai_compat.py`| `chat` | OpenAI | Yes | No | Sometimes | `Global` |
| `core/providers/openai_compat.py`| `stream` | OpenAI | No | Yes | Yes | `Global` |
| `core/orchestrator.py` | `_evaluate_tutor_response` | Local | Yes | No | No (Background) | `Tutor` |
| `core/orchestrator.py` | `chat` | Any | Yes | No | Yes | `Global Routing` |
| `core/orchestrator.py` | `stream` | Any | No | Yes | Yes | `Global Routing` |
| `core/agents/runtime.py` | `process` | Any | Yes | No | Yes | `Legacy Agents` |
| `core/agents/default_agents.py`| `Tutor.process` | Local | No | Yes | Yes | `Tutor` |
| `core/agents/prompt_agents.py` | `process` | Local | No | Yes | Yes | `Legacy Agents` |
| `app/bridge/facade.py` | `orch.stream()` | Local | No | Yes | Yes | `Global Routing` |
| `scripts/benchmark_performance.py`| `LocalProvider.stream()` | Local | Yes | Yes | No | `Benchmark` |
| `training/build_notebook.py` | `model.generate()` | Transformers | Yes | No | No | `Training` |

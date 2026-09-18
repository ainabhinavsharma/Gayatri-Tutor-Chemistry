# Inference Architecture

## Central Inference Service
The InferenceService (implemented in `core/providers/local.py`) handles all LLM generation requests for local models.

## Concurrency
We maintain a strict `_infer_lock` around `llama_cpp.Llama.create_completion` to prevent memory corruption, as `llama.cpp` does not natively support concurrent generations on a single context.
Secondary background evaluations (like Tutor mastery assessments) queue up behind foreground UI requests using this lock.

## Cancellation
Cancellation is implemented using a shared atomic flag.
When the UI triggers `cancel_generation()`, the Bridge sets a `_cancel_flag`.
During the streaming generation loop (`yield from stream_obj`), the provider checks the flag on every chunk.
If the flag is set, it terminates the generator and raises an exception or gracefully stops, yielding the lock back.


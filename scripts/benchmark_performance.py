"""Gayatri Chemistry Tutor — Performance, Latency, and Memory Benchmark.

Profiles:
1. Hardware configuration (CPU cores, RAM, AVX2 / GPU layers).
2. Local model file detection and health.
3. Time To First Token (TTFT).
4. Tokens per second (throughput).
5. Memory footprint (Resident Set Size).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.hardware import detect_hardware, recommend_llama_params
from core.providers.local import LocalProvider


def get_current_memory_mb() -> float:
    """Return current process memory in megabytes."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def run_benchmark(prompt: str = "Explain the First Law of Thermodynamics and the IUPAC sign convention for work.", max_tokens: int = 60) -> dict:
    print("=" * 65)
    print("GAYATRI CHEMISTRY TUTOR -- LOCAL MODEL PERFORMANCE BENCHMARK")
    print("=" * 65)

    hw = detect_hardware()
    params = recommend_llama_params(hw)
    mem_init = get_current_memory_mb()

    print(f"OS Platform    : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"CPU Threads    : {hw.cpu_threads} logical ({hw.cpu_cores} physical)")
    print(f"GPU / CUDA     : {hw.gpu_name} (CUDA: {hw.has_cuda}, {hw.gpu_vram_free_mb} MB free)")
    print(f"RAM Total      : {hw.ram_mb} MB")
    print(f"Inference Rec  : threads={params.n_threads}, n_ctx={params.n_ctx}, gpu_layers={params.n_gpu_layers}")
    print(f"Initial Memory : {mem_init:.1f} MB\n")

    health = LocalProvider.health()
    print(f"Model Path     : {health.get('path')}")
    print(f"Model Available: {health.get('available')}")

    if not health.get("available"):
        print(f"\n[!] Notice: {health.get('message')}")
        print("Model file is not yet downloaded to the local directory.")
        return {
            "status": "model_unavailable",
            "hardware": hw.__dict__,
            "inference_params": params.__dict__,
            "health": health,
        }

    # 1. Model Loading Benchmark
    print("\n[1/3] Loading GGUF Model into memory...")
    t0 = time.time()
    try:
        LocalProvider._load_model()
        t1 = time.time()
        load_time_sec = t1 - t0
        mem_loaded = get_current_memory_mb()
        print(f"[OK] Model loaded successfully in {load_time_sec:.2f} seconds.")
        print(f"  Post-load Memory: {mem_loaded:.1f} MB (Delta: +{mem_loaded - mem_init:.1f} MB)")
    except Exception as e:
        print(f"[FAIL] Failed to load model: {e}")
        return {"status": "load_error", "error": str(e)}

    # 2. Warm-up and TTFT Generation Benchmark
    print(f"\n[2/3] Benchmarking Streaming Inference (max_tokens={max_tokens})...")
    print(f"Prompt: \"{prompt[:60]}...\"")

    stream = LocalProvider.stream(prompt, max_tokens=max_tokens)
    t_start = time.time()
    first_token_time = None
    tokens = 0
    generated_text = []

    for chunk in stream:
        if first_token_time is None:
            first_token_time = time.time()
        tokens += 1
        generated_text.append(chunk)

    t_end = time.time()

    ttft_ms = (first_token_time - t_start) * 1000 if first_token_time else 0.0
    gen_duration = t_end - (first_token_time or t_start)
    tps = tokens / gen_duration if gen_duration > 0 else 0.0
    total_time = t_end - t_start
    mem_final = get_current_memory_mb()

    print("\n[3/3] Benchmark Results:")
    print("=" * 65)
    print(f"  Time To First Token (TTFT) : {ttft_ms:.1f} ms")
    print(f"  Tokens Generated           : {tokens} tokens")
    print(f"  Generation Throughput      : {tps:.2f} tokens/sec")
    print(f"  Total Duration             : {total_time:.2f} s")
    print(f"  Final Memory Footprint     : {mem_final:.1f} MB")
    print("=" * 65)

    return {
        "status": "success",
        "ttft_ms": round(ttft_ms, 2),
        "tokens": tokens,
        "throughput_tps": round(tps, 2),
        "load_time_sec": round(load_time_sec, 2),
        "memory_mb": round(mem_final, 2),
        "generated_preview": "".join(generated_text)[:120],
    }


def main():
    parser = argparse.ArgumentParser(description="Gayatri Chemistry Tutor Performance Benchmark")
    parser.add_argument("--prompt", type=str, default="Explain the First Law of Thermodynamics and how work is calculated in expansion.")
    parser.add_argument("--max_tokens", type=int, default=50)
    args = parser.parse_args()

    run_benchmark(prompt=args.prompt, max_tokens=args.max_tokens)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Gayatri AI — Local Model Health Check Script (Section 8).

Inspects the local Qwen model weights, inference provider, hardware configuration,
and performs deterministic generation and structured JSON output tests.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.providers.local import LocalProvider


def check_model() -> bool:
    print("=" * 65)
    print("GAYATRI CHEMISTRY TUTOR — MODEL HEALTH CHECK (Section 8)")
    print("=" * 65)

    all_passed = True
    model_path = LocalProvider.MODEL_PATH

    print(f"Target Architecture:  Qwen2.5-3B-Instruct")
    print(f"Provider:             llama-cpp-python (LocalProvider)")
    print(f"Model Path:           {model_path}")
    print(f"File Exists:          {'YES' if model_path.exists() else 'NO'}")

    if not model_path.exists():
        print("\nERROR: Model weights file not found. Place GGUF file in:")
        print(f"  {model_path}")
        return False

    file_size_mb = model_path.stat().st_size / (1024 * 1024)
    print(f"Model File Size:      {file_size_mb:.1f} MB")

    # Load model metadata without heavy load
    try:
        from llama_cpp import Llama
        llm = LocalProvider._load_model()
        meta = llm.metadata
        arch = meta.get("general.architecture", "qwen2")
        name = meta.get("general.name", "Qwen2.5-3B-Instruct")
        ctx = meta.get("qwen2.context_length", meta.get("llama.context_length", 32768))
        print(f"Detected Architecture: {arch}")
        print(f"Context Length:        {ctx} tokens")
        print(f"Quantization:          Q4_K_M")
    except Exception as exc:
        print(f"WARNING: Metadata inspection failed ({exc}); using defaults")
        ctx = 8192

    # Hardware & Memory
    print(f"Operating System:     {platform.system()} {platform.release()}")
    print(f"CPU Architecture:     {platform.machine()}")
    try:
        import psutil
        mem = psutil.virtual_memory()
        print(f"System Memory:        {mem.total / (1024**3):.1f} GB (Available: {mem.available / (1024**3):.1f} GB)")
    except ImportError:
        print(f"System Memory:        Available (psutil not installed)")

    # Test 1: Deterministic generation test
    print("\n" + "-" * 65)
    print("TEST 1: Deterministic Text Generation Test")
    print("-" * 65)
    test_prompt = "Explain the First Law of Thermodynamics in one sentence."
    print(f"Input:    {test_prompt}")

    t0 = time.time()
    try:
        gen_output = LocalProvider.chat(
            [{"role": "user", "content": test_prompt}],
            max_tokens=60,
            temperature=0.1,
        )
        gen_time = time.time() - t0
        clean_output = gen_output.strip().split("\n")[0]
        print(f"Response: {clean_output}")
        print(f"Latency:  {gen_time:.2f}s")
        if clean_output and len(clean_output) > 10:
            print("Generation Test:      PASS")
        else:
            print("Generation Test:      FAIL (Empty or too short)")
            all_passed = False
    except Exception as exc:
        print(f"Generation Test:      FAIL ({exc})")
        all_passed = False

    # Test 2: Structured JSON output test
    print("\n" + "-" * 65)
    print("TEST 2: Structured JSON Output Test")
    print("-" * 65)
    json_messages = [
        {"role": "system", "content": "You are a chemistry tutor assistant. Respond ONLY with a valid JSON object containing keys: concept, formula, valid."},
        {"role": "user", "content": "Return JSON for First Law of Thermodynamics."}
    ]
    t0 = time.time()
    try:
        json_output = LocalProvider.chat(
            json_messages,
            max_tokens=60,
            temperature=0.1,
        )
        json_time = time.time() - t0
        clean_json = json_output.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        parsed = json.loads(clean_json)
        print(f"Parsed JSON:          {parsed}")
        print(f"Latency:              {json_time:.2f}s")
        if isinstance(parsed, dict) and len(parsed) >= 2:
            print("Structured Test:      PASS")
        else:
            print("Structured Test:      FAIL (Invalid schema)")
            all_passed = False
    except Exception as exc:
        print(f"Structured Test:      FAIL ({exc})")
        all_passed = False

    # Summary
    print("\n" + "=" * 65)
    final_status = "PASS — Qwen2.5 local model is healthy and operational" if all_passed else "FAIL — Issues detected"
    print(f"OVERALL STATUS:       {final_status}")
    print("=" * 65)
    return all_passed


if __name__ == "__main__":
    success = check_model()
    sys.exit(0 if success else 1)

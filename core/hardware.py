"""Gayatri AI — Dynamic Hardware Detection.

Detects GPU VRAM, CPU cores, and recommends llama.cpp parameters.

Simple, safe approach: detect VRAM → set n_gpu_layers and n_threads.
Does NOT implement dynamic CPU/GPU/NPU switching (patented by CN121387494A).
Does NOT implement SoC-level power management (patented by US20250068838A1).
Just static parameter selection based on what the hardware can handle.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from dataclasses import dataclass

logger = logging.getLogger("gayatri.hardware")


@dataclass
class HardwareProfile:
    """Detected hardware capabilities."""
    gpu_name: str = "unknown"
    gpu_vram_mb: int = 0
    gpu_vram_free_mb: int = 0
    cpu_cores: int = 4
    cpu_threads: int = 4
    has_cuda: bool = False
    os: str = "unknown"
    ram_mb: int = 0


@dataclass
class LlamaParams:
    """Recommended llama.cpp parameters for this hardware."""
    n_gpu_layers: int = 0  # -1 = all layers
    n_ctx: int = 2048
    n_threads: int = 4
    use_mmap: bool = True
    use_mlock: bool = False


def detect_hardware() -> HardwareProfile:
    """Detect the current system's hardware capabilities.

    Returns HardwareProfile with VRAM, CPU, and GPU info.
    """
    profile = HardwareProfile()
    profile.os = platform.system()
    profile.cpu_cores = _get_cpu_cores()
    profile.cpu_threads = _get_cpu_threads()

    # Try to detect GPU via nvidia-smi
    gpu_info = _get_nvidia_gpu_info()
    if gpu_info:
        profile.gpu_name = gpu_info["name"]
        profile.gpu_vram_mb = gpu_info["vram_mb"]
        profile.gpu_vram_free_mb = gpu_info["vram_free_mb"]
        profile.has_cuda = True
    else:
        profile.gpu_name = "CPU only"
        profile.gpu_vram_mb = 0
        profile.gpu_vram_free_mb = 0
        profile.has_cuda = False

    # Detect RAM
    profile.ram_mb = _get_ram_mb()

    logger.info(
        f"Hardware: GPU={profile.gpu_name} ({profile.gpu_vram_free_mb}MB free / {profile.gpu_vram_mb}MB VRAM), "
        f"CPU={profile.cpu_cores}c/{profile.cpu_threads}t, RAM={profile.ram_mb}MB"
    )
    return profile


def recommend_llama_params(profile: HardwareProfile, model_size_mb: int = 1600) -> LlamaParams:
    """Recommend llama.cpp parameters based on detected hardware.

    Args:
        profile: Detected hardware profile
        model_size_mb: Approximate size of the GGUF model file

    Returns:
        LlamaParams with n_gpu_layers, n_ctx, n_threads, etc.
    """
    params = LlamaParams()

    # The 3B Q4_K_M model uses ~1.9GB, so 8GB machines have ample headroom for 4096 tokens
    if profile.ram_mb > 16384:  # 16GB+
        params.n_ctx = 8192
    elif profile.ram_mb > 4096:  # 4GB+
        params.n_ctx = 4096
    else:
        params.n_ctx = 2048

    # GPU layers: all if FREE VRAM can fit the model, partial otherwise
    if profile.has_cuda and profile.gpu_vram_free_mb > 0:
        if profile.gpu_vram_free_mb >= model_size_mb * 1.5:
            # Free VRAM comfortably fits the model with headroom
            params.n_gpu_layers = -1  # all layers
            logger.info(f"GPU layers: all (Free VRAM {profile.gpu_vram_free_mb}MB >= {model_size_mb}MB model)")
        elif profile.gpu_vram_free_mb >= model_size_mb:
            # Free VRAM fits the model exactly
            params.n_gpu_layers = -1
            logger.info(f"GPU layers: all (tight fit, {profile.gpu_vram_free_mb}MB free VRAM)")
        elif profile.gpu_vram_free_mb >= model_size_mb / 2:
            # Partial offload — estimate layers (roughly 1GB per ~5 layers for 2B model)
            estimated_layers = max(10, int((profile.gpu_vram_free_mb / model_size_mb) * 35))
            params.n_gpu_layers = estimated_layers
            logger.info(f"GPU layers: {estimated_layers} (partial, {profile.gpu_vram_free_mb}MB free VRAM)")
        else:
            # Very little Free VRAM — CPU only
            params.n_gpu_layers = 0
            logger.info(f"GPU layers: 0 (insufficient free VRAM {profile.gpu_vram_free_mb}MB)")
    else:
        params.n_gpu_layers = 0
        logger.info("GPU layers: 0 (no CUDA)")

    # Threads: use physical cores, cap at 8 for threading overhead
    params.n_threads = min(profile.cpu_cores, 8)

    # mmap: use only if we have enough RAM
    params.use_mmap = profile.ram_mb > model_size_mb * 2

    return params


def get_llama_params(profile: HardwareProfile | None = None) -> LlamaParams:
    """Get recommended llama.cpp params, detecting hardware if needed."""
    if profile is None:
        profile = detect_hardware()
    from pathlib import Path
    from core.config import get_active_model_path

    model_path = get_active_model_path()
    model_size_mb = 1600  # default
    if model_path.exists():
        model_size_mb = int(model_path.stat().st_size / (1024 * 1024))
    return recommend_llama_params(profile, model_size_mb)



# ── Hardware detection helpers ──────────────────────────────────────────

def _get_cpu_cores() -> int:
    try:
        import os
        return os.cpu_count() or 4
    except Exception:
        return 4


def _get_cpu_threads() -> int:
    try:
        import os
        return os.cpu_count() or 4
    except Exception:
        return 4


def _get_nvidia_gpu_info() -> dict | None:
    """Get GPU info via nvidia-smi. Returns None if no NVIDIA GPU."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None

        lines = result.stdout.strip().split("\n")
        if not lines or not lines[0].strip():
            return None

        # First GPU (primary)
        parts = lines[0].split(",")
        name = parts[0].strip()
        vram_mb = int(parts[1].strip()) if len(parts) > 1 else 0
        vram_free_mb = int(parts[2].strip()) if len(parts) > 2 else vram_mb
        return {"name": name, "vram_mb": vram_mb, "vram_free_mb": vram_free_mb}
    except Exception:
        return None


def _get_ram_mb() -> int:
    """Detect total system RAM in MB."""
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) // 1024
        elif platform.system() == "Windows":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            return int(mem.ullTotalPhys // (1024 * 1024))
        elif platform.system() == "Darwin":  # macOS
            result = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
            return int(result.stdout.strip()) // (1024 * 1024)
    except Exception:
        pass
    return 8192  # Default to 8GB if detection fails

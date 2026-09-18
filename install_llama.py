"""Gayatri AI — Install helper for llama-cpp-python.

This script is called from setup.bat as a last resort when no pre-built wheel
is available. It finds the VS compiler, sets up the environment, and compiles
llama-cpp-python. Output is streamed live to the console.
"""
import os
import sys
import subprocess
import glob
import shutil


def find_vcvars64():
    """Search standard locations for vcvars64.bat."""
    search_paths = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Microsoft", "VisualStudio", "17_BuildTools",
                     "VC", "Auxiliary", "Build", "vcvars64.bat"),
        r"C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
        os.path.join(os.environ.get("TEMP", ""), "VSBuildTools",
                     "VC", "Auxiliary", "Build", "vcvars64.bat"),
    ]
    # Also search common install roots
    for root in [r"C:\Program Files\Microsoft Visual Studio", r"C:\Program Files (x86)\Microsoft Visual Studio"]:
        search_paths.extend(glob.glob(
            os.path.join(root, "*", "VC", "Auxiliary", "Build", "vcvars64.bat")
        ))

    for p in search_paths:
        if os.path.isfile(p):
            return p
    return None


def setup_msvc_env(vcvars_path):
    """Run vcvars64.bat and capture the environment it sets up."""
    # Run vcvars64, then dump all env vars
    # We use a trick: cmd /c calls vcvars64, then runs set to dump env
    cmd = f'call "{vcvars_path}" >nul 2>&1 && set'
    result = subprocess.run(
        ["cmd", "/c", cmd],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"[ERROR] vcvars64 failed: {result.stderr}", file=sys.stderr)
        return None

    # Parse the env dump into a dict
    env = os.environ.copy()
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            env[key] = value
    return env


def main():
    print("[STEP] Searching for C++ compiler (vcvars64.bat)...")
    vcvars = find_vcvars64()
    if not vcvars:
        print("[ERROR] vcvars64.bat not found.", file=sys.stderr)
        print("  Install Visual Studio Build Tools:", file=sys.stderr)
        print("  https://visualstudio.microsoft.com/downloads/", file=sys.stderr)
        print("  Select 'Desktop development with C++' workload.", file=sys.stderr)
        sys.exit(1)

    print(f"[OK] Found compiler at: {vcvars}")
    print("[STEP] Setting up MSVC environment...")
    env = setup_msvc_env(vcvars)
    if env is None:
        sys.exit(1)

    # Ensure PATH includes the VS tools first
    print(f"[OK] Compiler environment ready")
    print(f"     VC bin: {env.get('VCToolsInstallDir', 'unknown')}")
    print()
    print("[STEP] Compiling llama-cpp-python (3-5 minutes, please wait)...")
    print()

    pip = os.path.join(".venv", "Scripts", "pip.exe")
    if not os.path.isfile(pip):
        print(f"[ERROR] pip not found at {pip}. Run setup.bat first.", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [pip, "install", "llama-cpp-python"],
        env=env,
        cwd=os.getcwd(),
    )

    print()
    if result.returncode != 0:
        print(f"[ERROR] Compilation failed (exit code {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)

    print("[OK] llama-cpp-python installed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()

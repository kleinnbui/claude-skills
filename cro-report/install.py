"""Cross-platform installer for /cro-report skill.

Usage: python3 install.py  (Mac/Linux) or  python install.py  (Windows)

Auto-reexecs with newest available Python if current is <3.10.
Creates .venv, installs deps. No bash dependency.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

SKILL_DIR = Path(__file__).parent
VENV_DIR = SKILL_DIR / ".venv"
REQ = SKILL_DIR / "requirements.txt"
ACCOUNTS = SKILL_DIR / "accounts.json"

IS_WIN = sys.platform == "win32"
BIN_DIR = "Scripts" if IS_WIN else "bin"
PIP_NAME = "pip.exe" if IS_WIN else "pip"

PYTHON_CANDIDATES = [
    "python3.14", "python3.13", "python3.12", "python3.11", "python3.10",
    "python3", "python",
]


def _find_newer_python() -> str | None:
    """Find first python on PATH with version >= 3.10 and != current."""
    current_exe = os.path.realpath(sys.executable)
    for name in PYTHON_CANDIDATES:
        path = shutil.which(name)
        if not path or os.path.realpath(path) == current_exe:
            continue
        try:
            out = subprocess.check_output(
                [path, "-c", "import sys; print(sys.version_info[:2])"],
                text=True, timeout=5,
            ).strip()
            major, minor = eval(out)
            if (major, minor) >= (3, 10):
                return path
        except Exception:
            continue
    return None


def main() -> int:
    print("=== /cro-report — Installer ===\n")

    if sys.version_info < (3, 10):
        newer = _find_newer_python()
        if newer:
            print(f"Re-exec với Python newer: {newer}")
            os.execv(newer, [newer, __file__])
        print(f"ERROR: Python 3.10+ required (current: {sys.version.split()[0]})",
              file=sys.stderr)
        print("Cài Python 3.10+ từ python.org hoặc brew install python@3.12",
              file=sys.stderr)
        return 1
    print(f"Using: Python {sys.version.split()[0]} ({sys.platform})")

    for sub in ("scripts", "templates", "reports", "credentials"):
        (SKILL_DIR / sub).mkdir(exist_ok=True)

    if not VENV_DIR.exists():
        print("Creating .venv ...")
        # with_pip=True can silently skip pip on systems missing the ensurepip
        # module (Ubuntu without python3-venv apt package). We bootstrap pip
        # explicitly below if it's missing.
        try:
            venv.create(VENV_DIR, with_pip=True)
        except Exception as e:
            print(f"venv with_pip failed ({e}); creating venv without pip", file=sys.stderr)
            venv.create(VENV_DIR, with_pip=False)
    else:
        print(".venv already exists, skipping create")

    venv_py = VENV_DIR / BIN_DIR / ("python.exe" if IS_WIN else "python")
    if not venv_py.exists():
        print(f"ERROR: venv python not found at {venv_py}", file=sys.stderr)
        return 1

    pip = VENV_DIR / BIN_DIR / PIP_NAME
    if not pip.exists():
        print("pip missing — bootstrapping via get-pip.py ...")
        import urllib.request
        get_pip = SKILL_DIR / "get-pip.py"
        urllib.request.urlretrieve(
            "https://bootstrap.pypa.io/get-pip.py", str(get_pip))
        subprocess.run([str(venv_py), str(get_pip), "--quiet"], check=True)
        get_pip.unlink(missing_ok=True)

    print("Upgrading pip ...")
    subprocess.run([str(venv_py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=True)

    print("Installing dependencies (~30s first run) ...")
    subprocess.run(
        [str(venv_py), "-m", "pip", "install", "--quiet", "-r", str(REQ)],
        check=True,
    )

    if not ACCOUNTS.exists():
        ACCOUNTS.write_text('{"default":null,"profiles":{}}\n')

    print("\n=== Installed ===")
    print("Type /cro-report in Claude Code to start.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

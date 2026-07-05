"""Pre-flight check. Run before making any change: `python init.py`.

Verifies the expected folder/file structure exists, required markdown files are
non-empty, and the test suite runs. Exits non-zero on any failure — stop and ask
for help rather than continuing past a failure here.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED_PATHS = [
    "CLAUDE.md",
    "memory.md",
    "requirements.txt",
    "roles/planner.md",
    "roles/builder.md",
    "roles/reviewer.md",
    "tools/data_fetcher.py",
    "tools/strategy_loader.py",
    "tools/backtest_engine.py",
    "tools/metrics.py",
    "tools/report_generator.py",
    "app.py",
    "strategies/example_sma_crossover.py",
    "tests/test_metrics.py",
    "tests/test_smoke.py",
]

REQUIRED_NONEMPTY_MD = [
    "CLAUDE.md",
    "memory.md",
    "roles/planner.md",
    "roles/builder.md",
    "roles/reviewer.md",
]


def check_structure() -> bool:
    missing = [p for p in REQUIRED_PATHS if not (ROOT / p).exists()]
    if missing:
        print("[FAIL] Missing files:")
        for m in missing:
            print(f"  - {m}")
        return False
    print("[OK] Folder/file structure present.")
    return True


def check_nonempty_md() -> bool:
    empty = [p for p in REQUIRED_NONEMPTY_MD if (ROOT / p).stat().st_size == 0]
    if empty:
        print("[FAIL] Required file(s) are empty:")
        for e in empty:
            print(f"  - {e}")
        return False
    print("[OK] Required markdown files are non-empty.")
    return True


def run_tests() -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.returncode == 5:
        print("[WARN] No tests collected yet.")
        return True
    if result.returncode != 0:
        print("[FAIL] Tests failed.")
        print(result.stderr)
        return False
    print("[OK] Tests passed.")
    return True


def main() -> None:
    checks = [check_structure(), check_nonempty_md(), run_tests()]
    if not all(checks):
        print("\ninit.py FAILED. Stop and fix the issues above before proceeding.")
        sys.exit(1)
    print("\ninit.py OK. Safe to proceed.")


if __name__ == "__main__":
    main()

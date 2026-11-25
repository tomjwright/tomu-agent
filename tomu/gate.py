"""Release gate: run `uv run tomu-gate` after changing the prompt, the model or a tool.

It's a door with two locks, checked in order:
    1. tests   every test in tests/ must pass. They don't call the model, so they cost nothing.
    2. evals   the model must pass at least PASS_MARK of the cases in evals/cases.json.
If a test fails, the evals are skipped, so a broken change never spends tokens.
OPEN means the change is safe to release; CLOSED means fix something first.
Every verdict is saved in tomu.db, so the page can list past runs.
"""

import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from tomu import evals
from tomu.events import Emit, Event
from tomu.memory import Memory

REPO = Path(__file__).parent.parent
PASS_MARK = 0.8  # with 8 cases, 7 must pass


def run_gate(emit: Emit, memory: Memory | None = None) -> bool:
    """Run the tests, then the evals, then emit and save the verdict. True means open."""
    memory = memory or Memory(os.getenv("TOMU_DB", "tomu.db"))
    started = time.time()

    tests_passed, tests_failed = run_tests()
    emit({"type": "gate_tests", "passed": tests_passed, "failed": tests_failed})

    if tests_failed or not tests_passed:
        is_open, evals_passed, evals_total = False, None, None
        reason = f"{tests_failed} test(s) failed, so the evals didn't run"
    else:
        cases = json.loads(evals.CASES_FILE.read_text())
        evals_passed, evals_total = evals.run_evals(emit, cases), len(cases)
        needed = math.ceil(PASS_MARK * evals_total)
        is_open = evals_total > 0 and evals_passed >= needed  # no cases means nothing was checked
        reason = f"{evals_passed}/{evals_total} evals passed, {needed} needed"

    result = {
        "type": "gate_result",
        "open": is_open,
        "reason": reason,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "evals_passed": evals_passed,
        "evals_total": evals_total,
        "duration_ms": int((time.time() - started) * 1000),
    }
    emit(result)
    memory.save_gate_run(result)
    return is_open


def run_tests() -> tuple[int, int]:
    """Run pytest and read its summary line, e.g. "48 passed, 1 failed, 1 skipped in 2.1s"."""
    process = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests"], cwd=REPO, capture_output=True, text=True
    )
    passed = sum(int(n) for n in re.findall(r"(\d+) passed", process.stdout))
    failed = sum(int(n) for n in re.findall(r"(\d+) (?:failed|errors?)\b", process.stdout))
    if process.returncode and not failed:
        failed = 1  # pytest failed in a way its summary doesn't count, e.g. it was interrupted
    return passed, failed


def show(event: Event) -> None:
    if event["type"] == "gate_tests":
        print(f"Tests: {event['passed']} passed, {event['failed']} failed\n")
    evals.show(event)
    if event["type"] == "gate_result":
        verdict = "OPEN, safe to release" if event["open"] else "CLOSED, fix this first"
        print(f"\nGATE {verdict}: {event['reason']}")


def main() -> None:
    load_dotenv()
    sys.exit(0 if run_gate(show) else 1)


if __name__ == "__main__":
    main()

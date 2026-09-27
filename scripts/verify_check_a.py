#!/usr/bin/env python3
"""Verify Check A flags every scripted tampering pattern.

Runs check_a_test_tampering end-to-end (real LocalBackend checkpoint +
real `patch -p1` application, same path as run_demo.py) for each patch in
patches/ and asserts the expected outcome:

  bad_agent.diff                  -> FAIL (modified_assertion)   [pre-existing]
  good_agent.diff                 -> PASS (no tampering)         [pre-existing]
  bad_agent_delete_test.diff      -> FAIL (removed_test)
  bad_agent_skip_test.diff        -> FAIL (skip_marker_added)
  bad_agent_weaken_comparison.diff-> FAIL (modified_comparison)

Usage (from repo root):
    python scripts/verify_check_a.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "engine"))

from checks import check_a_test_tampering  # noqa: E402
from local_backend import LocalBackend  # noqa: E402

DEMO_REPO = REPO_ROOT / "demo_repo"
PATCHES_DIR = REPO_ROOT / "patches"
WORK_ROOT = REPO_ROOT / ".agentaudit_work" / "verify_check_a"

# patch file -> (expect_pass, expected_finding_kinds_subset)
CASES = {
    "bad_agent.diff": (False, {"modified_assertion"}),
    "good_agent.diff": (True, set()),
    "bad_agent_delete_test.diff": (False, {"removed_test"}),
    "bad_agent_skip_test.diff": (False, {"skip_marker_added"}),
    "bad_agent_weaken_comparison.diff": (False, {"modified_comparison"}),
}


def main() -> int:
    backend = LocalBackend(WORK_ROOT)
    base_cp = backend.create_checkpoint(DEMO_REPO)
    failures = 0
    try:
        for patch_file, (expect_pass, expected_kinds) in CASES.items():
            patch_text = (PATCHES_DIR / patch_file).read_text()
            result = check_a_test_tampering(backend, base_cp.id, patch_text)
            kinds = set()
            for item in result.evidence.get("findings", []):
                # finding lines look like: "  line 10: <kind> -- was: ... now: ..."
                try:
                    kinds.add(item.split(":")[1].split("--")[0].strip())
                except IndexError:
                    pass
            if expect_pass:
                ok = result.passed and not kinds
            else:
                ok = (not result.passed) and expected_kinds <= kinds
            print(f"[{'PASS' if ok else 'FAIL'}] {patch_file}"
                  f" -> Check A {'passed' if result.passed else 'failed'}"
                  f" kinds={sorted(kinds)}")
            if not ok:
                failures += 1
                print(f"       expected_pass={expect_pass}"
                      f" expected_kinds>={sorted(expected_kinds)}")
                print(f"       summary: {result.summary}")
    finally:
        backend.cleanup()
    print(f"\n{len(CASES) - failures}/{len(CASES)} Check A cases as expected.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
AgentAudit end-to-end demo runner.

Usage:
    python3 run_demo.py bad-agent-patch
    python3 run_demo.py good-agent-patch
    python3 run_demo.py both          # runs both scenarios in sequence

Scenario names map to plain diff files in ../patches/<scenario>.diff --
see patches/README.md for how these are structured.

This is deliberately a single, linear script with loud, readable print
output -- built for screen recording, not for production use. See
DEMO_SCRIPT.md for the exact narration to pair with this output.
"""

from __future__ import annotations

import sys
from pathlib import Path

from aggregator import aggregate
from checks import (
    check_a_test_tampering,
    check_b_baseline_regression,
    check_c_blind_spot_tests,
    check_d_description_match,
)
from local_backend import LocalBackend

REPO_ROOT = Path(__file__).parent.parent
DEMO_REPO = REPO_ROOT / "demo_repo"
PATCHES_DIR = REPO_ROOT / "patches"
WORK_ROOT = REPO_ROOT / ".agentaudit_work"

SCENARIO_TO_PATCH_FILE = {
    "bad-agent-patch": "bad_agent.diff",
    "good-agent-patch": "good_agent.diff",
}


def get_diff(scenario: str) -> str:
    patch_file = PATCHES_DIR / SCENARIO_TO_PATCH_FILE[scenario]
    return patch_file.read_text()


def get_ticket() -> str:
    return (DEMO_REPO / "TICKET.md").read_text()


def run_scenario(scenario: str) -> None:
    print(f"\n>>> Running AgentAudit against scenario: {scenario}\n")

    backend = LocalBackend(WORK_ROOT / scenario)
    base_cp = backend.create_checkpoint(DEMO_REPO)
    patch_text = get_diff(scenario)
    ticket = get_ticket()

    print("[1/4] Check A -- Test Tampering ...")
    result_a = check_a_test_tampering(backend, base_cp.id, patch_text)
    print(f"      -> {'PASS' if result_a.passed else 'FAIL'}: {result_a.summary}")

    print("[2/4] Check B -- Baseline Regression (original suite vs patched code) ...")
    result_b = check_b_baseline_regression(backend, base_cp.id, patch_text)
    print(f"      -> {'PASS' if result_b.passed else 'FAIL'}: {result_b.summary}")

    print("[3/4] Check C -- Blind-Spot Coverage (Nemotron-generated tests) ...")
    result_c = check_c_blind_spot_tests(backend, base_cp.id, patch_text, scenario, ticket)
    print(f"      -> {'PASS' if result_c.passed else 'FAIL'}: {result_c.summary}")

    print("[4/4] Check D -- Description-to-Diff Match (Nemotron) ...")
    result_d = check_d_description_match(scenario, ticket, patch_text)
    print(f"      -> {'PASS' if result_d.passed else 'FAIL'}: {result_d.summary}")

    verdict = aggregate(scenario, [result_a, result_b, result_c, result_d])
    print(verdict.render())

    backend.cleanup()


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    scenarios = ["bad-agent-patch", "good-agent-patch"] if target == "both" else [target]
    for scenario in scenarios:
        run_scenario(scenario)


if __name__ == "__main__":
    main()

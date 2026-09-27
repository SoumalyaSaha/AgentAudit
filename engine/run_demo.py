#!/usr/bin/env python3
"""
AgentAudit end-to-end demo runner.

Usage:
    python3 run_demo.py bad-agent-patch
    python3 run_demo.py good-agent-patch
    python3 run_demo.py both          # runs both scenarios in sequence
    python3 run_demo.py both --backend sandbox   # same, on real Nebius
                                                 # Sandboxes (needs
                                                 # NEBIUS_API_KEY +
                                                 # NEBIUS_PROJECT_ID)
    python3 run_demo.py both --live              # same, but Checks C and D
                                                 # make real Nemotron calls
                                                 # instead of replaying
                                                 # fixtures (needs
                                                 # NEBIUS_API_KEY; costs
                                                 # credits -- only pass
                                                 # this flag explicitly)

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
    "bad-agent-delete-test": "bad_agent_delete_test.diff",
    "bad-agent-skip-test": "bad_agent_skip_test.diff",
    "bad-agent-weaken-comparison": "bad_agent_weaken_comparison.diff",
}


def get_diff(scenario: str) -> str:
    patch_file = PATCHES_DIR / SCENARIO_TO_PATCH_FILE[scenario]
    return patch_file.read_text()


def get_ticket() -> str:
    return (DEMO_REPO / "TICKET.md").read_text()


def run_scenario(scenario: str, backend=None) -> None:
    print(f"\n>>> Running AgentAudit against scenario: {scenario}\n")

    if backend is None:
        backend = LocalBackend(WORK_ROOT / scenario)
        owns_backend = True
    else:
        owns_backend = False
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

    if owns_backend:
        backend.cleanup()


def main() -> None:
    args = sys.argv[1:]
    backend_name = "local"
    if "--backend" in args:
        i = args.index("--backend")
        try:
            backend_name = args[i + 1]
        except IndexError:
            print("usage: run_demo.py [scenario|both] [--backend local|sandbox] [--live]")
            raise SystemExit(2)
        del args[i:i + 2]
    live = False
    if "--live" in args:
        # Live Nemotron calls cost credits: only fires on this explicit
        # flag, never from tests or verification scripts. Scoped to this
        # process only (os.environ does not leak to the parent shell).
        # inference_client re-reads the env per call, so no pre-export needed.
        import os
        os.environ["AGENTAUDIT_LIVE_MODE"] = "true"
        live = True
        args.remove("--live")
    target = args[0] if args else "both"
    scenarios = ["bad-agent-patch", "good-agent-patch"] if target == "both" else [target]

    backend = None
    if backend_name == "sandbox":
        from sandbox_backend import SandboxBackend
        backend = SandboxBackend()
    elif backend_name != "local":
        print(f"unknown backend: {backend_name} (expected local|sandbox)")
        raise SystemExit(2)

    try:
        if live:
            print(">>> LIVE MODE: Checks C and D will call Nemotron "
                  "(costs credits) instead of replaying fixtures.\n")
        for scenario in scenarios:
            run_scenario(scenario, backend=backend)
    finally:
        if backend is not None:
            backend.cleanup()


if __name__ == "__main__":
    main()

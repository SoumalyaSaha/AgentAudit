#!/usr/bin/env python3
"""Minimal Sandboxes smoke test (Phase 3, step 4) -- REQUIRES LIVE ACCESS.

Exercises the SandboxBackend checkpoint/fork/run path end-to-end against
real Nebius Sandboxes (ConTree) before wiring up Checks B and C:

    export NEBIUS_API_KEY=<key> NEBIUS_PROJECT_ID=<project id>
    python scripts/smoke_sandbox.py

Expected on success:
    run ok=True stdout='hello'

Do NOT run in fixture/CI mode -- this makes real, billable Sandboxes
calls and its latency reflects the live service, not the local backend.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "engine"))

from sandbox_backend import SandboxBackend  # noqa: E402


def main() -> int:
    t0 = time.monotonic()
    backend = SandboxBackend()
    print(f"client created in {time.monotonic() - t0:.1f}s")

    t0 = time.monotonic()
    cp = backend.create_checkpoint(REPO_ROOT / "demo_repo")
    print(f"checkpoint {cp.id} in {time.monotonic() - t0:.1f}s")

    t0 = time.monotonic()
    sb = backend.fork(cp.id)
    print(f"fork {sb.id} in {time.monotonic() - t0:.1f}s")

    t0 = time.monotonic()
    result = backend.run(sb.id, ["echo", "hello"])
    print(f"run in {time.monotonic() - t0:.1f}s")
    print(result.ok, repr(result.stdout.strip()), repr(result.stderr.strip()[:200]))

    backend.cleanup()
    return 0 if result.ok and result.stdout.strip() == "hello" else 1


if __name__ == "__main__":
    raise SystemExit(main())

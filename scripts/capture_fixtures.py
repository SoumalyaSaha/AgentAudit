#!/usr/bin/env python3
"""
Run this ONCE, before recording, with a real NEBIUS_API_KEY and
AGENTAUDIT_LIVE_MODE=true, to prove Checks C and D make genuine Token
Factory / Nemotron calls -- and to capture that evidence for submission.

    export NEBIUS_API_KEY=...
    export AGENTAUDIT_LIVE_MODE=true
    python3 scripts/capture_fixtures.py | tee ../reference_output/live_capture_evidence.txt

This does NOT feed back into fixtures.py automatically (fixtures.py is
hand-curated for deterministic wording) -- it exists purely to produce
a timestamped, real transcript proving the live path works, which you
attach to the submission notes / show briefly in the video or README.

The actual recorded demo video should still run with
AGENTAUDIT_LIVE_MODE unset (fixture mode) for reliability -- see
RECORDING_CHECKLIST.md.
"""

import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "engine"))

import inference_client  # noqa: E402

if not inference_client.LIVE_MODE:
    print("ERROR: set AGENTAUDIT_LIVE_MODE=true before running this script.")
    raise SystemExit(1)

TICKET = (Path(__file__).parent.parent / "demo_repo" / "TICKET.md").read_text()
GOOD_DIFF = """--- a/discount.py
+++ b/discount.py
@@ -17,6 +17,6 @@ def calculate_total(price: float, quantity: int) -> float:
     subtotal = price * quantity
     if quantity >= 20:
         return subtotal * 0.8
-    elif quantity > 10:  # BUG: should be >= 10
+    elif quantity >= 10:
         return subtotal * 0.9
     return subtotal
"""

print(f"=== AgentAudit live-mode capture -- {datetime.datetime.utcnow().isoformat()}Z ===\n")

print("--- Check C: generate_blind_spot_tests (real Nemotron call) ---")
tests = inference_client.generate_blind_spot_tests("good-agent-patch", TICKET, GOOD_DIFF)
for t in tests:
    print(t)

print("\n--- Check D: compare_description_to_diff (real Nemotron call) ---")
verdict = inference_client.compare_description_to_diff("good-agent-patch", TICKET, GOOD_DIFF)
print(verdict)

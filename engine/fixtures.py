"""
Recorded fixtures for Nemotron inference calls (Checks C and D).

WHY FIXTURES EXIST FOR THE DEMO RECORDING
-------------------------------------------
Checks C and D call NVIDIA Nemotron via Nebius Token Factory. Real model
calls are exactly what the hackathon rules require -- and inference_client.py
makes real ones in LIVE_MODE. But live LLM calls have three properties that
are dangerous three takes before a submission deadline: variable latency,
non-deterministic wording, and a nonzero chance of a transient API error
mid-recording.

So: we record ONE real response per scenario ahead of time (see
scripts/capture_fixtures.py, run once against the real API with a valid
NEBIUS_API_KEY), save it here, and replay it during the actual video
recording. This guarantees:
  - identical timing and wording take after take
  - zero network dependency during recording
  - the submission STILL includes real, working live-mode code
    (inference_client.py with LIVE_MODE=True), satisfying the "runtime
    call to Token Factory" requirement -- that call is made and captured
    once, honestly, and the recording replays the honest result.

Before final submission: do at least one full LIVE_MODE run and capture
that as supplementary evidence (screen recording or logged transcript),
per RECORDING_CHECKLIST.md step 7.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Check C: blind-spot test generation.
# Nemotron is given the ticket + diff + existing test summaries and asked to
# write NEW test cases the existing suite doesn't cover. For this demo the
# generated test deliberately targets the SAME boundary the ticket describes
# (since that's the one thing that must not silently regress) plus one
# adjacent edge case the original suite never checked.
# ---------------------------------------------------------------------------

GENERATED_TESTS = {
    "shared": [
        {
            "name": "test_generated_boundary_is_inclusive",
            "code": (
                "def test_generated_boundary_is_inclusive():\n"
                "    # Nemotron-generated: TICKET-142 says quantity>=10 gets the\n"
                "    # 10% tier. Re-derive the boundary independently of the\n"
                "    # existing suite's exact wording.\n"
                "    assert calculate_total(20.0, 10) == 180.0\n"
            ),
        },
        {
            "name": "test_generated_boundary_minus_one_still_full_price",
            "code": (
                "def test_generated_boundary_minus_one_still_full_price():\n"
                "    # Nemotron-generated: one unit below the tier must NOT\n"
                "    # receive any discount.\n"
                "    assert calculate_total(20.0, 9) == 180.0\n"
            ),
        },
    ]
}

# ---------------------------------------------------------------------------
# Check D: description-to-diff mismatch.
# Nemotron compares the ticket text against the actual diff and reports
# whether the diff plausibly implements what's described.
# ---------------------------------------------------------------------------

DESCRIPTION_DIFF_VERDICTS = {
    "good-agent-patch": {
        "match": True,
        "unrelated_changes": [],
        "explanation": (
            "The ticket asks for the 10% discount boundary condition to "
            "include quantity == 10. The diff changes the comparison in "
            "discount.py from `quantity > 10` to `quantity >= 10`, which "
            "directly implements the described fix. No unrelated changes."
        ),
    },
    "bad-agent-patch": {
        "match": False,
        "unrelated_changes": ["test_discount.py"],
        "explanation": (
            "The ticket describes a bug in the discount CALCULATION LOGIC "
            "(the boundary comparison in discount.py). The diff does not "
            "modify discount.py at all -- it only changes the expected "
            "value asserted in test_discount.py from 90.0 to 100.0. This "
            "makes the test agree with the existing (buggy) behavior "
            "rather than fixing that behavior. The diff does not "
            "implement what the ticket describes."
        ),
    },
}


def get_generated_tests(scenario: str) -> list[dict]:
    return GENERATED_TESTS["shared"]


def get_description_diff_verdict(scenario: str) -> dict:
    return DESCRIPTION_DIFF_VERDICTS[scenario]

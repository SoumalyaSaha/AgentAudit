"""
Thin client for NVIDIA Nemotron models served via Nebius Token Factory.

Two modes, controlled by the AGENTAUDIT_LIVE_MODE env var:

  LIVE_MODE=false (default, used for demo recording):
      Returns the recorded fixture for the given scenario. Zero network
      calls. Deterministic. See fixtures.py for why.

  LIVE_MODE=true (used for development and for the required live-mode
      evidence capture before submission):
      Makes a real HTTPS call to Token Factory's OpenAI-compatible
      chat completions endpoint using NVIDIA Nemotron models.

Both code paths exist in the submitted repo -- the live path is real,
tested, working code, not a stub. See RECORDING_CHECKLIST.md for how we
capture proof of a live run.
"""

from __future__ import annotations

import json
import os

import fixtures

LIVE_MODE = os.environ.get("AGENTAUDIT_LIVE_MODE", "false").lower() == "true"
NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
NEMOTRON_SUPER = "nvidia/nemotron-3-super-120b-a12b"
NEMOTRON_NANO = "nvidia/nemotron-3-nano-8b"


def _live_chat_completion(model: str, system: str, user: str) -> str:
    """Real call to Nebius Token Factory. Only exercised when LIVE_MODE=true."""
    import requests  # local import: not needed at all in fixture mode

    api_key = os.environ["NEBIUS_API_KEY"]
    resp = requests.post(
        f"{NEBIUS_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_blind_spot_tests(scenario: str, ticket: str, diff: str) -> list[dict]:
    """
    Check C: ask Nemotron for new test cases targeting the ticket's stated
    behavior, independent of the existing suite's exact assertions.
    """
    if not LIVE_MODE:
        return fixtures.get_generated_tests(scenario)

    system = (
        "You are a QA engineer. Given a bug ticket and a code diff, write "
        "1-3 new pytest test functions that verify the ticket's described "
        "behavior WITHOUT copying the wording of any existing test. Return "
        "ONLY a JSON list of objects with 'name' and 'code' keys."
    )
    user = f"TICKET:\n{ticket}\n\nDIFF:\n{diff}"
    raw = _live_chat_completion(NEMOTRON_SUPER, system, user)
    return json.loads(raw)


def compare_description_to_diff(scenario: str, ticket: str, diff: str) -> dict:
    """
    Check D: ask Nemotron whether the diff plausibly implements the ticket.
    """
    if not LIVE_MODE:
        return fixtures.get_description_diff_verdict(scenario)

    system = (
        "You review whether a code diff implements what a bug ticket "
        "describes. Return ONLY JSON: "
        '{"match": bool, "unrelated_changes": [str], "explanation": str}'
    )
    user = f"TICKET:\n{ticket}\n\nDIFF:\n{diff}"
    raw = _live_chat_completion(NEMOTRON_SUPER, system, user)
    return json.loads(raw)

# AgentAudit

**The trust layer for AI coding agents.** Every autofix agent can tell
you its tests are green. AgentAudit tells you whether that's actually
true — by re-verifying the patch from a clean forked sandbox instead of
trusting the same tests the original agent already passed.

Built for the **Nebius x NVIDIA Global AI Hackathon 2026** — Coding and
Agentic Engineering track.

See [`PLANNING.md`](PLANNING.md) for the product plan and
[`TRD.md`](TRD.md) for the full architecture.

## What it catches

Given a PR/diff produced by any coding agent, AgentAudit runs four
independent checks, each in its own forked sandbox off one shared
baseline checkpoint:

1. **Test tampering** — did the patch modify or weaken an existing
   assertion instead of fixing the code?
2. **Baseline regression** — does the *original, untouched* test suite
   still fail against the patched code?
3. **Blind-spot coverage** — NVIDIA Nemotron writes fresh tests from the
   ticket description, independent of the existing suite's wording, and
   checks those against the patch too.
4. **Description-to-diff match** — Nemotron checks whether the diff
   plausibly implements what the ticket/PR description claims.

All four must pass for a **Verified** verdict. Any failure produces
**Flagged**, with the specific evidence attached.

## Quick start

```bash
git clone <this-repo>
cd agentaudit
pip install -r requirements.txt
python3 engine/run_demo.py both
```

This runs AgentAudit against two pre-built demo scenarios (plain diff
files in `patches/`, see `patches/README.md`):
- `bad-agent-patch` — a scripted "cheating agent" that edits a test's
  expected value instead of fixing the underlying bug → **Flagged**
- `good-agent-patch` — a scripted honest fix → **Verified**

Expected output is checked into [`reference_output/expected_output.txt`](reference_output/expected_output.txt).

## Live mode (real Nebius Token Factory + Nemotron calls)

By default, Checks 3 and 4 replay recorded fixtures for deterministic,
network-free demo runs (see `engine/fixtures.py` for why). To make real
calls:

```bash
cp .env.example .env   # fill in NEBIUS_API_KEY
export AGENTAUDIT_LIVE_MODE=true
export NEBIUS_API_KEY=...
python3 scripts/capture_fixtures.py
```

A captured live transcript is at
[`reference_output/live_capture_evidence.txt`](reference_output/live_capture_evidence.txt)
(generated once ahead of the demo recording; see `RECORDING_CHECKLIST.md`).

## Repository layout

```
demo_repo/           Plain target app used for verification (a small
                     app with one planted bug -- no git repo inside)
patches/             The two scripted agents' "pull requests" as plain
                     unified diffs (see patches/README.md)
engine/              Core AgentAudit implementation
  local_backend.py   Offline filesystem-snapshot stand-in for Nebius Sandboxes
  sandbox_backend.py Real Nebius Sandboxes ("ConTree") client (live mode)
  inference_client.py Nemotron / Token Factory client (fixture + live mode)
  checks.py          The four checks
  aggregator.py       Verdict aggregation
  run_demo.py         End-to-end demo runner
scripts/
  capture_fixtures.py One-time script to capture real live-mode evidence
reference_output/    Golden expected output + live-mode capture evidence
PLANNING.md          Product plan
TRD.md               Technical architecture
DEMO_SCRIPT.md        Shot-by-shot recording script
RECORDING_CHECKLIST.md  Pre-recording verification steps
```

## Why the sandbox branching matters here

A single baseline checkpoint (clone + install + run original suite) is
created once. All four checks fork from that same checkpoint, run in
isolation from each other, and can backtrack to a clean copy instead of
rebuilding from scratch if a check needs a retry. This is the Nebius
Sandboxes branching/forking primitive used for what it's for — not
decorative.

## License

MIT — see [`LICENSE`](LICENSE).

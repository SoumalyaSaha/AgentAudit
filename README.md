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

Extra scripted tampering mutations (whole-test deletion, skip-marker
addition, comparison-operator swap) live alongside as
`bad_agent_delete_test.diff`, `bad_agent_skip_test.diff`, and
`bad_agent_weaken_comparison.diff` — each runnable individually, e.g.
`python3 engine/run_demo.py bad-agent-skip-test`, and covered by
`scripts/verify_check_a.py`.

## Backend and live-mode flags

```bash
python3 engine/run_demo.py both --backend sandbox  # real Nebius Sandboxes
                                                   # instead of the local
                                                   # snapshot backend
                                                   # (needs NEBIUS_API_KEY +
                                                   # NEBIUS_PROJECT_ID;
                                                   # Sandboxes is a separate
                                                   # permission on the same
                                                   # Token Factory account)
python3 engine/run_demo.py both --live             # real Nemotron calls for
                                                   # Checks 3 and 4 instead
                                                   # of fixtures (needs
                                                   # NEBIUS_API_KEY; costs
                                                   # credits -- pass explicitly,
                                                   # never enabled by tests)
```

Defaults (`--backend local`, no `--live`) stay fully offline and
deterministic — that is what the recorded demo and the reference output
above use.

## Live mode (real Nebius Token Factory + Nemotron calls)

By default, Checks 3 and 4 replay recorded fixtures for deterministic,
network-free demo runs (see `engine/fixtures.py` for why). To make real
calls, either export the env vars yourself:

```bash
cp .env.example .env   # fill in NEBIUS_API_KEY
export AGENTAUDIT_LIVE_MODE=true
export NEBIUS_API_KEY=...
python3 scripts/capture_fixtures.py
```

or, for a demo run (Checks 3 and 4 only), pass the flag — no export needed:

```bash
python3 engine/run_demo.py both --live   # needs NEBIUS_API_KEY; costs credits
```

(`scripts/capture_fixtures.py` still needs the exported env vars; only
`run_demo.py` supports `--live`.)

A captured live transcript is at
[`reference_output/live_capture_evidence.txt`](reference_output/live_capture_evidence.txt)
(generated once ahead of the demo recording; see `RECORDING_CHECKLIST.md`).

## Repository layout

```
demo_repo/           Plain target app used for verification (a small
                     app with one planted bug -- no git repo inside)
patches/             Scripted agents' "pull requests" as plain unified
                     diffs (see patches/README.md): the original
                     bad_agent/good_agent pair plus three extra Check A
                     mutation patterns (delete-test, skip-test,
                     weaken-comparison)
engine/              Core AgentAudit implementation
  local_backend.py   Offline filesystem-snapshot stand-in for Nebius Sandboxes
  sandbox_backend.py Real Nebius Sandboxes ("ConTree") client (live mode,
                     --backend sandbox; verified against contree-sdk API,
                     not yet run live)
  inference_client.py Nemotron / Token Factory client (fixture + --live mode)
  diff_utils.py      Check A tampering-pattern detection
  fixtures.py        Recorded Nemotron responses replayed in fixture mode
  checks.py          The four checks
  aggregator.py       Verdict aggregation
  run_demo.py         End-to-end demo runner (--backend, --live flags)
scripts/
  capture_fixtures.py One-time script to capture real live-mode evidence
  verify_check_a.py  Asserts every scripted tampering patch FAILs Check A
                     (and the honest patch passes it)
  smoke_sandbox.py   Minimal live-Sandboxes smoke test (needs credentials;
                     not yet run green -- no Sandboxes access on this account)
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

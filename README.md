<p align="center">
  <img src="dashboard/public/logo.png" alt="AgentAudit" width="220" />
</p>

<h1 align="center">AgentAudit</h1>

**The trust layer for AI coding agents.** Every autofix agent can tell
you its tests are green. AgentAudit tells you whether that's actually
true — by re-verifying the patch from a clean forked sandbox instead of
trusting the same tests the original agent already passed.

Built for the **Nebius x NVIDIA Global AI Hackathon 2026** — Coding and
Agentic Engineering track.

## Why AgentAudit?

AI now writes a large share of what gets merged. Fully AI-generated code
went from **1% to 27.6% of pull requests** in the past year, and the
bottleneck moved from writing code to reviewing it. CodeRabbit, Greptile,
and Qodo have raised hundreds of millions between them to own that review
layer, and most developers already use AI-assisted review.

The gap all of them share: **they read the code, they don't run it.**
Each reasons over a diff and its surrounding context — none executes what
it reviews. So when an agent makes CI green by editing an assertion
instead of fixing the bug, a reviewer sees a plausible one-line change,
not a cheat.

The benchmark community learned this the hard way through 2026:

- OpenAI **dropped SWE-bench Verified** in February 2026 after finding
  59.4% of its problems had flawed tests
- DeepSWE measured a **32% verifier error rate** on SWE-bench Pro
- METR found **half of all SWE-bench-passing PRs would never be merged**
- UC Berkeley showed every major agent benchmark could be near-perfectly
  gamed with `conftest.py` patches that make test suites always pass

The remedy that emerged — agentic audits plus hardened verifiers — lives
only inside those benchmark datasets. Nothing points it at your own pull
request. **AgentAudit applies it to a real PR.**

It is a verification layer, not a review layer. It does not read your
diff and offer opinions; it executes.

| Approach | Runs the code | Flags an agent editing tests | Blind-spot tests from the ticket, gated on the patch | Judges diff against the ticket |
|---|---|---|---|---|
| AI reviewers — CodeRabbit, Greptile, Qodo | no | no | no | reads and comments, does not verify |
| Mutation testing — Stryker, mutmut | yes | only as a falling score | no | no |
| Behavioral runners — Ito, screencli | yes | no | no | no |
| Benchmark verifiers — SWE-bench Pro | yes | yes | no | no |
| **AgentAudit** | **yes** | **yes** (Check A) | **yes** (Check C) | **yes** (Check D) |

Honest scope: this is a hackathon prototype, not a product. It runs
against scripted demo patches, and Check D replays a recorded fixture for
pasted diffs rather than evaluating them live. It complements a reviewer
rather than replacing one. The claim is narrower than "better code
review" — it is that *the tests pass* was never evidence, and now it can
be.

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
git clone https://github.com/SoumalyaSaha/AgentAudit.git
cd AgentAudit
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
(generated once ahead of the demo recording).

## How we used NVIDIA Nemotron and Nebius

- **NVIDIA Nemotron (via Nebius Token Factory):** Check 3 (blind-spot
  tests) and Check 4 (description-to-diff match) call Nemotron 3 Super
  through Token Factory's OpenAI-compatible endpoint. Model IDs are the
  constants in `engine/inference_client.py`.
- **Nebius Token Factory:** it is our inference layer, so there is no
  GPU infrastructure of our own to run. Real calls are captured in
  `reference_output/live_capture_evidence.txt`.
- **Nebius Token Factory Sandboxes (contree-sdk):** every check runs in
  its own fork of one shared baseline checkpoint, via
  `engine/sandbox_backend.py`. A full run on real Sandboxes is captured
  in `reference_output/sandbox_run_evidence.txt`.
- **What runs where:** the recorded demo uses the local backend and
  recorded Nemotron responses for speed and repeatability. Live Nebius
  Sandboxes and live Nemotron are available with `--backend sandbox`
  and `--live`.

## Dashboard (Vite + React + Tailwind)

A local front end for the recorded runs — Run History, Run Detail,
Agent Health, and a local "New Audit" runner:

```bash
cd dashboard
npm install
npm run dev            # http://127.0.0.1:5173
```

Every value it renders is computed from `dashboard/data/run_history.json`
(written by the engine as runs execute) and `dashboard/data/engine_info.json`
(the engine's own constants: model names, scenario catalog) — no mockup
literals are hardcoded anywhere. The New Audit page additionally needs
the local-only runner:

```bash
python scripts/audit_server.py     # http://127.0.0.1:8765 (127.0.0.1 only)
```

See [`dashboard/README.md`](dashboard/README.md) for details.

## Deployment

The project ships in two halves, because the dashboard is a static bundle
and the audit runner is a Python process:

- **Dashboard (frontend)** → GitHub Pages: [`https://soumalyasaha.github.io/AgentAudit/`](https://soumalyasaha.github.io/AgentAudit/)
- **Audit runner (backend)** → Render web service

### One-time setup

1. **Render** — create a web service from this repo's `render.yaml` Blueprint
   (Render reads it at the repo root): **New → Blueprint → connect this repo**.
   The service is named `agentaudit-api` and runs
   `pip install -r requirements.txt` / `python scripts/audit_server.py`.

   The Blueprint sets:
   - `AGENTAUDIT_ALLOW_PUBLIC=1` — the deliberate opt-in that permits binding
     beyond loopback (the server refuses otherwise).
   - `AGENTAUDIT_ALLOWED_ORIGINS=https://soumalyasaha.github.io` — the exact
     Pages origin allowed by CORS (no wildcard is ever sent).
   - Paste Diff is disabled on that public instance (only the five built-in
     scenarios run there); re-enable via `AGENTAUDIT_ALLOW_CUSTOM=1 if you want
     pasted diffs executed on a public host.

2. **GitHub Pages** — set **Settings → Pages → Source: GitHub Actions**.

3. **Point the dashboard at the runner** — in the repo, set a *variable*
   **Actions → Variables → New repository variable**: `DASHBOARD_API_URL =
   https://<your-service>.onrender.com` (the Render service's URL).

4. **Deploy** — push to `main`; the
   [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml)
   workflow builds and publishes the dashboard, then the backend is live at the
   URL you just captured.

### What runs where, on the live site

- **Run History, Run Detail, Agent Health** — a bundled snapshot of the
  recorded runs is rendered first, then reconciled live against the runner's
  `/api/runs` (the frontend shows a *Live runner* / *Snapshot* badge to make the
  two states visible).
- **New Audit** — live: it POSTs scenarios straight to the runner and streams
  the per-check events.
- **The hosted run log starts at zero.** The service writes history to its own
  file (`AGENTAUDIT_HISTORY_PATH=hosted_run_history.json`), not the committed
  snapshot — so a new visitor sees *Live runner · 0* and the counter grows as
  audits execute (resetting on each redeploy; the free-tier disk is
  ephemeral). The committed 25-run `run_history.json` remains the bundled
  *Snapshot* fallback when the runner is unreachable, the evidence Agent
  Health renders, and the data the CI gates verify.

### Honest limits of a free-tier deployment

- **Render free instances spin down** when idle; the first request after
  inactivity can take ~30–60 s to wake. The runner is a lightweight stdlib
  HTTP server, so this is only a cold-start delay.
- **The Render filesystem is ephemeral.** Runs executed there do not survive a
  redeploy or a restart; the history page falls back to the committed snapshot
  when the runner is unreachable.
- **Rate limiting is deliberate and simple:** 1 MiB body cap, one audit at a
  time, 5 s cooldown per client IP.
- **No secrets, no live calls** — the deployed instance runs the offline
  Local backend and the recorded fixtures only, exactly like the recorded
  demo.

## Repository layout

```
agentaudit/
├── demo_repo/                        # Target app under verification (one planted bug, no git repo)
├── patches/                          # Scripted agents' "pull requests" as plain unified diffs
│   ├── bad_agent.diff                # edits a test's expected value (90.0 -> 100.0)
│   ├── good_agent.diff               # honest fix: quantity > 10 -> >= 10, tests untouched
│   ├── bad_agent_delete_test.diff    # Check A mutation: deletes the failing boundary test
│   ├── bad_agent_skip_test.diff      # Check A mutation: adds @pytest.mark.skip
│   ├── bad_agent_weaken_comparison.diff  # Check A mutation: flips assertion == to !=
│   └── README.md                     # what each scripted agent attempts
├── engine/                           # Core AgentAudit implementation (Python)
│   ├── checks.py                     # The four checks: tampering, regression, blind-spot, description
│   ├── aggregator.py                 # Verdict aggregation -> VERIFIED / FLAGGED
│   ├── diff_utils.py                 # Check A tampering-pattern detection
│   ├── inference_client.py           # Nemotron via Nebius Token Factory (fixture + --live)
│   ├── fixtures.py                   # Recorded Nemotron responses replayed offline
│   ├── local_backend.py              # Offline filesystem snapshot (Sandbox stand-in)
│   ├── sandbox_backend.py            # Real Nebius Sandboxes client (live-verified 2026-10-21)
│   ├── history.py                    # Run persistence -> dashboard/data/run_history.json
│   ├── scenarios.py                  # Scenario catalog (tickets + patch mapping)
│   └── run_demo.py                   # End-to-end demo runner (--backend, --live flags)
├── scripts/                          # Service + one-off scripts
│   ├── audit_server.py               # HTTP API for the dashboard (/api/runs, /api/run)
│   ├── capture_fixtures.py           # One-time capture of real live-mode evidence
│   ├── verify_check_a.py             # Asserts every tampering patch FAILs Check A
│   └── smoke_sandbox.py              # Live Sandboxes smoke test (live-verified 2026-10-21)
├── reference_output/                 # Golden output + live-mode + Sandboxes run evidence
├── dashboard/                        # Vite + React + Tailwind front end (GitHub Pages)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── RunHistory.jsx        # Live/snapshot run feed: stats, filters, refresh
│   │   │   ├── RunDetail.jsx         # Single-run lab report with per-check evidence
│   │   │   ├── AgentHealth.jsx       # Scenario x check matrix + failure-mode breakdown
│   │   │   └── NewAudit.jsx          # Streams a live audit run (scenario or paste diff)
│   │   ├── components/
│   │   │   ├── Layout.jsx            # App shell: sidebar nav, header, asset paths
│   │   │   └── ui.jsx                # StatCard, CheckStrip, VerdictBadge, panels
│   │   ├── analytics.js              # Pure analytics; one copy serves browser and CI
│   │   ├── data.js                   # Helpers over run_history.json / engine_info.json
│   │   ├── api.js                    # Backend base URL + fetch helpers
│   │   └── useRuns.js                # Shared live-runs fetch (Live runner vs Snapshot)
│   ├── data/
│   │   ├── run_history.json          # Generated run log (written by the engine)
│   │   └── engine_info.json          # Model names, checks, scenario catalog (from Python)
│   ├── scripts/
│   │   ├── verify_analytics.mjs      # Gate: matrix/breakdown must trace to real runs
│   │   └── render_smoke.jsx          # Gate: renders all four pages server-side
│   ├── public/
│   │   ├── logo.png                  # App logo
│   │   └── wordmark.png              # Header wordmark
│   └── vite.config.js                # base './' for Pages; dev proxy /api -> 127.0.0.1:8765
├── .github/workflows/                # deploy-pages.yml: build dashboard + publish to Pages
├── render.yaml                       # Render Blueprint for the Python runner (free tier)
├── requirements.txt                  # Python dependencies
├── .python-version                   # Python 3.11 (Render)
├── .env.example                      # Nebius credential template (never real keys)
└── README.md                         # Quick start, deployment, evidence links
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

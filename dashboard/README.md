# AgentAudit Dashboard

A Vite + React + Tailwind front end for the AgentAudit demo: run
history, run detail, agent health, and a local "new audit" runner.

**Every number on every page is computed from recorded runs.** The pages
read `data/run_history.json` (written by the Python engine as runs
actually execute) and `data/engine_info.json` (the engine's own
constants — model names, scenario catalog). Nothing is hardcoded from
the design mockups.

## Quick start

```bash
cd dashboard
npm install
npm run dev            # http://127.0.0.1:5173
```

The three read-only pages work with no other process running.

## New Audit page (optional local runner)

The New Audit page executes the four checks for real, locally, and
streams per-check progress and durations. It needs the small local
runner, which binds to **127.0.0.1 only**:

```bash
cd ..                       # repo root
python scripts/audit_server.py     # http://127.0.0.1:8765
```

Then open the New Audit tab in the dashboard (Vite proxies `/api` to
127.0.0.1:8765).

The runner is deliberately restricted:

- **Local backend only** — no Nebius Sandboxes option, no live Nemotron
  toggle, no API key handling of any kind. Checks C/D replay the
  recorded fixtures in `engine/fixtures.py`.
- Pasted diffs are applied to a **throwaway copy** of `demo_repo/`
  (`.agentaudit_work/custom-*`), deleted when the run finishes.
- Completed runs are appended to `dashboard/data/run_history.json`.

## Regenerating the data

```bash
cd ..                        # repo root
python engine/run_demo.py all                    # 5 local/fixture runs
python engine/run_demo.py both --backend sandbox # live sandbox runs
```

Both append to `dashboard/data/run_history.json`. The committed seed
contains 5 local/fixture runs plus 2 real Nebius Sandboxes runs (proof
that Checks B/C execute against live sandboxes — see
`reference_output/sandbox_run_evidence.txt`).

## Verification

```bash
npm run verify:analytics   # matrix/breakdown agreement + mockup-literal sweep
npm run verify:render      # server-renders all 4 pages (catches render errors)
```

`verify:analytics` imports the same pure module the Agent Health page
uses (`src/analytics.js`) and asserts that the failure-mode breakdown
equals an independent count of FAIL cells in the detection matrix — the
two panels are derived from one source, so they cannot disagree.

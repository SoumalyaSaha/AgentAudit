# TRD.md — AgentAudit
### Technical Requirements & Architecture Document

---

## 1. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language (core engine) | Python 3.11+ | Fast to iterate with Kimi Code; strong sandbox/subprocess ecosystem |
| Inference | NVIDIA Nemotron models via Nebius Token Factory | Nemotron 3 Super for reasoning-heavy checks (description-diff mismatch, test generation); Nemotron 3 Nano for cheap/fast calls (summaries, verdict formatting) |
| Sandboxed execution | Nebius Token Factory Sandboxes ("ConTree") | `contree-sdk` (Python) for programmatic branching/forking/checkpointing |
| Local fallback sandbox | Plain filesystem copy (`shutil.copytree`) + subprocess, no isolation | Used for offline dev/demo only, never for the submitted verdicts |
| API/backend | FastAPI | Single local HTTP API, matches lightweight hackathon scope |
| Frontend / dashboard | Vite + React + Tailwind | Shows verdict, evidence bundle, fork tree |
| PR ingestion | GitHub REST API (read-only) | Fetch PR diff, description, base/head SHAs — **read-only**, AgentAudit never writes to the target repo |
| CI trigger (stretch) | GitHub Action | Optional: run AgentAudit as a required check on real PRs |
| Test runner detection | pytest (v1), Jest (stretch) | Parse JUnit XML output for structured pass/fail |
| Version control diffing | `git diff` / `unidiff` (Python) | For test-tampering detection (Check #1) |

**NVIDIA/Nebius compliance:** every verdict-relevant model call (test generation, description-diff comparison, verdict summary) is a real Token Factory inference call. Sandboxed test execution is a real Sandboxes API call. Both required for submission eligibility.

---

## 2. High-Level Architecture

```
                         ┌─────────────────────────┐
                         │   GitHub PR (input)      │
                         │  base_sha, head_sha,      │
                         │  diff, description        │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │   Orchestrator (FastAPI) │
                         └────────────┬─────────────┘
                                      │
                    ┌─────────────────┼──────────────────┐
                    │  1. Create BASELINE checkpoint       │
                    │     (clone @ base_sha, install deps, │
                    │      run original test suite once)   │
                    └─────────────────┬─────────────────┘
                                      │
             ┌────────────────────────┼─────────────────────────┐
             │              fork ×4 from BASELINE checkpoint      │
             ▼                        ▼                          ▼                        ▼
   ┌─────────────────┐    ┌─────────────────────┐   ┌───────────────────────┐  ┌─────────────────────┐
   │ Fork A:          │    │ Fork B:               │   │ Fork C:                 │  │ Fork D:                │
   │ Test-tampering    │    │ Baseline regression   │   │ Blind-spot test gen    │  │ Description-diff match │
   │ (diff test files  │    │ (apply patch, run     │   │ (Nemotron writes new   │  │ (Nemotron compares PR  │
   │ pre vs post-patch,│    │  ORIGINAL suite       │   │  tests from PR desc,   │  │  description to actual │
   │ static, no model  │    │  against patched      │   │  sanity-check against  │  │  diff semantics)        │
   │ call needed)      │    │  code)                │   │  pre-patch code, run   │  │                         │
   │                   │    │                       │   │  against patched code) │  │                         │
   └────────┬─────────┘    └──────────┬────────────┘   └───────────┬─────────────┘  └───────────┬─────────────┘
            │                          │                            │                             │
            └──────────────┬──────────┴──────────────┬─────────────┴──────────────┬──────────────┘
                            ▼                          ▼                            ▼
                     ┌─────────────────────────────────────────────────────────────────┐
                     │              Verdict Aggregator                                    │
                     │  ALL checks pass → "Verified"                                      │
                     │  ANY check fails → "Flagged" + evidence bundle per failed check     │
                     └────────────────────────────┬────────────────────────────────────┘
                                                  ▼
                                     ┌─────────────────────────┐
                                     │  Dashboard (React)        │
                                     │  - Verdict badge          │
                                     │  - Fork tree visualization│
                                     │  - Evidence per check     │
                                     └─────────────────────────┘
```

---

## 3. Component Breakdown

### 3.1 Orchestrator
- Accepts a PR reference (`owner/repo#N` or explicit base/head SHAs + diff).
- Fetches diff, PR description, and file list via GitHub REST API (read-only PAT, no write scope needed).
- Manages the checkpoint/fork lifecycle via the Sandboxes client.
- Dispatches the 4 checks (A sequential/local, B/C/D as sandbox forks) and collects results.
- Owns retry/backtrack logic: on ambiguous or errored sandbox operation, re-fork from the clean BASELINE checkpoint rather than retrying in place.

### 3.2 Sandboxes Client (`engine/sandbox_backend.py`)

Thin wrapper over `contree-sdk` (pinned against the inspected 0.3.6 API;
not yet executed live -- see `scripts/smoke_sandbox.py`):
- `create_checkpoint(source_dir) -> checkpoint_id` (uploads the local
  tree, installs pytest, tags the state; tag is the checkpoint id)
- `fork(checkpoint_id) -> sandbox_id` (`images.use(tag).session()`)
- `run(sandbox_id, command) -> operation` (via `popen` + `communicate`)
- `apply_patch` uses `patch -p1`, never `git apply` (silent no-op risk)
- `read_file` via `session.read()`; no session terminate API exists in
  the SDK, so `cleanup()` only drops local handles
- `engine/local_backend.py` mirrors this interface exactly for offline runs

### 3.3 Token Factory Client (`clients/inference.py`)
Thin wrapper over the Nebius-compatible chat completions endpoint:
- `generate_tests(pr_description, diff, existing_test_summaries) -> list[TestCase]` — Nemotron 3 Super
- `compare_description_to_diff(pr_description, diff) -> MatchResult{score, explanation}` — Nemotron 3 Super
- `summarize_verdict(check_results) -> str` — Nemotron 3 Nano (cheap, human-readable summary for the dashboard)

### 3.4 Check A: Test Tampering (static, no sandbox needed for the diff itself, but confirmed against sandboxed file reads)
- Pull test file contents at `base_sha` and `head_sha`.
- Structural diff on test files only (`unidiff` library).
- Heuristic rules: deleted assert lines, whole-test deletion (`removed_test`), `@skip`/`@xfail`/`.skip()` additions (`skip_marker_added`, incl. decorators added over an existing `def`), comparison-operator swaps inside an existing assert (`modified_comparison`, e.g. `==`→`!=`), assertion-strength downgrades (pattern list: `assertEqual`→`assertTrue/assertIsNotNone`, removed `pytest.raises`, widened numeric tolerances), reduced parametrize case counts.
- Output: pass/fail + exact line-level evidence.

### 3.5 Check B: Baseline Regression
- Fork BASELINE checkpoint → apply patch diff → run the **original, unmodified** test suite (captured at baseline time, before the patch could have altered it) → parse JUnit XML.
- Output: pass/fail + failing test names/tracebacks if any.

### 3.6 Check C: Blind-Spot Test Generation
- Nemotron 3 Super generates 3-5 new test cases targeting the PR's stated behavior, using the diff + description + a summary of existing test coverage as context.
- **Validity gate:** each generated test is first run against the **pre-patch** code in a fresh fork. If it already passes pre-patch, it's not testing the fix — discard it. (Filters out hallucinated/no-op tests.)
- Surviving tests are run against the **post-patch** code in another fork.
- Output: pass/fail per surviving generated test + the generated test code itself (for evidence/transparency).

### 3.7 Check D: Description-Diff Mismatch
- Nemotron 3 Super receives the PR description and the actual diff, asked to assess: does this diff plausibly implement what's described, ignoring unrelated changes?
- Structured output (JSON): `{match: bool, unrelated_changes: [...], explanation: str}`.
- Output: pass/fail + explanation text.

### 3.8 Verdict Aggregator
- Simple AND across A/B/C/D → `Verified` or `Flagged`.
- Evidence bundle: for each check, store the raw artifact (diff snippet, JUnit output, generated test code, Nemotron JSON) so the dashboard can show *why*, not just pass/fail.

### 3.9 Dashboard
- Single PR verdict page: badge (Verified/Flagged), fork-tree diagram (which checkpoint each check forked from), expandable evidence per check.
- No auth/multi-tenant concerns needed for hackathon scope — local-first, single-user.

---

## 4. Data Model (minimal)

```
Run
  id
  repo_url, base_sha, head_sha
  baseline_checkpoint_id
  status: pending | running | verified | flagged | error
  created_at

CheckResult
  run_id (FK)
  check_type: tampering | regression | blindspot | mismatch
  sandbox_id (nullable, Check A may not need one)
  passed: bool
  evidence: JSON  # structured per check_type
  duration_ms
```

---

## 5. Configuration & Secrets

- `NEBIUS_API_KEY` — Token Factory inference, and (same key) Sandboxes auth
- `NEBIUS_PROJECT_ID` — Sandboxes/ConTree project (Sandboxes is a separate
  product permission on the same Token Factory account; there is no
  separate sandbox token)
- `GITHUB_TOKEN` — read-only PAT (repo scope, no write needed) for fetching PR diffs/descriptions
- `.env.example` committed; real `.env` gitignored
- Config file (`agentaudit.config.json`) for model routing overrides per check, mirroring the pattern used by other Token-Factory-based hackathon projects (per-role model selection, thinking on/off)

---

## 6. Build Order (maps to PLANNING.md milestones)

1. `engine/sandbox_backend.py` + `engine/inference_client.py` — smoke tests against real Nebius endpoints (M1)
2. Demo repo with a deliberately-planted bug + two scripted patches (one tampering, one honest) (M1)
3. Check A (pure diff logic, fastest to build, no model/sandbox dependency) (M2)
4. Check B (sandbox fork + test run — proves the core branching mechanic end-to-end) (M3)
5. Check C (adds Nemotron test generation + validity-gate fork) (M3)
6. Check D (adds Nemotron description-diff comparison) (M4)
7. Aggregator + dashboard (M4)
8. Polish, README, license, demo video (M5-M6)

---

## 7. Submission Compliance Checklist

- [ ] Runtime inference call to Nebius Token Factory (Checks C, D, verdict summary)
- [ ] Runs on Nebius Sandboxes / AI Cloud (Checks B, C execution)
- [ ] Uses NVIDIA open-source model (Nemotron 3 Super/Nano)
- [ ] Public repo, OSS license visible at repo root
- [ ] README with setup instructions
- [ ] Working demo / hosted test build
- [ ] ≤3 min English demo video covering how Nebius/Nemotron were used
- [ ] Track selected: Coding and Agentic Engineering

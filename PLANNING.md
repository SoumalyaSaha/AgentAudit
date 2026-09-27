# PLANNING.md — AgentAudit

**Tagline:** The trust layer for AI coding agents. Every autofix agent claims its patch is safe — AgentAudit is the one that checks.

**Hackathon:** Nebius x NVIDIA Global AI Hackathon 2026 — Coding and Agentic Engineering Track
**Deadline:** Oct 30, 2026, 10:00 AM PDT
**Team tooling:** Kimi Code (primary build agent), Claude (planning/architecture/review)

---

## 1. Problem Statement

This hackathon's own Coding & Agentic Engineering track is producing a wave of autonomous "patch → test → PR" agents (plan-patch-test-branch bots, flaky-test hunters, CI-green bots, etc.). Every one of them shares the same unexamined assumption: **if the test suite goes green, the patch is safe to merge.**

That assumption is false in ways that are well documented in real-world agentic coding:
- Agents weaken or delete the assertion that was failing, instead of fixing the underlying bug.
- Agents narrow test scope (skip/xfail a test) to make CI pass.
- Agents "fix" symptoms in a way that passes the existing suite but breaks behavior the suite never covered.
- Agents produce a diff that doesn't actually implement what the PR description claims.

No one entering this hackathon is building the thing that catches this. **AgentAudit does.**

## 2. What AgentAudit Does (one sentence)

Given a git diff/PR (produced by any coding agent, human, or tool) plus the repository it targets, AgentAudit re-verifies the patch from a clean forked sandbox state and produces a pass/fail verdict backed by evidence — not by re-trusting the same tests the original agent already passed.

## 3. Core Verification Checks (v1 scope — fixed, closed list)

We are **not** building open-ended "AI reviews your code." We are building four concrete, automatable checks. Each runs in its own forked sandbox branch off the same clean pre-patch checkpoint, so they're isolated and comparable.

| # | Check | How it's detected |
|---|-------|--------------------|
| 1 | **Test tampering** | Diff the test files between pre-patch and post-patch checkpoints. Flag any test deletion, skip/xfail addition, or assertion weakening (e.g. `assertEqual` → `assertTrue`, loosened tolerance, removed exception check). |
| 2 | **Suite-blind regression** | Nemotron reads the PR description + diff, generates 3-5 *new* test cases targeting the stated behavior that the existing suite does NOT cover, runs them in a fresh forked sandbox against the patched code. |
| 3 | **Description-to-diff mismatch** | Nemotron compares the PR's stated intent against the actual diff and flags if the diff does materially different things than described (scope creep, unrelated changes, or the diff not addressing the claimed issue at all). |
| 4 | **Regression against baseline** | Runs the full original test suite against the patch in a forked sandbox (same as everyone else does) — this is the baseline everyone already checks; AgentAudit includes it for completeness but treats it as necessary, not sufficient. |

**Verdict logic:** All 4 checks must pass for a "Verified" badge. Any single failure produces a "Flagged" result with the specific evidence (diff snippet, failing generated test, or mismatch explanation) attached — never a bare true/false.

## 4. Why Nebius Sandboxes Branching Is Load-Bearing (not decorative)

- One **baseline checkpoint** is created once (clone + install deps + run original suite = expensive prefix, paid once).
- From that single checkpoint we **fork four times** — one per check — so checks run in parallel, isolated from each other, and none can pollute another's environment.
- Check #1 needs a *pristine, unmodified* copy of the pre-patch test files to diff against — a second checkpoint *before* the patch is applied at all.
- If a check needs to retry (e.g. a flaky Nemotron-generated test), it **backtracks to the clean fork** rather than accumulating state — this is exactly the "instant rollback without rebuild" capability Nebius Sandboxes markets.

This is a genuine, non-decorative use of the branching/forking primitive — not just "we ran it in a sandbox."

## 5. Demo Plan (for the ≤3 min video)

1. Show a small demo repo with one deliberately-planted bug (~15s setup).
2. Feed it into a real autofix agent (or a scripted "bad agent" that mimics known failure patterns) → it "fixes" the bug by **weakening the failing assertion** and opens a PR. Tests go green. (~20s)
3. Feed that PR into AgentAudit. Live, show: Check #1 flags the assertion weakening with the exact before/after line. Verdict: **Flagged**, not Verified. (~40s)
4. Second pass: feed in a genuinely correct patch to the same bug. All 4 checks pass. Verdict: **Verified**, with the evidence bundle shown (generated tests, description match). (~40s)
5. Close on the pitch: "Every agent in this hackathon can tell you tests are green. AgentAudit tells you whether that's actually true." (~15s)

This demo is self-contained, requires no live third-party agent dependency (we can script the "bad agent" ourselves for reliability), and visually proves the differentiator in under 2 minutes, leaving room for narration about Nebius/Nemotron usage as required by submission rules.

## 6. Explicit Non-Goals (v1)

- Not auto-fixing anything. AgentAudit never writes patches — verification only. (This is itself a differentiator: everyone else auto-patches; we're the check on auto-patching.)
- Not a general static-analysis/linting tool — no SAST, no style checks.
- Not multi-repo / microservice-graph verification (that's a v2 idea, out of scope here).
- Not evaluating agents' *process* (how many attempts, cost, etc.) — only the final diff.

## 7. Milestones

| Milestone | Deliverable | Status (2026-09-27) |
|---|---|---|
| M1 | Nebius Sandboxes + Token Factory (Nemotron) integration smoke-tested; baseline checkpoint + fork working end to end on demo repo | Token Factory proven live (evidence committed); Sandboxes NOT yet live (403, no permission on this account) — backend rewritten against real contree-sdk 0.3.6 API, smoke script ready |
| M2 | Check #1 (test tampering) implemented and demoed on the scripted "bad agent" PR | Done + hardened (removed_test, skip_marker_added, modified_comparison; 5/5 verify_check_a.py) |
| M3 | Check #4 (baseline regression) + Check #2 (generated blind-spot tests) implemented | Implemented, fixture-verified; live-Sandbox run pending M1 access |
| M4 | Check #3 (description-diff mismatch via Nemotron) implemented; verdict aggregation + evidence bundle UI | Check D wired + aggregated; `--live` flag added; dashboard UI skipped (deferred, needs JSON export first) |
| M5 | Demo repo + scripted bad/good agent PRs finalized; dashboard polish; README + docs + license | In progress (this phase) |
| M6 | Record ≤3 min demo video; submit |

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Sandbox concurrency cap (50 simultaneous ops) hit during 4-way fork + retries | Keep checks sequential-ish where cheap (checks 1 and 4 are fast); only parallelize where it matters for the demo narrative |
| Nemotron-generated tests are themselves flaky/wrong | Cap generated-test count (3-5), require them to pass against the *original pre-patch* code first as a sanity check (if they fail on original code too, discard as invalid) |
| Judges see this as "just another test runner" | Lead every explanation with the test-tampering catch — it's the most concrete, hard-to-dismiss proof of value |
| Beta API access/rate limits on Sandboxes | Build a LocalBackend fallback (directory snapshots, no isolation) for offline development/demo rehearsal, matching the pattern other teams use for reliability |

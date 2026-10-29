# AgentAudit — 2:15 Live Pitch Script (balanced two-person cut)
### Nebius × NVIDIA Global AI Hackathon 2026

Two people, one screen, **135 seconds**. Driver speaks three times instead of once — it reads as a real pitch, not a monologue with a stagehand.

| Role | Who | Job |
|---|---|---|
| **Narrator** | your friend | reads every line marked **N** — the story |
| **Driver** | you | runs terminal + dashboard, reads lines marked **D** |

---

## Timeline

| Time | Section | Who |
|------|---------|-----|
| 0:00 – 0:15 | Hook | N |
| 0:15 – 0:27 | Reveal | N |
| 0:27 – 1:12 | Demo: bad agent | **D** opens, N narrates, **D** lands the evidence |
| 1:12 – 1:28 | Demo: good agent | **D** opens, N pays it off |
| 1:28 – 1:52 | Nebius moat | N |
| 1:52 – 2:15 | Close | N |

*Driver: 3 lines, ~15s total. Narrator: ~120s. The demo still owns the biggest block — it's the one part with an external dependency (the run finishing) and needs the slack.*

---

## Before you shoot

1. Dashboard open at `http://127.0.0.1:5173/` on **Run History**, window filling the frame.
2. Terminal open in `D:\agentaudit\engine`, font big enough to read on camera.
3. Run both scenarios once beforehand so nothing surprises you.
4. **Fixture mode during the shoot** (instant, no network risk). Do one `--live` run *before* the shoot so a real *Live Nemotron* run sits in history to point at.

---

## The script

### 0:00 – 0:15 · Hook

**N:**

> An AI agent opens a pull request. Tests green, CI green — ship it, right?
>
> Except the agent didn't fix the bug. It *edited the test* to make the bug disappear.
>
> Green checks, broken product. Nobody's checking the agent.

---

### 0:15 – 0:27 · Reveal

**N:**

> AgentAudit is the trust layer for AI coding agents. Any patch in, four independent checks out — every one backed by evidence.

**D:**

> Watch it run.

---

### 0:27 – 1:12 · Demo — the cheating agent

**D:** *(framing, then run)*

> Here's a patch an AI agent actually wrote. Let's put it through the audit.
>
> ```
> python engine/run_demo.py bad-agent-patch
> ```

**N:** *(as it prints)*

> Fresh clone, agent's diff applied, four checks running.

**N:**

> **Test Tampering** — no model, caught instantly. The agent flipped an expected value from ninety to a hundred instead of fixing the code. Cheating, flagged.

**N:**

> **Blind-Spot Coverage** — Nemotron, NVIDIA's 120-billion-parameter model on Nebius Token Factory, reads the ticket and writes brand-new tests the suite never had. Two fail. The patch can't pass tests it never saw.

**N:**

> **Description Match** — PR says "fixes the boundary bug." Diff edits the test file, not the source. Mismatch.

**D:** *(point at verdict, switch to dashboard, open the run, expand one check)*

> And that verdict isn't a summary — every number on this screen traces back to that run. Open any check, get the exact diff behind it.

---

### 1:12 – 1:28 · Demo — the honest agent

**D:** *(framing, then run)*

> Now the control — a patch that did the right thing.
>
> ```
> python engine/run_demo.py good-agent-patch
> ```

**N:**

> Same four checks: fixes the source, touches no tests, all green. **VERIFIED.** It doesn't just hate patches — it knows the difference.

---

### 1:28 – 1:52 · Nebius moat

**N:**

> Two reasons this runs on Nebius — and they're load-bearing.
>
> **Inference:** real Nemotron 3 Super through Token Factory's OpenAI-compatible endpoint — blind spots found by a frontier model, not a regex.
>
> **Sandboxes:** every check in an isolated ephemeral container off a fresh clone. No state leaking between runs, instant rollback. That's the line between a demo and infrastructure.

---

### 1:52 – 2:15 · Close

**N:**

> Agents write more of our code every day. The gap between "tests pass" and "it actually works" is where outages live.
>
> AgentAudit closes it — evidence-backed verdicts, every time.
>
> Trust, but verify. **AgentAudit.**

---

## Contingency — never go silent

- **Terminal stalls:** **D** — *"While that runs — the dashboard behind me already has every run recorded, let me open one."* → click into Run History.
- **Dashboard won't load:** **D** — *"The dashboard's just a view onto the same verdict data — the evidence is complete here in the terminal."* → finish in terminal.
- **Blank on a check name:** Test Tampering, Baseline Regression, Blind-Spot Coverage, Description Match — **T, R, B, D**.
- **"What if the model hallucinates a test?"** — *"Check B runs generated tests in a sandbox and reports real pass/fail — the model proposes, the sandbox disposes. Check T is deliberately model-free, so tampering detection can't hallucinate."*
- **"Only catches bad agents?"** — *"No — good-agent comes back VERIFIED, all four green. It discriminates."*
- **"Live or canned?"** — *"Both ship. Fixture replay for demos, one flag flips Checks B and D to real Nemotron calls. This run is [fixture / live]."* — say whichever is true.

---

## Scenarios (names exactly)

| Scenario | Outcome |
|---|---|
| `bad-agent-patch` | FLAGGED — edits an assertion |
| `good-agent-patch` | VERIFIED — fixes source, no test edits |
| `bad-agent-delete-test` | FLAGGED — deletes failing test |
| `bad-agent-skip-test` | FLAGGED — `@pytest.mark.skip`s failing test |
| `bad-agent-weaken-comparison` | FLAGGED — flips `==` to `!=` |

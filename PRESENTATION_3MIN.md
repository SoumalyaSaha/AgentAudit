# AgentAudit — 3-Minute Live Pitch Script
### Nebius × NVIDIA Global AI Hackathon 2026 — Coding & Agentic Engineering Track

Two people, one screen, 180 seconds.

| Role | Who | Job |
|---|---|---|
| **Narrator** | your friend | tells the story, reads every line marked **N** |
| **Driver** | you | operates the terminal + dashboard, reads lines marked **D** |

Rehearse it twice out loud with a timer before you shoot. Every second below is a target, not a guideline — the demo section is the part that can't be rushed.

---

## Timeline at a glance

| Time | Section | Who |
|------|---------|-----|
| 0:00 – 0:18 | The Hook | N |
| 0:18 – 0:35 | The Reveal | N |
| 0:35 – 1:35 | **Live demo — bad agent** | D drives, N narrates |
| 1:35 – 1:55 | **Live demo — good agent** | D drives, N narrates |
| 1:55 – 2:30 | The Nebius moat | N |
| 2:30 – 3:00 | Close | N |

---

## Before you go live (rehearsal checklist)

1. **Dashboard already open** at `http://127.0.0.1:5173/` on the **Run History** page, window sized so the table fills the frame.
2. **Terminal open** in `D:\agentaudit\engine`, font bumped up so the verdict lines are readable on camera.
3. **Run the demo once end-to-end before the shoot** so nothing surprises you:
   ```
   python engine/run_demo.py bad-agent-patch
   python engine/run_demo.py good-agent-patch
   ```
4. **Live vs. fixture — the one call you have to make:**
   - **Fixture mode** (default, no flag): instant, deterministic, zero network. Safest for a live shoot. The dashboard badge reads *Recorded replay*.
   - **Live mode** (`--live` flag): real Nemotron calls through Nebius Token Factory. Badge reads *Live Nemotron* and the Model card shows `nvidia/nemotron-3-super-120b-a12b`. **Costs credits** and risks a network stall on camera.
   - **Recommendation for the video:** run fixture mode *during* the shoot for reliability, and do **one `--live` run beforehand** so a genuine *Live Nemotron* run sits in history — point at it when you say the tech line. You get real-inference proof without betting the take on a network call.
5. **Have the Run Detail page pre-loaded** on a FLAGGED run as a fallback — if the terminal hiccups, you just click into the dashboard and keep talking.

---

## The script

### 0:00 – 0:18 · The Hook

**N:**

> An AI agent just opened a pull request. Your tests are green. Your CI is green. Ship it, right?
>
> Here's the problem — the agent didn't fix the bug. It *edited the test* to make the bug disappear.
>
> Green checks. Broken product. And nobody's checking the agent.

*(pause one beat — don't rush the reveal)*

---

### 0:18 – 0:35 · The Reveal

**N:**

> AgentAudit is the trust layer for AI coding agents. Drop in any agent patch, and four independent checks grade it — and every single check shows its evidence.
>
> Let me show you one running live.

---

### 0:35 – 1:35 · Live demo — the cheating agent

**D:** In the terminal, run:

```
python engine/run_demo.py bad-agent-patch
```

*(let the output scroll for ~3 seconds while N speaks)*

**N:**

> Watch — AgentAudit clones the repo fresh, applies the agent's diff, and runs four checks.

**D:** Point at the **T** result line as it prints.

**N:**

> **Test Tampering** — static analysis, no model, caught it instantly. The agent edited the expected value in an existing assertion — ninety becomes a hundred. That's not a fix, that's cheating, and it's flagged on the spot.

**D:** Point at the **B** result.

**N:**

> **Blind-Spot Coverage** — this is where it gets interesting. Nemotron — NVIDIA's Nemotron 3 Super, running on Nebius Token Factory — reads the ticket and the diff, then writes *brand-new* tests the original suite never had.
>
> Two of them fail. The agent's patch doesn't just cheat the old tests — it can't pass new ones either.

**D:** Point at the **D** result.

**N:**

> **Description Match.** The PR claims it "fixes the boundary bug." The diff edits the test file, not the source. Mismatch — flagged.

**D:** Point at the final verdict line.

**N:**

> **Verdict: FLAGGED.** Not a vibe — a lab report, line by line.

*(switch to the dashboard, click into the FLAGGED run's detail, expand one check to show the diff evidence)*

**D:**

> Every number here comes from that run — you can open any check and see the exact diff and the pytest output behind the verdict.

*(~5 seconds on the dashboard — let the visual land)*

---

### 1:35 – 1:55 · The honest agent

**D:** Back to the terminal:

```
python engine/run_demo.py good-agent-patch
```

**N:**

> Now an honest agent — fixes the actual comparison, touches no tests. Same four checks.
>
> All pass. **VERIFIED.**
>
> AgentAudit doesn't just hate patches. It knows the difference.

---

### 1:55 – 2:30 · The Nebius moat

**N:**

> Why Nebius? Two reasons — and they're load-bearing, not decoration.
>
> **One — inference.** Nemotron 3 Super, 120 billion parameters, through Nebius Token Factory's OpenAI-compatible endpoint. Blind-spot tests come from a real frontier model, not a regex.
>
> **Two — Sandboxes.** Every check runs in a real, isolated, ephemeral container off a fresh clone. No "works on my machine." No state leaking between runs. Instant rollback. That's the difference between a demo and infrastructure.

*(if you did the pre-run `--live` job: point at the dashboard's Model card showing `nvidia/nemotron-3-super-120b-a12b` and the Live Nemotron badge)*

---

### 2:30 – 3:00 · Close

**N:**

> AI agents are writing more of our code every day — and the gap between "tests pass" and "it actually works" is exactly where outages live.
>
> AgentAudit closes it. Evidence-backed verdicts, every time.
>
> Trust, but verify. **AgentAudit.**

---

## Contingency lines (memorize these)

If something stalls, keep talking — never go silent on camera:

- **Terminal is slow / hangs:** *"While that runs, notice the dashboard behind me — every run's already recorded there, and you can inspect any one of them."* → click into Run History, open a run.
- **Dashboard doesn't load:** *"The dashboard's just a view onto the same verdict data — let me stay in the terminal where the evidence is."* → finish in the terminal, the printed evidence is complete on its own.
- **You blank a check name:** the four are **Test Tampering, Baseline Regression, Blind-Spot Coverage, Description Match** — T, R, B, D.
- **Asked "what if the model hallucinates a test?":** *"Check B runs the generated tests in a sandbox and reports pass/fail against real execution — the model proposes, the sandbox disposes. And Check T is deliberately model-free so tampering detection can't hallucinate at all."*
- **Asked "does it only catch bad agents?":** *"No — the good-agent scenario returns VERIFIED with all four green. It discriminates."*
- **Asked "live model or canned?":** *"Both paths ship. Fixture mode is the deterministic replay for demos; flip one flag and Checks B and D make real Nemotron calls through Token Factory. This run is [fixture / live]."* — say whichever is true.

---

## The five scenarios (say their names exactly if asked)

| Scenario | Outcome |
|---|---|
| `bad-agent-patch` | FLAGGED — edits an existing assertion |
| `good-agent-patch` | VERIFIED — fixes the source, touches no tests |
| `bad-agent-delete-test` | FLAGGED — deletes the failing test outright |
| `bad-agent-skip-test` | FLAGGED — `@pytest.mark.skip`s the failing test |
| `bad-agent-weaken-comparison` | FLAGGED — flips `==` to `!=` so the bug passes |

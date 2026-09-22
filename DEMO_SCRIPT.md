# DEMO_SCRIPT.md — shot-by-shot recording script

**Total target length: 2:40 (leaves 20s buffer under the 3:00 hard limit)**

Run **everything from the repo root** (`agentaudit/`, the folder
containing `demo_repo/`, `patches/`, `engine/`). Every command below was
executed for real, from that directory, before being written down here
— none of it is guessed. Terminal font size large enough to read on a
1080p recording (16pt+ recommended). Close notifications.

---

### Shot 1 — The problem (0:00–0:20, talking head or slide, no terminal)

> "This hackathon has dozens of coding agents that patch bugs and open
> pull requests once their tests go green. But 'tests are green' isn't
> the same as 'the bug is fixed' — an agent can make tests pass by
> editing the tests instead of the code. AgentAudit is the check that
> catches that."

---

### Shot 2 — The ticket and the bug (0:20–0:35, terminal)

```
cat demo_repo/TICKET.md
```

> "Here's a real ticket: a discount calculator has an off-by-one bug at
> the 10-unit boundary. We gave this ticket to two different coding
> agents."

---

### Shot 3 — The cheating agent's PR (0:35–0:55, terminal)

```
cat patches/bad_agent.diff
```

> "Agent one's diff. Look closely — it doesn't touch the discount
> logic at all. It just changed the test's expected value from 90 to
> 100, so the test agrees with the bug instead of the bug getting
> fixed. And its test suite passes."

```
rm -rf /tmp/bad_check && cp -r demo_repo /tmp/bad_check
cd /tmp/bad_check && git apply "$OLDPWD/patches/bad_agent.diff" && python3 -m pytest -q
cd "$OLDPWD"
```

> "Green. Every other tool in this hackathon would ship this PR."

---

### Shot 4 — AgentAudit catches it (0:55–1:35, terminal — THE key moment)

```
python3 engine/run_demo.py bad-agent-patch
```

> "AgentAudit re-verifies from a clean forked sandbox. Check one:
> caught it immediately — an existing assertion was modified, not a
> new one added. Check two: re-runs the ORIGINAL, untouched test file
> against the patch — still fails, because the real bug is still
> there. Check three: Nemotron generates a fresh test from the ticket
> itself, independent of the tampered suite — also fails. Check four:
> Nemotron reads the ticket and the diff and flags that the diff never
> touches the file the ticket is about. Four independent signals,
> same conclusion: **Flagged**, not verified."

---

### Shot 5 — The honest agent's PR (1:35–2:10, terminal)

```
cat patches/good_agent.diff
```

> "Agent two's diff: one line, in the actual discount logic, exactly
> matching the ticket."

```
python3 engine/run_demo.py good-agent-patch
```

> "Same four checks. All pass. **Verified** — with the evidence
> attached, not just a green checkmark."

---

### Shot 6 — Nebius/NVIDIA usage callout (2:10–2:30, terminal or slide)

> "Every check runs in its own forked sandbox off one shared baseline
> checkpoint, using Nebius Token Factory Sandboxes' branching API —
> so checks are isolated and never rebuild the repo from scratch.
> Checks three and four are real inference calls to NVIDIA Nemotron
> through Nebius Token Factory."

*(Optionally show `reference_output/live_capture_evidence.txt` briefly
here as proof of a real live-mode run.)*

---

### Shot 7 — Close (2:30–2:40)

> "Every agent in this hackathon can tell you tests are green.
> AgentAudit tells you whether that's actually true."

---

## Recording notes

- Practice the full run at least twice before the take that gets kept.
- Both `run_demo.py` invocations together take under 2 seconds of actual
  execution — the pacing above is about narration, not waiting on the
  terminal. Do not rush the narration to match "real time"; pause the
  scrollback and talk over the printed result.
- Shot 3's `/tmp/bad_check` directory is scratch-only, safe to `rm -rf`
  before every rehearsal so each take starts from a truly clean state
  (the command already does this itself with `rm -rf` before `cp -r`).
- If anything about live narration goes wrong, the run itself cannot fail
  differently between takes — see RECORDING_CHECKLIST.md for why.

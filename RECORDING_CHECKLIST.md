# RECORDING_CHECKLIST.md

Goal: zero chance of an on-camera failure. Everything here was chosen
because it removes a specific, real way this kind of demo goes wrong.

## Design decisions that already remove risk (nothing to do, just know why)

- **Fixture mode by default** (`AGENTAUDIT_LIVE_MODE` unset). The recorded
  take never calls a live API. No network flakiness, no rate limits, no
  variable LLM wording between takes, no risk of a slow response killing
  your pacing. Verified byte-identical output across repeated runs (see
  `reference_output/expected_output.txt`).
- **LocalBackend, not live Sandboxes, powers the recorded run.** Same
  interface as the real Nebius Sandboxes client, but filesystem-snapshot-based,
  so there's no dependency on Sandboxes API uptime/auth during recording.
  The real Sandboxes backend still exists and is used for the live-mode
  evidence capture (see below) — the submission is not "fake," it's
  "recorded reliably, proven live separately."
- **Total run time a few seconds, with no network waits.** Measured
  ~4s per scenario (~8s for `both`) on Windows; faster on Linux.
  There is no waiting on APIs, no risk of dead air, no temptation to
  cut/edit mid-command.
- **Deterministic verdicts, confirmed by direct testing**, not assumption:
  bad-agent-patch → FLAGGED on all 4 checks, good-agent-patch → VERIFIED
  on all 4 checks, reproduced identically across multiple runs and from
  a cold clone in a different directory.

## Before you record (do these once, in order)

- [ ] **1. Real fresh-git-clone test — not a folder copy.** `cp -r` does
      NOT reproduce the same environment as a real submission (see "A
      real bug this checklist already caught" below). Do the actual
      sequence:
      ```
      git init && git add -A && git commit -m "test"
      cd .. && git clone <path-to-that-repo> clone_test
      cd clone_test && python3 engine/run_demo.py both
      ```
      If it doesn't work from a real clone, it won't work for judges.
- [ ] **2. Diff the output against the golden reference.**
      `python3 engine/run_demo.py both | diff - reference_output/expected_output.txt`
      Any difference means something changed — investigate before recording.
- [ ] **3. Capture live-mode evidence separately, ahead of time.**
      ```
      export NEBIUS_API_KEY=<real key>
      export AGENTAUDIT_LIVE_MODE=true
      python3 scripts/capture_fixtures.py | tee reference_output/live_capture_evidence.txt
      ```
      Do this ONCE, well before recording, not live on camera. Save the
      output file — it's your proof that Checks C/D make real Token
      Factory calls, satisfying the submission's runtime-inference
      requirement, without betting the recording on live latency.
      `unset AGENTAUDIT_LIVE_MODE` afterward so the recorded take uses
      fixture mode again.
- [ ] **4. Close everything that can pop a notification, alert, or
      auto-update dialog during recording** (Slack, email, OS updates,
      messaging apps).
- [ ] **5. Set terminal font to 16pt+, disable italic ligatures if your
      font renders `->` or `==` oddly, and confirm the window is wide
      enough that the widest line in `expected_output.txt` doesn't wrap.**
- [ ] **6. Pre-warm nothing — there's nothing to pre-warm.** No pip
      installs, no Docker pulls, no model downloads happen during the
      recorded run. Confirm `pytest` is already installed in the
      recording environment beforehand (`pip show pytest`) so shot 3
      doesn't stall.
- [ ] **7. Do two full silent dry runs of the ENTIRE script** (all 7
      shots, actually typing/pasting each command) immediately before
      the take you intend to keep, so muscle memory matches
      DEMO_SCRIPT.md exactly.
- [ ] **8. Record a local screen capture, not a live stream** — if
      something does go wrong, you re-take that one shot rather than
      losing the whole recording.
- [ ] **9. Have `reference_output/expected_output.txt` open in a second
      window during recording** as a silent reference for what the
      terminal SHOULD show, so you notice immediately if something looks
      wrong before finishing the take.

## A real bug this checklist already caught (documented so it isn't reintroduced)

Early versions of `apply_patch` used `git apply`. That silently fails in
exactly the setup this project ends up in: once the repo is committed
to git and `.agentaudit_work/` (the fork/checkpoint working directory)
lives inside it, `git apply` run from a subdirectory resolves patch
paths against the **ancestor repo's root**, not the current working
directory — so it reports success (returncode 0, no error) while
touching nothing. This was caught by testing inside an actual `git
init` + `git clone` of the full project, not just by running the demo
from an ad hoc scratch directory. Fixed by switching to `patch -p1`
(see `engine/local_backend.py` and `engine/sandbox_backend.py`), which
always resolves paths relative to cwd. **Lesson for future changes:**
any test of `run_demo.py` that only copies files around (`cp -r`)
instead of doing a real `git init && git add && git commit && git
clone` will NOT catch this class of bug — always test from an actual
git clone before trusting a "it works" result.

- [ ] If a command's output doesn't match what you rehearsed, STOP, don't
      try to explain it away live — cut, fix, re-run steps 1-2 above,
      re-take.
- [ ] Narrate over the printed result rather than the command executing —
      since execution is near-instant, there's no "watching it think"
      moment to narrate through.

## After recording, before submitting

- [ ] Re-run the fresh-clone test (step 1) one final time against the
      exact commit hash you're submitting.
- [ ] Confirm `LICENSE`, `README.md` with setup instructions, and the
      `.env.example` are all present at the repo root per Devpost rules.
- [ ] Double check the video is ≤ 3:00 and covers Token Factory + Nemotron
      usage in the narration (submission requirement, not optional).

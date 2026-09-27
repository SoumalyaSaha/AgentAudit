# patches/README.md

## Why plain `.diff` files instead of git branches

Earlier drafts of this demo used two git branches inside `demo_repo/`
(`bad-agent-patch`, `good-agent-patch`) to represent the two scripted
agents' pull requests. That meant `demo_repo/` was its own nested git
repository living inside the outer `agentaudit/` repository.

That's a real problem for a GitHub submission: when the outer repo is
committed, git either silently treats the inner repo as a submodule
(so its files never actually get pushed -- a fresh clone shows an
empty `demo_repo/` folder) or, if mishandled, gets flattened in a way
that loses the branch history entirely. Either way, the demo would
work perfectly for the one person who built it locally and break
silently for anyone else who clones the repo -- including judges.

**Fix:** `demo_repo/` is now a plain, ordinary folder (no `.git`
inside it at all). The two agents' "pull requests" are captured as
plain unified-diff files:

- `bad_agent.diff` -- the cheating agent's patch (edits the test's
  expected value instead of fixing the bug)
- `good_agent.diff` -- the honest agent's patch (fixes the actual bug)
- `bad_agent_delete_test.diff` -- deletes the whole boundary test
  function (`removed_test`)
- `bad_agent_skip_test.diff` -- adds a `@pytest.mark.skip` decorator to
  the boundary test (`skip_marker_added`)
- `bad_agent_weaken_comparison.diff` -- flips `==` to `!=` in the
  boundary assertion (`modified_comparison`)

The last three are extra scripted tampering mutations for Check A,
verified by `scripts/verify_check_a.py` (all must FAIL Check A, while
`good_agent.diff` must PASS it). They are also wired into
`engine/run_demo.py` as `bad-agent-delete-test`, `bad-agent-skip-test`,
and `bad-agent-weaken-comparison` so each can be run end-to-end; the
default `both` target still runs only the two original scenarios, so
`reference_output/expected_output.txt` is unaffected.

`engine/run_demo.py` reads whichever diff file matches the requested
scenario and applies it with `git apply` inside a forked sandbox copy
of `demo_repo/` -- `git apply` works fine against a plain directory,
it doesn't require the target to be a git repository itself (verified
directly before making this change).

This is simpler, survives a plain `git clone` with zero special
handling, and behaves identically to the branch-based version -- same
four checks, same verdicts, same evidence.

## Regenerating these patches

If you ever change `demo_repo/discount.py` or `demo_repo/test_discount.py`
and need to regenerate the patches by hand:

```bash
cd demo_repo
diff -u discount.py.orig discount.py > ../patches/good_agent.diff
diff -u test_discount.py.orig test_discount.py > ../patches/bad_agent.diff
```

Or simplest: keep a scratch copy of the base files, make your edit,
and run `diff -u <original> <edited>` -- just make sure the diff
headers use relative paths (`a/discount.py`, `b/discount.py`) matching
the format already in these files, since `git apply` expects that.

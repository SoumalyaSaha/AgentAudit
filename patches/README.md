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

"""
LocalBackend: a deterministic, offline, zero-network stand-in for the
Nebius Token Factory Sandboxes ("ConTree") API.

WHY THIS EXISTS
----------------
The submitted project uses the real Sandboxes API (see sandbox_backend.py)
for the version that satisfies the hackathon's runtime requirements.
LocalBackend exists so the SAME orchestration/check code can run against
a plain filesystem snapshot instead, with the exact same interface
(checkpoint / fork / run / read_file). This gives us:

  1. A demo recording path with zero network calls, zero API latency,
     zero rate-limit risk, and byte-identical output every single run —
     critical when you only get a few takes to record a 3-minute video.
  2. An offline dev loop while building/debugging the four checks,
     without burning Nebius credits on every iteration.
  3. A safety net: if Sandboxes has an outage or auth hiccup on demo day,
     swap one constructor call and the whole pipeline still runs.

The interface mirrors sandbox_backend.py (the real Sandboxes wrapper)
exactly, so swapping backends is a one-line change in run_demo.py.
"""

from __future__ import annotations

import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Operation:
    """Mirrors the real Sandboxes API's operation/result shape."""
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class Checkpoint:
    id: str
    path: Path


@dataclass
class Sandbox:
    id: str
    path: Path
    parent_checkpoint_id: str


class LocalBackend:
    """
    Deterministic local stand-in for Nebius Sandboxes.

    A "checkpoint" is a plain filesystem snapshot of the target repo's
    base state (see ../patches/README.md for why the demo's two agent
    "PRs" are plain diff files rather than git branches). A "fork" is
    an independent copy of a checkpoint -- cheap, isolated, and each
    fork gets its own working directory so concurrent checks never step
    on each other's files.
    """

    def __init__(self, work_root: Path):
        self.work_root = work_root
        self.work_root.mkdir(parents=True, exist_ok=True)
        self._checkpoints: dict[str, Checkpoint] = {}
        self._sandboxes: dict[str, Sandbox] = {}

    # ---- checkpoint / fork lifecycle -----------------------------------

    def create_checkpoint(self, source_dir: Path) -> Checkpoint:
        """Snapshot `source_dir` (a plain directory, not a git repo) into an isolated checkpoint dir."""
        cp_id = f"cp-{uuid.uuid4().hex[:8]}"
        cp_path = self.work_root / cp_id
        shutil.copytree(source_dir, cp_path)
        cp = Checkpoint(id=cp_id, path=cp_path)
        self._checkpoints[cp_id] = cp
        return cp

    def fork(self, checkpoint_id: str) -> Sandbox:
        """Create an isolated, independently-runnable copy of a checkpoint."""
        cp = self._checkpoints[checkpoint_id]
        sb_id = f"sb-{uuid.uuid4().hex[:8]}"
        sb_path = self.work_root / sb_id
        # Full copy so each fork has its own independent files, safe for
        # `git apply` without touching sibling forks.
        shutil.copytree(cp.path, sb_path)
        sb = Sandbox(id=sb_id, path=sb_path, parent_checkpoint_id=checkpoint_id)
        self._sandboxes[sb_id] = sb
        return sb

    def backtrack(self, sandbox_id: str) -> Sandbox:
        """Discard a sandbox and re-fork a clean copy from its parent checkpoint."""
        sb = self._sandboxes[sandbox_id]
        shutil.rmtree(sb.path, ignore_errors=True)
        del self._sandboxes[sandbox_id]
        return self.fork(sb.parent_checkpoint_id)

    # ---- execution -------------------------------------------------------

    def apply_patch(self, sandbox_id: str, patch_text: str) -> Operation:
        """
        Apply a unified diff to a sandbox's files.

        Uses the POSIX `patch` command rather than `git apply` deliberately:
        `git apply` silently resolves patch paths relative to the nearest
        ANCESTOR git repository's root (not the current working directory)
        whenever it's run inside a subdirectory of any git repo -- which is
        exactly the situation once this whole project is committed to git
        and .agentaudit_work/ sits inside it. That causes `git apply` to
        report success (returncode 0) while silently touching nothing,
        which is a much worse failure mode than an honest error. Verified
        directly: reproduced the silent no-op inside a nested git repo,
        confirmed `patch -p1` is immune to it (paths are always resolved
        relative to cwd, with no ambient-repo path magic).
        """
        sb = self._sandboxes[sandbox_id]
        patch_path = sb.path / "_incoming.patch"
        patch_path.write_text(patch_text)
        proc = subprocess.run(
            ["patch", "-p1", "-i", str(patch_path)],
            cwd=sb.path,
            capture_output=True,
            text=True,
        )
        patch_path.unlink(missing_ok=True)
        return Operation(proc.returncode, proc.stdout, proc.stderr)

    def run(self, sandbox_id: str, command: list[str]) -> Operation:
        sb = self._sandboxes[sandbox_id]
        proc = subprocess.run(command, cwd=sb.path, capture_output=True, text=True)
        return Operation(proc.returncode, proc.stdout, proc.stderr)

    def read_file(self, sandbox_id: str, rel_path: str) -> str:
        sb = self._sandboxes[sandbox_id]
        return (sb.path / rel_path).read_text()

    # ---- cleanup ----------------------------------------------------------

    def cleanup(self) -> None:
        shutil.rmtree(self.work_root, ignore_errors=True)

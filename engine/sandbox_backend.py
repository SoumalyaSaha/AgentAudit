"""
SandboxBackend: real Nebius Sandboxes ("ConTree") client, matching
LocalBackend's interface (checkpoint / fork / apply_patch / run /
read_file / cleanup) so run_demo.py can swap backends with a flag:

    python engine/run_demo.py both --backend sandbox

Written against `contree-sdk` 0.3.6 (pip install contree-sdk), inspected
offline via its installed source -- NOT yet verified against a live
Sandboxes account.

VERIFICATION STATUS (updated 2026-10-14): LIVE-VERIFIED against a
Sandboxes-enabled account (all token permissions True). Smoke test passes
(checkpoint/fork/echo ok); full `run_demo.py both --backend sandbox`
passes with correct verdicts (bad-agent-patch FLAGGED on all 4 checks,
good-agent-patch VERIFIED on all 4). Two SDK behaviors found live and
coded around (see create_checkpoint/_finish docstrings):
1. run() only prepares; .wait() executes and returns the post-execution
   image -- the prepared handle must never be reused for reads/tags.
2. popen()...communicate() consumes its originating handle (uuid resets
   to None), so stateful steps use run().wait() exclusively; fork ids
   are local unique keys since fresh handles start with uuid None.
Observed latency: checkpoint ~8s, trivial run ~1.5s, full both-scenarios
run ~66s vs ~8s local -- recording stays on LocalBackend for
reliability, live Sandboxes as proven backup.

It is NOT used for the recorded demo video itself -- see fixtures.py for
why the recording uses LocalBackend instead.

Auth: default IAMAuth reads NEBIUS_API_KEY / NEBIUS_PROJECT_ID from the
environment and targets https://api.tokenfactory.nebius.com/sandboxes/
(the same Token Factory account -- Sandboxes is a separate product
permission on that account, confirmed working for Token Factory alone
does NOT imply Sandboxes access).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path

try:
    from contree_sdk import ContreeSync as _ContreeClient
except ImportError:  # pragma: no cover - only hit if contree-sdk isn't installed
    _ContreeClient = None

# Base image sessions start from. Must provide python3 + pytest after the
# setup step below (pip install pytest). UNVERIFIED: whether this exact
# ref resolves in the Sandboxes image registry -- `images.use()` resolves
# lazily without importing, so a bad ref fails late, at first use.
BASE_IMAGE_REF = os.environ.get("AGENTAUDIT_SANDBOX_IMAGE", "python:3.11")

# Working directory inside every sandbox. All patch/test paths resolve here.
REPO_DIR = "/repo"

# `popen(..., timeout=...)` ceiling per command. UNVERIFIED: exact kwarg
# name/behavior live (surface-observed only).
RUN_TIMEOUT_SECS = float(os.environ.get("AGENTAUDIT_SANDBOX_TIMEOUT", "300"))


@dataclass
class Operation:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class Checkpoint:
    id: str  # ConTree image tag backing this checkpoint
    _session: object = field(repr=False, compare=False, default=None)


@dataclass
class Sandbox:
    id: str  # local unique key (fresh live handles start with uuid None)
    parent_checkpoint_id: str


class SandboxBackend:
    """Live-Sandboxes twin of LocalBackend.

    Checkpoint/fork maps onto ConTree's tag-based image versioning, which
    is the same capability in a different shape:
      checkpoint = build state in a session, then session.tag_as(tag)
      fork       = client.images.use(tag).session()
    """

    def __init__(self):
        if _ContreeClient is None:
            raise RuntimeError(
                "contree-sdk is not installed. Run `pip install contree-sdk` "
                "or use LocalBackend for offline/demo runs."
            )
        # Default IAMAuth resolves NEBIUS_API_KEY / NEBIUS_PROJECT_ID from
        # the environment (UNVERIFIED live: env-var lookup is per the SDK
        # config docstring, never executed here).
        self.client = _ContreeClient()
        self._checkpoints: dict[str, Checkpoint] = {}
        self._sandboxes: dict[str, object] = {}
        self._records: dict[str, Sandbox] = {}

    # ---- checkpoint / fork lifecycle -----------------------------------

    def create_checkpoint(self, source_dir: Path) -> Checkpoint:
        """Snapshot a local directory as a reusable tagged image.

        Mirrors LocalBackend.create_checkpoint(source_dir): uploads the
        tree, installs pytest, tags the state. LIVE-VERIFIED 2026-10-14.

        Lifecycle note (learned live): `run()` only *prepares*; `.wait()`
        executes and returns the post-execution image. `popen()...communicate()`
        consumes the originating handle (its uuid resets to None), so this
        backend never uses popen for stateful steps -- only run().wait(),
        whose returned object is always stored back.
        """
        cp_id = f"agentaudit-cp-{uuid.uuid4().hex[:8]}"
        session = self.client.images.use(BASE_IMAGE_REF).session()
        session = session.apply_files(self._upload_map(source_dir))
        # Execute setup AND tag atomically: _await applies req.tag to the
        # post-execution image, so no stale-handle tagging is possible.
        session = session.run(
            shell="pip install --quiet pytest",
            cwd=REPO_DIR,
            disposable=False,
            timeout=RUN_TIMEOUT_SECS,
            tag=cp_id,
        ).wait()
        cp = Checkpoint(id=cp_id, _session=session)
        self._checkpoints[cp_id] = cp
        return cp

    def fork(self, checkpoint_id: str) -> Sandbox:
        # Fresh use(tag).session() handles start with uuid None (resolved
        # lazily on first execution), so the sandbox id is a local unique
        # key -- never str(session.uuid), which would collide as "None"
        # across multiple un-executed forks.
        session = self.client.images.use(checkpoint_id).session()
        sb = Sandbox(
            id=f"sb-{uuid.uuid4().hex[:8]}", parent_checkpoint_id=checkpoint_id
        )
        self._sandboxes[sb.id] = session
        self._records[sb.id] = sb
        return sb

    def backtrack(self, sandbox_id: str) -> Sandbox:
        # The live session object carries no parent pointer, so the parent
        # checkpoint id comes from our own fork-time record.
        parent = self._records.pop(sandbox_id).parent_checkpoint_id
        self._sandboxes.pop(sandbox_id, None)
        return self.fork(parent)

    # ---- execution -------------------------------------------------------

    def apply_patch(self, sandbox_id: str, patch_text: str) -> Operation:
        """Apply a unified diff inside the sandbox.

        Uses `patch -p1`, not `git apply` -- see local_backend.py's
        apply_patch docstring for why: git apply silently no-ops when run
        inside a subdirectory of an ambient git repo.
        """
        session = self._sandboxes[sandbox_id]
        session = session.apply_files(
            {f"{REPO_DIR}/_incoming.patch": patch_text.encode("utf-8")}
        )
        self._sandboxes[sandbox_id] = session
        return self._exec(
            sandbox_id, shell="patch -p1 -i _incoming.patch"
        )

    def run(self, sandbox_id: str, command: list[str]) -> Operation:
        session = self._sandboxes[sandbox_id]
        # checks.py passes ["python3", ...]; the base image provides
        # python3 (LIVE-VERIFIED 2026-10-14: python:3.11 image runs it).
        prepared = session.run(
            command[0],
            args=command[1:],
            cwd=REPO_DIR,
            disposable=False,
            timeout=RUN_TIMEOUT_SECS,
        )
        return self._finish(sandbox_id, prepared)

    def write_file(self, sandbox_id: str, rel_path: str, content: str) -> None:
        """Overwrite/create a file inside the sandbox (backend-agnostic
        twin of LocalBackend.write_file, used by checks that inject or
        restore test files without touching LocalBackend privates)."""
        session = self._sandboxes[sandbox_id]
        session = session.apply_files(
            {f"{REPO_DIR}/{rel_path}": content.encode("utf-8")}
        )
        self._sandboxes[sandbox_id] = session

    def _exec(self, sandbox_id: str, shell: str) -> Operation:
        session = self._sandboxes[sandbox_id]
        prepared = session.run(
            shell=shell,
            cwd=REPO_DIR,
            disposable=False,
            timeout=RUN_TIMEOUT_SECS,
        )
        return self._finish(sandbox_id, prepared)

    def _finish(self, sandbox_id: str, prepared) -> Operation:
        # wait() executes and returns the POST-execution image: store it
        # back, since the pre-execution handle must not be reused.
        executed = prepared.wait()
        self._sandboxes[sandbox_id] = executed
        stdout, stderr = executed.stdout, executed.stderr
        if isinstance(stdout, (bytes, bytearray)):
            stdout = bytes(stdout).decode("utf-8", errors="replace")
        if isinstance(stderr, (bytes, bytearray)):
            stderr = bytes(stderr).decode("utf-8", errors="replace")
        return Operation(executed.exit_code, str(stdout or ""), str(stderr or ""))

    def read_file(self, sandbox_id: str, rel_path: str) -> str:
        session = self._sandboxes[sandbox_id]
        return bytes(session.read(f"{REPO_DIR}/{rel_path}")).decode("utf-8")

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    def _upload_map(source_dir: Path) -> dict[str, bytes]:
        """Map local tree -> {absolute image path: bytes} for apply_files."""
        mapping: dict[str, bytes] = {}
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                mapping[f"{REPO_DIR}/{path.relative_to(source_dir).as_posix()}"] = (
                    path.read_bytes()
                )
        return mapping

    # ---- cleanup ----------------------------------------------------------

    def cleanup(self) -> None:
        # The 0.3.6 surface exposes no session terminate/close/delete API
        # (managers exist only for files and images), so there is nothing
        # to call here. Dropping our handles; any server-side expiry is
        # governed by the account, not the SDK. UNVERIFIED live.
        self._sandboxes.clear()
        self._checkpoints.clear()
        self._records.clear()

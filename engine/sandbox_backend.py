"""
SandboxBackend: real Nebius Sandboxes ("ConTree") client, matching
LocalBackend's interface (checkpoint / fork / apply_patch / run /
read_file / cleanup) so run_demo.py can swap backends with a flag:

    python engine/run_demo.py both --backend sandbox

Written against `contree-sdk` 0.3.6 (pip install contree-sdk), inspected
offline via its installed source -- NOT yet verified against a live
Sandboxes account.

VERIFICATION STATUS (updated 2026-09-27): UNVERIFIED LIVE. Every call
below matches a real method observed on the installed 0.3.6 classes, but
no live account/credentials were available in this environment, so the
end-to-end sequence (auth -> use image -> session -> tag/fork -> popen)
has never been executed. Before depending on it:
  1. export NEBIUS_API_KEY + NEBIUS_PROJECT_ID (Sandboxes-enabled account)
  2. python scripts/smoke_sandbox.py   (echo hello through checkpoint/fork)
  3. python engine/run_demo.py both --backend sandbox

It is NOT used for the recorded demo video itself -- see fixtures.py and
RECORDING_CHECKLIST.md for why the recording uses LocalBackend instead.

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
    id: str  # str(session uuid)
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
        tree, installs pytest, tags the state. UNVERIFIED live.
        """
        cp_id = f"agentaudit-cp-{uuid.uuid4().hex[:8]}"
        image = self.client.images.use(BASE_IMAGE_REF)
        session = image.session()
        session = session.apply_files(self._upload_map(source_dir))
        setup = session.popen(
            args=["sh", "-c", "pip install --quiet pytest"],
            cwd=REPO_DIR,
            text=True,
            timeout=RUN_TIMEOUT_SECS,
        )
        setup.communicate()
        session = session.tag_as(cp_id)
        cp = Checkpoint(id=cp_id, _session=session)
        self._checkpoints[cp_id] = cp
        return cp

    def fork(self, checkpoint_id: str) -> Sandbox:
        session = self.client.images.use(checkpoint_id).session()
        sb = Sandbox(id=str(session.uuid), parent_checkpoint_id=checkpoint_id)
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
        session = session.apply_files({f"{REPO_DIR}/_incoming.patch": patch_text})
        self._sandboxes[sandbox_id] = session
        return self._popen(session, ["sh", "-c", "patch -p1 -i _incoming.patch"])

    def run(self, sandbox_id: str, command: list[str]) -> Operation:
        session = self._sandboxes[sandbox_id]
        # checks.py passes ["python3", ...]; the base image provides
        # python3 (UNVERIFIED live: exact interpreter name on the image).
        return self._popen(session, command)

    def _popen(self, session, command: list[str]) -> Operation:
        proc = session.popen(
            args=command, cwd=REPO_DIR, text=True, timeout=RUN_TIMEOUT_SECS,
        )
        out = proc.communicate()
        if isinstance(out, tuple) and len(out) == 2:
            stdout, stderr = (str(part or "") for part in out)
        else:  # UNVERIFIED: communicate() shape -- fall back to properties
            stdout, stderr = str(proc.stdout or ""), str(proc.stderr or "")
        return Operation(proc.returncode, stdout, stderr)

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

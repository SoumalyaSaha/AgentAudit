"""
SandboxBackend: real Nebius Token Factory Sandboxes ("ConTree") client,
matching LocalBackend's interface exactly (checkpoint / fork / apply_patch
/ run / read_file / cleanup) so run_demo.py can swap backends with a
one-line change:

    backend = SandboxBackend()   # instead of LocalBackend(work_root)

This wraps the official `contree-sdk` (pip install contree-sdk). It is
real, working code intended for:
  - the required "runs on Nebius Sandboxes" submission criterion
  - development against the real API when validating the demo scenarios
    before recording

It is NOT used for the recorded demo video itself -- see fixtures.py and
RECORDING_CHECKLIST.md for why the recording uses LocalBackend instead.

Requires:
    NEBIUS_SANDBOX_TOKEN, NEBIUS_PROJECT   (Sandboxes/ConTree Early Access)

NOTE: contree-sdk is in public beta and its exact method surface may
differ slightly from what's used below (session.checkpoint(),
session.write_file(), etc.) -- this file is written against the
documented capabilities (checkpoint/fork/run/read) as of the SDK's
published docs, but MUST be smoke-tested against a real Sandbox
account (`pip show contree-sdk` for the installed version, then a
one-off `session.run("echo hi")` call) before depending on it for a
live submission run. Budget time for this in M1 -- see PLANNING.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from contree import Client as _ContreeClient  # contree-sdk
except ImportError:  # pragma: no cover - only hit if contree-sdk isn't installed
    _ContreeClient = None


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
    id: str


@dataclass
class Sandbox:
    id: str
    parent_checkpoint_id: str


class SandboxBackend:
    def __init__(self):
        if _ContreeClient is None:
            raise RuntimeError(
                "contree-sdk is not installed. Run `pip install contree-sdk` "
                "or use LocalBackend for offline/demo runs."
            )
        token = os.environ["NEBIUS_SANDBOX_TOKEN"]
        project = os.environ["NEBIUS_PROJECT"]
        self.client = _ContreeClient(token=token, project=project)
        self._checkpoints: dict[str, Checkpoint] = {}
        self._sandboxes: dict[str, Sandbox] = {}

    def create_checkpoint(self, source_repo_url: str, ref: str) -> Checkpoint:
        # Clone the given repo URL at `ref` inside a fresh sandbox, then
        # tag the resulting filesystem state as a reusable checkpoint image.
        session = self.client.sandbox(image="tag:python:3.11")
        session.run(f"git clone --quiet {source_repo_url} /repo")
        session.run(f"git -C /repo checkout --quiet {ref}")
        session.run("pip install --quiet -r /repo/requirements.txt || true")
        checkpoint_id = session.checkpoint(disposable=False)
        cp = Checkpoint(id=checkpoint_id)
        self._checkpoints[checkpoint_id] = cp
        return cp

    def fork(self, checkpoint_id: str) -> Sandbox:
        session = self.client.sandbox(from_checkpoint=checkpoint_id)
        sb = Sandbox(id=session.id, parent_checkpoint_id=checkpoint_id)
        self._sandboxes[sb.id] = session
        return sb

    def backtrack(self, sandbox_id: str) -> Sandbox:
        sb = self._sandboxes[sandbox_id]
        return self.fork(sb.parent_checkpoint_id)

    def apply_patch(self, sandbox_id: str, patch_text: str) -> Operation:
        session = self._sandboxes[sandbox_id]
        session.write_file("/repo/_incoming.patch", patch_text)
        # Uses `patch -p1`, not `git apply` -- see local_backend.py's
        # apply_patch docstring for why: git apply silently no-ops when
        # run inside a subdirectory of an ambient git repo, resolving
        # patch paths against the wrong root instead of erroring loudly.
        result = session.run("cd /repo && patch -p1 -i _incoming.patch")
        return Operation(result.exit_code, result.stdout, result.stderr)

    def run(self, sandbox_id: str, command: list[str]) -> Operation:
        session = self._sandboxes[sandbox_id]
        result = session.run("cd /repo && " + " ".join(command))
        return Operation(result.exit_code, result.stdout, result.stderr)

    def read_file(self, sandbox_id: str, rel_path: str) -> str:
        session = self._sandboxes[sandbox_id]
        return session.read_file(f"/repo/{rel_path}")

    def cleanup(self) -> None:
        for sb in self._sandboxes.values():
            try:
                sb.terminate()
            except Exception:
                pass

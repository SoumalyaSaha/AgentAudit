#!/usr/bin/env python3
"""
Local audit runner for the dashboard's "New Audit" page.

Binds to 127.0.0.1 ONLY by default. Exposes a single run endpoint that
executes the four AgentAudit checks against the local demo repo and
streams per-check progress + durations back to the browser.

Safety properties (deliberate):
  - LOCAL BY DEFAULT. Binding anywhere else requires AGENTAUDIT_ALLOW_PUBLIC=1,
    and a public bind additionally requires an explicit CORS allowlist. No
    Nebius Sandboxes option, no live Nemotron toggle, no API key handling of
    any kind. Checks C/D replay the recorded fixtures in engine/fixtures.py.
  - Pasted diffs are applied to a THROWAWAY copy of the demo repo
    (.agentaudit_work/custom-*) that is deleted when the run finishes.
  - On a PUBLIC bind, only the five built-in scenarios are accepted. Pasted
    diffs execute whatever test code they contain, which is safe on loopback
    (your own machine) but is arbitrary code execution from strangers once the
    port is exposed -- so it stays local unless AGENTAUDIT_ALLOW_CUSTOM=1.
    Hosted mode also applies a per-IP cooldown, a single-run lock, a body cap,
    and a per-run timeout (AGENTAUDIT_RUN_TIMEOUT, default 180s).
  - Completed runs are appended to dashboard/data/run_history.json. That file
    lives on the host's disk: on an ephemeral host (Render free tier) runs
    survive until the instance is redeployed or restarted.

Usage:
    python scripts/audit_server.py            # 127.0.0.1:8765
    python scripts/audit_server.py --port 9000
    # Public (Render-style) -- deliberately opt-in:
    AGENTAUDIT_ALLOW_PUBLIC=1 AGENTAUDIT_ALLOWED_ORIGINS=https://<user>.github.io \
        PORT=10000 python scripts/audit_server.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "engine"))

# Deployment knobs (all optional; local behaviour is unchanged without them).
#
#   PORT                    Render/Heroku-style hosts inject this. Default 8765.
#   AGENTAUDIT_ALLOW_PUBLIC Must be "1" to bind anywhere other than loopback.
#                           This is deliberately opt-in: the historical
#                           guarantee has been "refuses to bind publicly".
#   AGENTAUDIT_ALLOWED_ORIGINS
#                           Comma-separated browser origins permitted by CORS.
#                           Defaults to the local Vite dev server only.
#   AGENTAUDIT_MAX_BODY     Max request body in bytes (default 1 MiB).
#   AGENTAUDIT_COOLDOWN     Min seconds between runs per client IP (default 5).
#   AGENTAUDIT_RUN_TIMEOUT  Max seconds one audit may run on a PUBLIC bind
#                           (default 180), checked at each event boundary --
#                           it aborts the run at the next check boundary and
#                           cannot preempt an in-flight pytest. Local loopback
#                           runs are unbounded.
#   AGENTAUDIT_ALLOW_CUSTOM Set "1" to accept pasted diffs on a PUBLIC bind.
#                           Always allowed on loopback.
MAX_BODY = int(os.environ.get("AGENTAUDIT_MAX_BODY", str(1024 * 1024)))
COOLDOWN_SECONDS = float(os.environ.get("AGENTAUDIT_COOLDOWN", "5"))
RUN_TIMEOUT_SECONDS = float(os.environ.get("AGENTAUDIT_RUN_TIMEOUT", "180"))
ALLOW_PUBLIC = os.environ.get("AGENTAUDIT_ALLOW_PUBLIC", "").lower() in ("1", "true", "yes")
ALLOW_CUSTOM = os.environ.get("AGENTAUDIT_ALLOW_CUSTOM", "").lower() in ("1", "true", "yes")
# Set in main() from the address we actually bound, so the handler's policy
# follows reality rather than the request's Origin header (which is spoofable).
IS_PUBLIC = False
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "AGENTAUDIT_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if o.strip()
]

import history  # noqa: E402
import scenarios as scenario_catalog  # noqa: E402
from aggregator import aggregate  # noqa: E402
from checks import (  # noqa: E402
    check_a_test_tampering,
    check_b_baseline_regression,
    check_c_blind_spot_tests,
    check_d_description_match,
)
from local_backend import LocalBackend  # noqa: E402

# One audit at a time: each run forks and executes pytest against a throwaway
# copy, so parallel runs multiply CPU/disk cost with no benefit to a demo.
_RUN_LOCK = threading.Lock()
_LAST_RUN_AT: dict[str, float] = {}  # client IP -> monotonic timestamp
_STATE_LOCK = threading.Lock()

DEMO_REPO = REPO_ROOT / "demo_repo"
WORK_ROOT = REPO_ROOT / ".agentaudit_work"


def _now() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _ticket() -> str:
    return (DEMO_REPO / "TICKET.md").read_text(encoding="utf-8")


def _patch_for(scenario: str) -> str:
    patch_file = REPO_ROOT / "patches" / scenario_catalog.SCENARIOS[scenario]["patch"]
    return patch_file.read_text(encoding="utf-8")


def run_audit(scenario: str, diff_text: str | None, ticket_text: str | None):
    """Yield progress events, then a final result event.

    `scenario` is one of the five known scenarios, or "custom-patch" for
    a pasted diff. Pasted diffs get their own throwaway work root.
    """
    custom = scenario == "custom-patch"
    work_root = WORK_ROOT / (f"custom-{uuid.uuid4().hex[:8]}" if custom else scenario)
    backend = LocalBackend(work_root)
    started = time.perf_counter()
    run_id = history.new_run_id()

    try:
        base_cp = backend.create_checkpoint(DEMO_REPO)
        patch = diff_text if custom else _patch_for(scenario)
        ticket = ticket_text if custom and ticket_text else _ticket()

        yield {"type": "started", "scenario": scenario, "run_id": run_id}

        steps = [
            ("T", "Test Tampering", lambda: check_a_test_tampering(backend, base_cp.id, patch)),
            ("R", "Baseline Regression", lambda: check_b_baseline_regression(backend, base_cp.id, patch)),
            ("B", "Blind-Spot Coverage", lambda: check_c_blind_spot_tests(backend, base_cp.id, patch, scenario, ticket)),
            ("D", "Description Match", lambda: check_d_description_match(scenario, ticket, patch)),
        ]

        results = []
        for key, name, fn in steps:
            yield {"type": "check_started", "key": key, "name": name}
            t0 = time.perf_counter()
            res = fn()
            res.duration_ms = (time.perf_counter() - t0) * 1000
            results.append(res)
            yield {
                "type": "check_done",
                "key": key,
                "name": name,
                "passed": res.passed,
                "summary": res.summary,
                "duration_ms": round(res.duration_ms, 1),
                "counts": res.counts,
            }

        verdict = aggregate(scenario, results)
        verdict.timestamp = _now()
        verdict.backend = "local"
        verdict.nemotron_mode = "fixture"
        verdict.duration_ms = (time.perf_counter() - started) * 1000
        verdict.diff_text = patch
        verdict.ticket_text = ticket
        verdict.run_id = run_id

        record = verdict.to_dict()
        history.append_run(record)
        history.write_engine_info()

        notes = []
        if custom:
            notes.append(
                "Custom diff: applied to a throwaway copy of demo_repo, which was deleted "
                "after the run."
            )
            notes.append(
                "Check D replays a recorded scenario verdict (no live model call in this "
                "local runner), so for a pasted diff it reports the recorded mismatch "
                "fixture rather than evaluating your diff."
            )

        yield {
            "type": "result",
            "verdict": verdict.status,
            "duration_ms": round(verdict.duration_ms, 1),
            "checks": record["checks"],
            "run": record,
            "notes": notes,
        }
    finally:
        backend.cleanup()
        if custom and work_root.exists():
            shutil.rmtree(work_root, ignore_errors=True)


class QuietServer(ThreadingHTTPServer):
    """ThreadingHTTPServer that ignores client-disconnect noise.

    Browsers and HTTP clients routinely drop connections mid-request
    (Vite's HMR probes, a page reload, a client cancelling a stream).
    The default handler prints a full traceback for each one, which
    buries the actual output in a local dev tool. Real errors still
    surface.
    """

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError, ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter console
        pass

    def _cors_origin(self) -> str | None:
        """Reflect the caller's Origin only when it is explicitly allowed.

        There is deliberately no wildcard: deploying publicly requires
        AGENTAUDIT_ALLOWED_ORIGINS to name the Pages/preview origin, so the
        server cannot be quietly opened to every site by accident. Non-browser
        clients (curl, tests) send no Origin and don't need CORS at all.
        """
        origin = self.headers.get("Origin")
        if not origin:
            return None
        return origin if origin in ALLOWED_ORIGINS else None

    def _cors_headers(self) -> None:
        origin = self._cors_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/scenarios"):
            self._json({
                "scenarios": [
                    {"name": name, **meta} for name, meta in scenario_catalog.SCENARIOS.items()
                ]
            })
        elif self.path.startswith("/api/runs"):
            runs = history._load(history.history_path())
            # Serve the FULL log, not a sliding window: the dashboard's Total
            # card counts the array it receives, so a [-25:] slice made the
            # counter freeze at 25 once 26+ runs existed -- and a fresh-start
            # counter that stops counting defeats its own point. The hosted
            # log resets on every deploy (ephemeral disk), so the payload
            # stays bounded in practice.
            self._json({"runs": runs, "total": len(runs)})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        if not self.path.startswith("/api/run"):
            self._json({"error": "not found"}, 404)
            return
        # 1. Reject oversized bodies on the header alone, before reading.
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._json({"error": f"body too large (max {MAX_BODY} bytes)"}, 413)
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json({"error": "invalid json"}, 400)
            return

        scenario = payload.get("scenario") or ""
        diff_text = payload.get("diff")
        ticket_text = payload.get("ticket")

        if scenario == "custom-patch":
            # Pasted diffs execute whatever test code they contain. That is the
            # whole point of the product, and it is fine on loopback (your own
            # machine), but on a public bind it hands arbitrary code execution
            # to any visitor -- so scenarios only, unless deliberately re-enabled.
            if IS_PUBLIC and not ALLOW_CUSTOM:
                self._json(
                    {
                        "error": (
                            "Paste Diff is disabled on this deployed instance; "
                            "it only runs the built-in scenarios. Run it locally "
                            "to audit your own diff (see README)."
                        )
                    },
                    403,
                )
                return
            if not diff_text or not diff_text.strip():
                self._json({"error": "a diff is required for a custom audit"}, 400)
                return
            if len(diff_text) > MAX_BODY:
                self._json({"error": f"diff too large (max {MAX_BODY} bytes)"}, 413)
                return
        elif scenario not in scenario_catalog.SCENARIOS:
            self._json({"error": f"unknown scenario: {scenario}"}, 400)
            return

        # 2. Per-IP cooldown, so a public deployment cannot be spun in a loop.
        client = self.client_address[0]
        now = time.monotonic()
        with _STATE_LOCK:
            last = _LAST_RUN_AT.get(client)
            if last is not None and (now - last) < COOLDOWN_SECONDS:
                self._json(
                    {"error": f"slow down: one audit per {COOLDOWN_SECONDS:g}s per client"},
                    429,
                )
                return

        # 3. One run at a time: each run forks and executes pytest, so parallel
        #    requests only multiply CPU/disk cost without helping anyone.
        if not _RUN_LOCK.acquire(blocking=False):
            self._json(
                {"error": "another audit is already running; try again in a moment"},
                409,
            )
            return
        with _STATE_LOCK:
            _LAST_RUN_AT[client] = time.monotonic()

        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Transfer-Encoding", "chunked")
            self._cors_headers()
            self.end_headers()

            # Hosted-mode ceiling: a runaway pytest must not pin the free-tier
            # instance forever. Local loopback runs are unbounded.
            deadline = (time.monotonic() + RUN_TIMEOUT_SECONDS) if IS_PUBLIC else None
            try:
                for event in run_audit(scenario, diff_text, ticket_text):
                    chunk = (json.dumps(event) + "\n").encode("utf-8")
                    self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                    self.wfile.write(chunk)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                    if deadline is not None and time.monotonic() > deadline:
                        raise TimeoutError(
                            f"audit exceeded {RUN_TIMEOUT_SECONDS:g}s "
                            "(hosted-mode limit)"
                        )
            except Exception as exc:  # surface failures to the UI, never crash silently
                chunk = (json.dumps({"type": "error", "error": f"{type(exc).__name__}: {exc}"}).encode("utf-8") + b"\n")
                self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        finally:
            _RUN_LOCK.release()


def main() -> None:
    # Line-buffer stdout so the startup banner (host:port, mode, guards) is
    # visible immediately in a platform's log stream instead of sitting in a
    # block buffer until exit -- hosted logs are how this gets diagnosed.
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    # Host/port resolution, deliberately explicit:
    #   AGENTAUDIT_ALLOW_PUBLIC=1  ->  0.0.0.0:$PORT   ($PORT defaults to 8765)
    #   unset (the default)        ->  127.0.0.1:8765
    # A hosted platform (Render) injects $PORT and health-probes 0.0.0.0, so a
    # loopback bind fails its port check even though the process is listening.
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT") or 8765),
        help="default: $PORT if set (Render injects one), else 8765",
    )
    ap.add_argument(
        "--host",
        default="0.0.0.0" if ALLOW_PUBLIC else "127.0.0.1",
        help="0.0.0.0 when AGENTAUDIT_ALLOW_PUBLIC=1, else 127.0.0.1",
    )
    args = ap.parse_args()

    loopback = args.host in ("127.0.0.1", "localhost")
    if not loopback and not ALLOW_PUBLIC:
        raise SystemExit(
            "refusing to bind anywhere but 127.0.0.1\n"
            "  (set AGENTAUDIT_ALLOW_PUBLIC=1 to expose this deliberately)"
        )

    global IS_PUBLIC
    IS_PUBLIC = not loopback

    # defence in depth: a public bind must be paired with an explicit CORS
    # allowlist -- the default only names the local dev server, which would
    # leave a deployed frontend unable to reach it (silently confusing), so
    # fail fast with instructions instead.
    if not loopback and not os.environ.get("AGENTAUDIT_ALLOWED_ORIGINS"):
        raise SystemExit(
            "public bind needs an explicit CORS allowlist:\n"
            "  set AGENTAUDIT_ALLOWED_ORIGINS=https://<your-github-username>.github.io"
        )

    history.write_engine_info()
    srv = QuietServer((args.host, args.port), Handler)
    scope = "loopback only" if loopback else f"PUBLIC, CORS={', '.join(ALLOWED_ORIGINS)}"
    # Always state the bound host and port plainly -- this is what a deployed
    # platform's log needs to show 0.0.0.0:<PORT> for its health probe.
    print(f"AgentAudit audit runner listening on {args.host}:{args.port}  ({scope})")
    if loopback and os.environ.get("PORT"):
        # Diagnoses the exact hosted failure ("No open ports detected on
        # 0.0.0.0, detected open ports on localhost"): $PORT is present, so this
        # is running under a platform, but the missing opt-in kept us on
        # loopback.
        print(
            "  WARNING: $PORT is set but AGENTAUDIT_ALLOW_PUBLIC is not -- "
            "binding 127.0.0.1 only. A hosted platform will fail its port "
            "check; set AGENTAUDIT_ALLOW_PUBLIC=1."
        )
    if not loopback:
        print(
            "  public mode: per-IP cooldown "
            f"{COOLDOWN_SECONDS:g}s, one run at a time, body cap {MAX_BODY}B, "
            f"run timeout {RUN_TIMEOUT_SECONDS:g}s"
        )
        print(
            "  paste-diff runs: ENABLED (AGENTAUDIT_ALLOW_CUSTOM=1)"
            if ALLOW_CUSTOM
            else "  paste-diff runs: disabled (built-in scenarios only)"
        )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()

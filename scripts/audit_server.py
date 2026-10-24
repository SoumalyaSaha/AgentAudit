#!/usr/bin/env python3
"""
Local audit runner for the dashboard's "New Audit" page.

Binds to 127.0.0.1 ONLY (never a public interface). Exposes a single
run endpoint that executes the four AgentAudit checks against the local
demo repo and streams per-check progress + durations back to the browser.

Safety properties (deliberate):
  - LOCAL BACKEND ONLY. No Nebius Sandboxes option, no live Nemotron
    toggle, no API key handling of any kind. Checks C/D replay the
    recorded fixtures in engine/fixtures.py.
  - Pasted diffs are applied to a THROWAWAY copy of the demo repo
    (.agentaudit_work/custom-*) that is deleted when the run finishes.
  - Completed runs are appended to dashboard/data/run_history.json.

Usage:
    python scripts/audit_server.py            # 127.0.0.1:8765
    python scripts/audit_server.py --port 9000
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "engine"))

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

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5173")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5173")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
            self._json({"runs": runs[-25:], "total": len(runs)})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        if not self.path.startswith("/api/run"):
            self._json({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json({"error": "invalid json"}, 400)
            return

        scenario = payload.get("scenario") or ""
        diff_text = payload.get("diff")
        ticket_text = payload.get("ticket")

        if scenario == "custom-patch":
            if not diff_text or not diff_text.strip():
                self._json({"error": "a diff is required for a custom audit"}, 400)
                return
        elif scenario not in scenario_catalog.SCENARIOS:
            self._json({"error": f"unknown scenario: {scenario}"}, 400)
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5173")
        self.end_headers()

        try:
            for event in run_audit(scenario, diff_text, ticket_text):
                chunk = (json.dumps(event) + "\n").encode("utf-8")
                self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
        except Exception as exc:  # surface failures to the UI, never crash silently
            chunk = (json.dumps({"type": "error", "error": f"{type(exc).__name__}: {exc}"}) + "\n").encode("utf-8")
            self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
            self.wfile.write(chunk)
            self.wfile.write(b"\r\n")
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    if args.host not in ("127.0.0.1", "localhost"):
        raise SystemExit("refusing to bind anywhere but 127.0.0.1")
    history.write_engine_info()
    srv = QuietServer((args.host, args.port), Handler)
    print(f"AgentAudit local audit runner on http://{args.host}:{args.port}  (local only)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()

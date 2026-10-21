from __future__ import annotations

from dataclasses import dataclass, field

from checks import CheckResult

# Stable short keys for the four checks, used by the dashboard's status
# strip (T/R/B/D) and the detection matrix columns.
CHECK_KEYS = {
    "Test Tampering": "T",
    "Baseline Regression": "R",
    "Blind-Spot Coverage": "B",
    "Description Match": "D",
}


@dataclass
class Verdict:
    scenario: str
    status: str  # "VERIFIED" | "FLAGGED"
    checks: list[CheckResult] = field(default_factory=list)
    # Dashboard-only metadata (never printed by render()).
    timestamp: str = ""
    backend: str = "local"       # "local" | "sandbox"
    nemotron_mode: str = "fixture"  # "fixture" | "live"
    duration_ms: float = 0.0
    diff_text: str = ""
    ticket_text: str = ""
    run_id: str = ""

    def render(self) -> str:
        lines = [f"\n{'=' * 60}", f"AgentAudit verdict for: {self.scenario}", f"{'=' * 60}"]
        for c in self.checks:
            mark = "PASS" if c.passed else "FAIL"
            lines.append(f"[{mark}] {c.name}: {c.summary}")
            for k, v in c.evidence.items():
                if isinstance(v, list):
                    for item in v:
                        lines.append(f"        {k}: {item}")
                else:
                    snippet = str(v)
                    if len(snippet) > 300:
                        snippet = snippet[:300] + "..."
                    lines.append(f"        {k}: {snippet}")
        lines.append(f"{'-' * 60}")
        lines.append(f"VERDICT: {self.status}")
        lines.append(f"{'=' * 60}\n")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """JSON-serialisable export of the full verdict (dashboard data)."""
        return {
            "id": self.run_id,
            "scenario": self.scenario,
            "verdict": self.status,
            "timestamp": self.timestamp,
            "backend": self.backend,
            "nemotron_mode": self.nemotron_mode,
            "duration_ms": round(self.duration_ms, 1),
            "diff": self.diff_text,
            "ticket": self.ticket_text,
            "checks": [
                {
                    "key": CHECK_KEYS.get(c.name, "?"),
                    "name": c.name,
                    "passed": c.passed,
                    "summary": c.summary,
                    "duration_ms": round(c.duration_ms, 1),
                    "counts": c.counts,
                    "evidence": c.evidence,
                }
                for c in self.checks
            ],
        }


def aggregate(scenario: str, checks: list[CheckResult]) -> Verdict:
    status = "VERIFIED" if all(c.passed for c in checks) else "FLAGGED"
    return Verdict(scenario=scenario, status=status, checks=checks)

from __future__ import annotations

from dataclasses import dataclass, field

from checks import CheckResult


@dataclass
class Verdict:
    scenario: str
    status: str  # "VERIFIED" | "FLAGGED"
    checks: list[CheckResult] = field(default_factory=list)

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


def aggregate(scenario: str, checks: list[CheckResult]) -> Verdict:
    status = "VERIFIED" if all(c.passed for c in checks) else "FLAGGED"
    return Verdict(scenario=scenario, status=status, checks=checks)

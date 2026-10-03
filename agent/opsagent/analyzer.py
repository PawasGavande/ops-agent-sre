"""Root-cause analysis. Heuristic engine for now (LLM added in a later PR)."""
import re

from .models import Diagnostics, RCAReport


def heuristic_rca(alert_name: str, d: Diagnostics) -> RCAReport:
    text = "\n".join([d.describe, d.logs, d.previous_logs, d.events])
    evidence: list[str] = []

    def grab(pattern: str, limit: int = 2):
        for line in text.splitlines():
            if re.search(pattern, line, re.I) and line.strip() not in evidence:
                evidence.append(line.strip()[:200])
                if len(evidence) >= limit:
                    return

    if re.search(r"OOMKilled", text):
        grab(r"OOMKilled|Last State|memory|Cache size growing")
        cause = ("Container was OOMKilled: memory usage exceeded its limit "
                 "(likely a memory leak or limit set too low).")
        fix = ("Raise resources.limits.memory as a stopgap and profile the service "
               "for unbounded growth; roll back the most recent release if it "
               "coincides with the first OOMKill.")
        conf = "high"
    elif re.search(r"connection refused|could not connect|ECONNREFUSED", text, re.I):
        grab(r"connection refused|could not connect|FATAL|exit code")
        cause = ("Application exits at startup because a dependency is unreachable "
                 "(connection refused), causing CrashLoopBackOff.")
        fix = ("Verify the dependency Service/endpoint and credentials exist; "
               "add retry/backoff on startup; roll back if config changed recently.")
        conf = "high"
    elif re.search(r"CrashLoopBackOff|Back-off restarting", text):
        grab(r"CrashLoopBackOff|Back-off|exit code|Error")
        cause = "Pod is crash-looping; logs do not show a clear single cause."
        fix = "Inspect previous container logs and recent config/image changes."
        conf = "low"
    else:
        cause = "No known failure signature found in collected telemetry."
        fix = "Collect more data (metrics, recent deploys) and investigate manually."
        conf = "low"

    if d.errors:
        evidence.append("diagnostics gaps: " + "; ".join(d.errors)[:200])
    return RCAReport(alert_name=alert_name, namespace=d.namespace, pod=d.pod,
                     root_cause=cause, evidence=evidence[:5],
                     suggested_fix=fix, confidence=conf, source="heuristic")


async def analyze(alert_name: str, d: Diagnostics) -> RCAReport:
    return heuristic_rca(alert_name, d)

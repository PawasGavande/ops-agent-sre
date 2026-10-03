import logging

from .models import RCAReport

log = logging.getLogger("opsagent")


async def notify(report: RCAReport) -> bool:
    """Placeholder sink: logs the report. Slack delivery arrives in a later PR."""
    log.info("RCA %s/%s: %s", report.namespace, report.pod, report.root_cause)
    return False

import logging

import httpx

from .config import settings
from .models import RCAReport

log = logging.getLogger("opsagent")
_EMOJI = {"high": "🔴", "medium": "🟠", "low": "🟡"}


def build_blocks(r: RCAReport) -> list[dict]:
    evidence = "\n".join(f"• `{e}`" for e in r.evidence) or "_none captured_"
    return [
        {"type": "header", "text": {"type": "plain_text",
                                    "text": f"{_EMOJI.get(r.confidence, '⚪')} {r.alert_name}"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*Pod*\n{r.namespace}/{r.pod}"},
            {"type": "mrkdwn", "text": f"*Confidence*\n{r.confidence} ({r.source})"}]},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Root cause*\n{r.root_cause}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Evidence*\n{evidence}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Suggested fix*\n{r.suggested_fix}"}},
    ]


async def notify(report: RCAReport) -> bool:
    url = settings.slack_webhook_url
    if not url:
        log.info("RCA %s/%s: %s", report.namespace, report.pod, report.root_cause)
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "text": f"RCA for {report.alert_name}: {report.root_cause}",
                "blocks": build_blocks(report)})
            resp.raise_for_status()
        return True
    except Exception as exc:
        log.warning("Slack notify failed: %s", exc)
        return False

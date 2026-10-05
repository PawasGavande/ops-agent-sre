import hmac
import logging
import os

from fastapi import FastAPI, Header, HTTPException

from . import diagnostics
from .analyzer import analyze
from .config import settings
from .models import AlertmanagerPayload
from .notifier import notify
from .remediation import propose_rollback

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("opsagent")
app = FastAPI(title="OpsAgent")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/webhook/alertmanager")
async def alertmanager(payload: AlertmanagerPayload,
                       authorization: str | None = Header(default=None)):
    token = settings.webhook_token
    if token and not hmac.compare_digest(authorization or "", f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="invalid token")

    results = []
    for alert in payload.alerts:
        if alert.status != "firing":
            continue
        ns = alert.labels.get("namespace", "")
        pod = alert.labels.get("pod", "")
        name = alert.labels.get("alertname", "unknown")
        if not ns or not pod:
            results.append({"alert": name, "skipped": "missing namespace/pod label"})
            continue
        try:
            diag = diagnostics.collect(ns, pod)
        except diagnostics.UnsafeArgument as exc:
            results.append({"alert": name, "skipped": str(exc)})
            continue
        report = await analyze(name, diag)
        outcome = await propose_rollback(report, diag.app)
        if outcome.status != "skipped" or settings.remediation_enabled:
            report.remediation = outcome.as_dict() | {"status": outcome.status}
        sent = await notify(report)
        log.info(
            "RCA alert=%s pod=%s/%s source=%s confidence=%s\n  root cause: %s\n  fix: %s\n"
            "  remediation: %s",
            name, ns, pod, report.source, report.confidence, report.root_cause,
            report.suggested_fix, report.remediation or "n/a",
        )
        results.append({"alert": name, "report": report.model_dump(), "notified": sent})
    return {"processed": len(results), "results": results}

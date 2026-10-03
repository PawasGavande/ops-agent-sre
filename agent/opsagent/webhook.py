import hmac
import logging

from fastapi import FastAPI, Header, HTTPException

from . import diagnostics
from .analyzer import analyze
from .config import settings
from .models import AlertmanagerPayload
from .notifier import notify
from .remediation import propose_rollback

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
        log.info("analyzed alert=%s pod=%s/%s source=%s", name, ns, pod, report.source)
        results.append({"alert": name, "report": report.model_dump(), "notified": sent})
    return {"processed": len(results), "results": results}

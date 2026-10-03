from typing import Any

from pydantic import BaseModel, Field


class Alert(BaseModel):
    status: str = "firing"
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: str | None = None
    fingerprint: str | None = None


class AlertmanagerPayload(BaseModel):
    """Subset of the Alertmanager webhook v4 payload."""

    status: str = "firing"
    receiver: str | None = None
    alerts: list[Alert] = Field(default_factory=list)
    commonLabels: dict[str, Any] = Field(default_factory=dict)


class Diagnostics(BaseModel):
    namespace: str
    pod: str
    logs: str = ""
    previous_logs: str = ""
    describe: str = ""
    events: str = ""
    errors: list[str] = Field(default_factory=list)


class RCAReport(BaseModel):
    alert_name: str
    namespace: str
    pod: str
    root_cause: str
    evidence: list[str] = Field(default_factory=list)
    suggested_fix: str
    confidence: str = "medium"  # low | medium | high
    source: str = "heuristic"  # heuristic | llm

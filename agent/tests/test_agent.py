import pytest
from fastapi.testclient import TestClient
from opsagent import diagnostics
from opsagent.analyzer import heuristic_rca
from opsagent.models import Diagnostics
from opsagent.webhook import app

client = TestClient(app)


def _payload(**labels):
    base = {"alertname": "KubePodCrashLooping", "namespace": "opsagent-demo",
            "pod": "faulty-app-crash-abc"}
    base.update(labels)
    return {"status": "firing", "alerts": [{"status": "firing", "labels": base}]}


def test_validate_name_rejects_flag_injection():
    for bad in ["--all-namespaces", "a b", "x;rm", "", "UPPER"]:
        with pytest.raises(diagnostics.UnsafeArgument):
            diagnostics.validate_name(bad)


def test_run_kubectl_blocks_write_verbs():
    for verb in ["delete", "apply", "exec", "patch"]:
        with pytest.raises(diagnostics.UnsafeArgument):
            diagnostics.run_kubectl([verb, "pod", "x"])


def test_heuristic_crash():
    d = Diagnostics(namespace="n", pod="p",
                    previous_logs="ERROR FATAL: could not connect to postgres (connection refused)")
    r = heuristic_rca("a", d)
    assert r.confidence == "high" and "unreachable" in r.root_cause


def test_heuristic_oom():
    d = Diagnostics(namespace="n", pod="p", describe="Last State: Terminated\n Reason: OOMKilled")
    assert "OOMKilled" in heuristic_rca("a", d).root_cause


def test_webhook_end_to_end(monkeypatch):
    monkeypatch.setattr(diagnostics, "run_kubectl",
                        lambda args: "FATAL could not connect (connection refused)")
    r = client.post("/webhook/alertmanager", json=_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["processed"] == 1
    assert body["results"][0]["report"]["confidence"] == "high"


def test_webhook_skips_bad_labels():
    r = client.post("/webhook/alertmanager", json=_payload(pod="--all"))
    assert r.json()["results"][0]["skipped"]
    r = client.post("/webhook/alertmanager", json={"alerts": [{"status": "firing", "labels": {}}]})
    assert "missing" in r.json()["results"][0]["skipped"]


def test_webhook_auth(monkeypatch):
    monkeypatch.setenv("WEBHOOK_TOKEN", "s3cret")
    assert client.post("/webhook/alertmanager", json=_payload()).status_code == 401
    monkeypatch.setattr(diagnostics, "run_kubectl", lambda a: "")
    ok = client.post("/webhook/alertmanager", json=_payload(),
                     headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200

import asyncio
import base64
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from opsagent import diagnostics, notifier, remediation
from opsagent.models import RCAReport
from opsagent.remediation import propose_rollback
from opsagent.webhook import app as fastapi_app

REPO = "PawasGavande/ops-agent-sre"
PATH = "k8s/base/faulty-app-healthy.yaml"
OLD, NEW = "mode: healthy\n", "mode: crash\n"


def b64(s):
    return base64.encodebytes(s.encode()).decode()  # GitHub returns base64 with newlines


class FakeGitHub:
    def __init__(self, commits=2, old=OLD, new=NEW, open_prs=None, fail=False):
        self.commits, self.old, self.new = commits, old, new
        self.open_prs, self.fail = open_prs or [], fail
        self.calls = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        body = json.loads(request.content) if request.content else None
        self.calls.append((method, path, body))
        if self.fail:
            return httpx.Response(500, json={"message": "boom"})
        if method == "GET" and path == f"/repos/{REPO}/commits":
            return httpx.Response(200, json=[{"sha": "c" * 40}, {"sha": "a" * 40}][: self.commits])
        if method == "GET" and path == f"/repos/{REPO}/contents/{PATH}":
            ref = request.url.params["ref"]
            return httpx.Response(200, json={
                "content": b64(self.new if ref == "main" else self.old),
                "sha": "blob-current" if ref == "main" else "blob-old"})
        if method == "GET" and path == f"/repos/{REPO}/pulls":
            return httpx.Response(200, json=self.open_prs)
        if method == "GET" and path == f"/repos/{REPO}/git/ref/heads/main":
            return httpx.Response(200, json={"object": {"sha": "headsha"}})
        if method == "POST" and path == f"/repos/{REPO}/git/refs":
            return httpx.Response(201, json={})
        if method == "PUT" and path == f"/repos/{REPO}/contents/{PATH}":
            return httpx.Response(200, json={})
        if method == "POST" and path == f"/repos/{REPO}/pulls":
            return httpx.Response(201, json={"html_url": "https://github.com/x/pull/42"})
        return httpx.Response(404, json={"message": f"unexpected {method} {path}"})

    def writes(self):
        return [c for c in self.calls if c[0] in ("POST", "PUT")]


@pytest.fixture
def gh(monkeypatch):
    monkeypatch.setenv("REMEDIATION_ENABLED", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("REMEDIATION_MODE", "pr")
    fake = FakeGitHub()

    def make(f):
        monkeypatch.setattr(remediation, "_client", lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(f.handler), base_url=remediation.API))
        return f
    make(fake)
    fake.install = make
    return fake


def report(conf="high", ns="opsagent-demo"):
    return RCAReport(alert_name="PodCrashLooping", namespace=ns, pod="p", root_cause="rc",
                     evidence=["boom line"], suggested_fix="fix", confidence=conf, source="llm")


def run(rep, app="faulty-app-healthy"):
    return asyncio.run(propose_rollback(rep, app))


def test_not_eligible_cases(gh, monkeypatch):
    assert run(report(conf="medium")).reason.startswith("confidence medium")
    assert "allowlist" in run(report(ns="prod")).reason
    monkeypatch.setenv("GITHUB_TOKEN", "")
    assert "GITHUB_TOKEN" in run(report()).reason
    monkeypatch.setenv("REMEDIATION_ENABLED", "false")
    assert run(report()).reason == "remediation disabled"
    assert gh.calls == []  # never touched GitHub


def test_missing_app_label_skips(gh):
    assert "app" in run(report(), app="").reason


def test_unsafe_app_name_is_rejected(gh):
    assert run(report(), app="../../etc").status == "error"
    assert gh.writes() == []


def test_no_previous_revision(gh):
    gh.commits = 1
    r = run(report())
    assert r.status == "skipped" and "no previous revision" in r.reason


def test_identical_content_skips(gh):
    gh.old = gh.new
    assert run(report()).status == "skipped"


def test_dry_run_makes_no_writes(gh, monkeypatch):
    monkeypatch.setenv("REMEDIATION_MODE", "dry-run")
    r = run(report())
    assert r.status == "dry-run" and r.restore_sha == "a" * 40 and r.path == PATH
    assert gh.writes() == []


def test_opens_pr_with_old_content(gh):
    r = run(report())
    assert r.status == "pr-opened" and r.pr_url == "https://github.com/x/pull/42"
    ref, put, pr = gh.writes()
    assert ref[2] == {"ref": "refs/heads/opsagent/rollback-faulty-app-healthy-aaaaaaa",
                      "sha": "headsha"}
    assert base64.b64decode(put[2]["content"]).decode() == OLD
    assert put[2]["sha"] == "blob-current" and put[2]["branch"].startswith("opsagent/rollback-")
    assert pr[2]["base"] == "main" and "Human review required" in pr[2]["body"]
    assert "boom line" in pr[2]["body"]


def test_existing_open_pr_short_circuits(gh):
    gh.open_prs = [{"head": {"ref": "opsagent/rollback-faulty-app-healthy-aaaaaaa"},
                    "html_url": "https://github.com/x/pull/7"}]
    r = run(report())
    assert r.status == "skipped" and r.pr_url.endswith("/7") and gh.writes() == []


def test_github_error_is_reported_not_raised(gh):
    gh.fail = True
    assert run(report()).status == "error"


def test_webhook_includes_remediation(gh, monkeypatch):
    monkeypatch.setenv("REMEDIATION_MODE", "dry-run")
    monkeypatch.setattr(diagnostics, "run_kubectl", lambda a: (
        "faulty-app-healthy" if any("jsonpath" in x for x in a)
        else "FATAL could not connect (connection refused)"))
    payload = {"alerts": [{"status": "firing", "labels": {
        "alertname": "PodCrashLooping", "namespace": "opsagent-demo",
        "pod": "faulty-app-healthy-x"}}]}
    body = TestClient(fastapi_app).post("/webhook/alertmanager", json=payload).json()
    rem = body["results"][0]["report"]["remediation"]
    assert rem["status"] == "dry-run" and rem["path"] == PATH


def test_slack_blocks_show_pr_link():
    rep = report()
    rep.remediation = {"status": "pr-opened", "pr_url": "https://github.com/x/pull/42"}
    assert "pull/42" in str(notifier.build_blocks(rep))
    rep.remediation = {"status": "skipped", "reason": "no previous revision"}
    assert "no previous revision" in str(notifier.build_blocks(rep))


def test_webhook_logs_rca(monkeypatch, caplog):
    import logging
    monkeypatch.setattr(diagnostics, "run_kubectl",
                        lambda a: "FATAL could not connect (connection refused)")
    payload = {"alerts": [{"status": "firing", "labels": {
        "alertname": "PodCrashLooping", "namespace": "opsagent-demo", "pod": "faulty-app-x"}}]}
    with caplog.at_level(logging.INFO, logger="opsagent"):
        TestClient(fastapi_app).post("/webhook/alertmanager", json=payload)
    assert "root cause:" in caplog.text and "faulty-app-x" in caplog.text

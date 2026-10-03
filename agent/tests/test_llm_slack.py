import asyncio

import httpx

from opsagent import analyzer, notifier
from opsagent.models import Diagnostics, RCAReport

D = Diagnostics(namespace="n", pod="p", previous_logs="connection refused")


def test_parse_llm_json_strips_fences():
    out = analyzer.parse_llm_json('```json\n{"root_cause": "x"}\n```')
    assert out == {"root_cause": "x"}


def test_prompt_wraps_untrusted_data():
    p = analyzer.build_prompt("A", D)
    assert "<previous_logs>" in p and "connection refused" in p


def test_analyze_falls_back_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = asyncio.run(analyzer.analyze("A", D))
    assert r.source == "heuristic"


def test_analyze_falls_back_on_llm_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    async def boom(*a, **k):
        raise RuntimeError("api down")
    monkeypatch.setattr(analyzer, "llm_rca", boom)
    assert asyncio.run(analyzer.analyze("A", D)).source == "heuristic"


def test_llm_rca_parses_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    def handler(request):
        return httpx.Response(200, json={"content": [{"type": "text", "text":
            '{"root_cause":"db down","evidence":["e1"],"suggested_fix":"fix","confidence":"high"}'}]})
    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(analyzer.httpx, "AsyncClient",
                        lambda **kw: real(transport=transport, **kw))
    r = asyncio.run(analyzer.llm_rca("A", D))
    assert r.source == "llm" and r.confidence == "high" and r.root_cause == "db down"


def test_slack_blocks_and_disabled_path(monkeypatch):
    rep = RCAReport(alert_name="A", namespace="n", pod="p", root_cause="rc",
                    evidence=["l1"], suggested_fix="f", confidence="high")
    blocks = notifier.build_blocks(rep)
    assert blocks[0]["type"] == "header" and "l1" in str(blocks)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    assert asyncio.run(notifier.notify(rep)) is False


def test_slack_posts(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.example/x")
    seen = {}

    def handler(request):
        seen["body"] = request.content
        return httpx.Response(200, text="ok")
    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(notifier.httpx, "AsyncClient",
                        lambda **kw: real(transport=transport, **kw))
    rep = RCAReport(alert_name="A", namespace="n", pod="p", root_cause="rc", suggested_fix="f")
    assert asyncio.run(notifier.notify(rep)) is True and b"blocks" in seen["body"]

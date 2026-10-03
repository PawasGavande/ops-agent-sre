"""Auto-remediation: open a *pull request* reverting a workload manifest to its previous version.

Safety model
  * Off unless REMEDIATION_ENABLED=true; defaults to dry-run (reports, changes nothing).
  * Only high-confidence RCAs in an allowlisted namespace are eligible.
  * The agent never merges and never touches the cluster: a human reviews the PR and
    GitOps (Argo CD) deploys it after merge.
  * Idempotent: the branch name is derived from the revision being restored, and an
    already-open PR for the same app short-circuits.
"""
import base64
import logging
from dataclasses import dataclass

import httpx

from .config import settings
from .diagnostics import validate_name
from .models import RCAReport

log = logging.getLogger("opsagent")
API = "https://api.github.com"


@dataclass
class Result:
    status: str  # skipped | dry-run | pr-opened | error
    reason: str = ""
    path: str = ""
    restore_sha: str = ""
    pr_url: str = ""

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=API,
        timeout=20,
        headers={
            "Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


def eligible(report: RCAReport, namespace: str) -> str | None:
    """Return None if eligible, otherwise the reason it is not."""
    if not settings.remediation_enabled:
        return "remediation disabled"
    if report.confidence != "high":
        return f"confidence {report.confidence} (needs high)"
    if namespace not in settings.remediation_namespaces:
        return f"namespace {namespace} not in allowlist"
    if not settings.github_token:
        return "GITHUB_TOKEN not set"
    return None


def _pr_body(report: RCAReport, path: str, current_sha: str, restore_sha: str) -> str:
    evidence = "\n".join(f"- `{e}`" for e in report.evidence) or "- (none captured)"
    return (
        f"## 🤖 Automated rollback proposed by OpsAgent\n\n"
        f"**Alert:** {report.alert_name} on `{report.namespace}/{report.pod}`  \n"
        f"**Confidence:** {report.confidence} ({report.source})\n\n"
        f"### Root cause\n{report.root_cause}\n\n### Evidence\n{evidence}\n\n"
        f"### Change\nRestores `{path}` to its content at `{restore_sha[:7]}` "
        f"(reverting the latest change, `{current_sha[:7]}`).\n\n"
        f"### Suggested fix\n{report.suggested_fix}\n\n"
        "---\n**Human review required.** OpsAgent never merges. "
        "After merge, GitOps deploys the change."
    )


async def propose_rollback(report: RCAReport, app: str) -> Result:
    skip = eligible(report, report.namespace)
    if skip:
        return Result("skipped", skip)
    if not app:
        return Result("skipped", "pod has no `app` label; cannot locate manifest")
    repo, base = settings.github_repo, settings.base_branch
    path = ""

    try:
        path = settings.manifest_path_template.format(app=validate_name(app))
        async with _client() as gh:
            commits = (await _ok(gh.get(
                f"/repos/{repo}/commits",
                params={"path": path, "sha": base, "per_page": 2}))).json()
            if len(commits) < 2:
                return Result("skipped", "no previous revision of the manifest to restore", path)
            current_sha, restore_sha = commits[0]["sha"], commits[1]["sha"]
            branch = f"opsagent/rollback-{app}-{restore_sha[:7]}"

            cur = (await _ok(gh.get(f"/repos/{repo}/contents/{path}", params={"ref": base}))).json()
            old = (await _ok(gh.get(
                f"/repos/{repo}/contents/{path}", params={"ref": restore_sha}))).json()
            if _decode(cur) == _decode(old):
                return Result("skipped", "previous revision is identical to current", path)

            prs = (await _ok(gh.get(
                f"/repos/{repo}/pulls", params={"state": "open", "per_page": 100}))).json()
            for pr in prs:
                if pr["head"]["ref"].startswith(f"opsagent/rollback-{app}-"):
                    return Result("skipped", "rollback PR already open", path, restore_sha,
                                  pr["html_url"])

            if settings.remediation_mode != "pr":
                return Result("dry-run", "would open rollback PR", path, restore_sha)

            head = (await _ok(gh.get(f"/repos/{repo}/git/ref/heads/{base}"))).json()
            await _ok(gh.post(f"/repos/{repo}/git/refs",
                              json={"ref": f"refs/heads/{branch}", "sha": head["object"]["sha"]}))
            await _ok(gh.put(f"/repos/{repo}/contents/{path}", json={
                "message": f"revert({app}): restore {path} to {restore_sha[:7]}\n\n"
                           f"Automated rollback proposed by OpsAgent "
                           f"for alert {report.alert_name}.",
                "content": old["content"].replace("\n", ""),
                "sha": cur["sha"],
                "branch": branch,
            }))
            pr = (await _ok(gh.post(f"/repos/{repo}/pulls", json={
                "title": f"revert({app}): roll back after {report.alert_name}",
                "head": branch,
                "base": base,
                "body": _pr_body(report, path, current_sha, restore_sha),
            }))).json()
            return Result("pr-opened", "rollback PR opened", path, restore_sha, pr["html_url"])
    except Exception as exc:
        log.warning("remediation failed: %s", exc)
        return Result("error", str(exc)[:200], path)


async def _ok(awaitable) -> httpx.Response:
    resp = await awaitable
    resp.raise_for_status()
    return resp


def _decode(contents: dict) -> str:
    return base64.b64decode(contents["content"]).decode()

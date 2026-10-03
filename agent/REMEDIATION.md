# Auto-rollback pull requests

When an alert arrives, the agent diagnoses it and, if allowed, **opens a pull request** that restores the
workload's manifest to its previous version. **It never merges and never changes the cluster.** A human reviews
the PR; after merge your GitOps tool (Argo CD) deploys it.

## How it decides
1. RCA confidence must be `high`, the pod's namespace must be in `REMEDIATION_NAMESPACES`.
2. It reads the pod's `app` label and maps it to a manifest (`MANIFEST_PATH_TEMPLATE`, default `k8s/base/{app}.yaml`).
3. It finds the last two commits touching that file on `main` and restores the older content.
4. If a rollback PR for that app is already open, or there is no earlier version, it does nothing and says why.

## Settings (all env vars; put them in the `opsagent-secrets` Secret)
| Variable | Default | Meaning |
|---|---|---|
| `REMEDIATION_ENABLED` | `false` | master switch |
| `REMEDIATION_MODE` | `dry-run` | `dry-run` reports only; `pr` opens real PRs |
| `GITHUB_TOKEN` | - | fine-grained PAT, **this repo only**: Contents RW + Pull requests RW |
| `GITHUB_REPO` | `PawasGavande/ops-agent-sre` | `owner/name` |
| `GITHUB_BASE_BRANCH` | `main` | |
| `REMEDIATION_NAMESPACES` | `opsagent-demo` | comma-separated allowlist |
| `MANIFEST_PATH_TEMPLATE` | `k8s/base/{app}.yaml` | |

Recommended: enable branch protection on `main` (require a PR + approval) so even a leaked token cannot push directly.

## Try it (kind demo)
1. Run with `REMEDIATION_ENABLED=true` and the default `dry-run`; check the Slack/agent output says what it *would* do.
2. Simulate a bad release: in `k8s/base/faulty-app-healthy.yaml` change `FAULT_MODE` to `"crash"`, merge to `main`
   (the cluster must be deployed from `main`, e.g. via Argo CD).
3. The healthy pod starts crash-looping, an alert fires, the agent proposes restoring the file to the previous commit.
4. Switch `REMEDIATION_MODE=pr` to get a real PR.

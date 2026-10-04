#!/usr/bin/env bash
# Build + deploy the OpsAgent agent and the Prometheus/Alertmanager stack into the kind cluster.
# Optional env: ANTHROPIC_API_KEY, SLACK_WEBHOOK_URL, WEBHOOK_TOKEN, GITHUB_TOKEN, REMEDIATION_ENABLED, REMEDIATION_MODE (stored in a k8s Secret).
set -euo pipefail
cd "$(dirname "$0")/.."
AGENT_IMAGE=opsagent/agent:0.1.0

for bin in docker kind kubectl helm; do
  command -v "$bin" >/dev/null || { echo "missing dependency: $bin" >&2; exit 1; }
done
kind get clusters | grep -qx opsagent || { echo "run 'make up' first" >&2; exit 1; }

echo ">> building and loading agent image"
docker build -t "$AGENT_IMAGE" agent
kind load docker-image "$AGENT_IMAGE" --name opsagent

echo ">> deploying agent"
kubectl apply -f k8s/agent/agent.yaml
secret_args=()
for v in ANTHROPIC_API_KEY SLACK_WEBHOOK_URL WEBHOOK_TOKEN GITHUB_TOKEN REMEDIATION_ENABLED REMEDIATION_MODE; do
  [ -n "${!v:-}" ] && secret_args+=("--from-literal=$v=${!v}")
done
if [ ${#secret_args[@]} -gt 0 ]; then
  kubectl create secret generic opsagent-secrets -n opsagent-system "${secret_args[@]}" \
    --dry-run=client -o yaml | kubectl apply -f -
  kubectl rollout restart deployment/opsagent -n opsagent-system
else
  echo "   (no secrets set: agent uses heuristic RCA and logs instead of Slack)"
fi

echo ">> installing kube-prometheus-stack"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo update >/dev/null
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f monitoring/kube-prometheus-stack-values.yaml --wait --timeout 10m

kubectl rollout status deployment/opsagent -n opsagent-system --timeout=120s
echo
echo "Done. Within ~3 minutes the crash/leak pods should raise alerts."
echo "  make agent-logs     # watch the agent's RCA output"
echo "  make alerts         # port-forward Alertmanager UI to http://localhost:9093"

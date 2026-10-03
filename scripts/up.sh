#!/usr/bin/env bash
# Create the local kind cluster, build the faulty app, load it, and deploy.
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE=opsagent/faulty-app:0.1.0

for bin in docker kind kubectl; do
  command -v "$bin" >/dev/null || { echo "missing dependency: $bin" >&2; exit 1; }
done

kind get clusters | grep -qx opsagent || kind create cluster --config scripts/kind-config.yaml
docker build -t "$IMAGE" apps/faulty-app
kind load docker-image "$IMAGE" --name opsagent
kubectl apply -k k8s/base
echo
echo "Deployed. Watch the failures appear with:"
echo "  kubectl get pods -n opsagent-demo -w"

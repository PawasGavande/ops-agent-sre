#!/usr/bin/env bash
set -euo pipefail
helm uninstall monitoring -n monitoring || true
kubectl delete -f k8s/agent/agent.yaml --ignore-not-found
kubectl delete namespace monitoring --ignore-not-found

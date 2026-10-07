#!/usr/bin/env python3
"""Validate the Alertmanager config the way Helm will actually deploy it.

kube-prometheus-stack ships a default Alertmanager config; Helm deep-merges maps from our values
file over it but REPLACES lists. A config that is valid on its own can therefore be invalid once
merged (e.g. a default route pointing at a receiver we replaced). This script reproduces that
merge, then runs `amtool check-config`. Requires amtool on PATH.
"""
import copy
import subprocess
import sys
import tempfile

import yaml

# Defaults from the kube-prometheus-stack chart (values.yaml: alertmanager.config).
CHART_DEFAULTS = yaml.safe_load("""
global: {resolve_timeout: 5m}
inhibit_rules:
  - source_matchers: ['severity = critical']
    target_matchers: ['severity =~ warning|info']
    equal: ['namespace', 'alertname']
route:
  group_by: ['namespace']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'null'
  routes:
    - receiver: 'null'
      matchers: ['alertname = "Watchdog"']
receivers:
  - name: 'null'
""")


def helm_merge(base, override):
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = helm_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def main(values_path="monitoring/kube-prometheus-stack-values.yaml"):
    user = yaml.safe_load(open(values_path))["alertmanager"]["config"]
    merged = helm_merge(CHART_DEFAULTS, user)
    with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
        yaml.safe_dump(merged, f)
    result = subprocess.run(["amtool", "check-config", f.name], capture_output=True, text=True)
    print(result.stdout + result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))

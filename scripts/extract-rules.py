#!/usr/bin/env python3
"""Extract PrometheusRule groups from the Helm values file so promtool can test them."""
import sys
import yaml

values = yaml.safe_load(open("monitoring/kube-prometheus-stack-values.yaml"))
rules = values["additionalPrometheusRulesMap"]["opsagent-demo"]
yaml.safe_dump(rules, open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/opsagent-rules.yml", "w"))

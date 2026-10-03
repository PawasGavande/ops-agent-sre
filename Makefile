.PHONY: up down status logs monitoring monitoring-down agent-logs alerts test-alert
up:      ; ./scripts/up.sh
down:    ; ./scripts/down.sh
status:  ; kubectl get pods -n opsagent-demo
logs:    ; kubectl logs -n opsagent-demo -l opsagent/fault=crash --previous --tail=50
monitoring:      ; ./scripts/monitoring-up.sh
monitoring-down: ; ./scripts/monitoring-down.sh
agent-logs:      ; kubectl logs -n opsagent-system deploy/opsagent -f
alerts:          ; kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-alertmanager 9093:9093
test-alert:      ; ./scripts/send-test-alert.sh

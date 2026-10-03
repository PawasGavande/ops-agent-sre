.PHONY: up down status logs
up:      ; ./scripts/up.sh
down:    ; ./scripts/down.sh
status:  ; kubectl get pods -n opsagent-demo
logs:    ; kubectl logs -n opsagent-demo -l opsagent/fault=crash --previous --tail=50

# 🚀 OpsAgent – Autonomous AI SRE & Kubernetes Self-Healing Engine

[![Project Board](https://img.shields.io/badge/GitHub_Project_Board-Live_Roadmap-2ea44f?style=for-the-badge&logo=github)](https://github.com/users/PawasGavande/projects/3)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS_EKS-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Python](https://img.shields.io/badge/Python_FastAPI-3776AB?style=for-the-badge&logo=python&logoColor=white)

> 📋 **[Click Here to View the Live Agile Kanban & Project Roadmap](https://github.com/users/PawasGavande/projects/3)**

## 📌 Overview
In production Kubernetes environments, engineers spend 20–45 minutes digging through pod logs and metrics when microservices crash (`CrashLoopBackOff`, `OOMKilled`). **OpsAgent** is an event-driven AI Site Reliability Engineering (SRE) agent that intercepts cluster alerts, runs automated Root Cause Analysis (RCA) on pod logs, and triggers 1-click GitOps rollbacks via Slack.

## 🏗️ Architecture Workflow
1. **Fault Detection:** Prometheus & Alertmanager monitor Kubernetes workloads and fire webhooks on pod crashes or resource spikes.
2. **Autonomous Investigation:** A Python FastAPI agent receives the alert and executes read-only `kubectl` diagnostics (`logs`, `describe`, `events`).
3. **AI Root Cause Analysis:** The agent feeds cluster telemetry to an LLM to pinpoint the exact code or configuration failure.
4. **Self-Healing / GitOps Rollback:** Posts an interactive RCA report to Slack and opens an automated Pull Request / ArgoCD rollback.

## 🗺️ Project Phases (Tracked via GitHub Projects)
- **Phase 1 (In Progress):** Local Kubernetes cluster setup + simulated faulty microservice (`CrashLoopBackOff` / memory leaks).
- **Phase 2 (Ready):** Python FastAPI Webhook + AI Log Analyzer Agent + Slack notifications.
- **Phase 3 (Backlog):** AWS EKS provisioning via Terraform, ArgoCD GitOps, and GitHub Actions CI/CD.

## 🧪 Phase 1 – Local cluster & faulty app

Prereqs: Docker, [kind](https://kind.sigs.k8s.io/), kubectl.

```bash
make up        # kind cluster + image build + deploy
make status    # expect: healthy=Running, crash=CrashLoopBackOff, leak=OOMKilled
make logs      # previous-container logs of the crashing pod
make down      # tear everything down
```

| Deployment | `FAULT_MODE` | Expected failure |
|---|---|---|
| `faulty-app-healthy` | `healthy` | none (control) |
| `faulty-app-crash` | `crash` | `CrashLoopBackOff` (exit 1 after 10s, DB connection error in logs) |
| `faulty-app-leak` | `leak` | `OOMKilled` (leaks 5 MB/s against a 64Mi limit) |

## 🤖 Phase 2 – Agent (webhook + diagnostics + RCA)

```bash
cd agent && pip install -r requirements-dev.txt && PYTHONPATH=. pytest -q
docker build -t opsagent/agent:0.1.0 agent && kind load docker-image opsagent/agent:0.1.0 --name opsagent
kubectl apply -f k8s/agent/agent.yaml
```
Point Alertmanager's webhook receiver at `http://opsagent.opsagent-system/webhook/alertmanager`.
The agent's ServiceAccount is **read-only** (get/list on pods, pod logs, events).

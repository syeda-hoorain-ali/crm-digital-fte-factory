---
id: 0100
title: Grafana Dashboard Setup and Monitoring Integration
stage: general
date: 2026-04-11
surface: agent
model: qwen3-code-plus
feature: monitoring
branch: main
user: Syeda Hoorain Ali
command: setup grafana dashboard with monitoring
labels: ["grafana", "prometheus", "monitoring", "dashboard", "kubernetes", "deployment"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - k8s/prometheus-configmap.yaml
  - k8s/prometheus-deployment.yaml
  - k8s/grafana-ini-configmap.yaml
  - k8s/grafana-configmap.yaml
  - k8s/grafana-deployment.yaml
  - k8s/crm-dashboard.json
  - scripts/deploy-k8s.sh
  - k8s/grafana-dashboard.yaml (deleted - redundant)
tests:
  - Verified dashboard UID consistency across all files
  - Verified all monitoring files exist and are valid
  - Tested Grafana home page configuration
  - Validated dashboard JSON structure (11 panels)
---

## Prompt

User requested: "can we also make a simple and quick dashboard for it too what are the steps and how much time it needed?"

Context: After completing CI/CD pipeline deployment with external access, user wanted a monitoring dashboard to visualize metrics. Backend already had Prometheus metrics instrumented.

Follow-up requests:
- "i want ui dashboard" (not API-based)
- "i want dashboard to be available at home page like localhost:3000"
- "now update the deploy k8s.sh script"
- "i want to run command to create dashboard from crm-dashboard.json file directly"

## Response snapshot

**Implementation:**

1. Deployed Prometheus with scrape config for API metrics
2. Deployed Grafana with 11-panel dashboard
3. Configured dashboard as home page (UID: crm-main-dashboard)
4. Updated deploy script with monitoring deployment steps
5. Used preferred ConfigMap command pattern

**Dashboard Panels (11 total):**
- Health Status, Webhook Requests/sec, API Latency p95
- Error Rate, Database Query Duration, Kafka Messages/sec
- Rate Limit Violations, Customers/Conversations Created
- Redis Operations/sec, Kafka Consumer Lag

**Key Fixes:**
- Metrics endpoint: /metrics/ (with trailing slash)
- Fixed dashboard UID to prevent regeneration on restart
- Home page config: Combined env var + ini file + API preferences
- Deleted redundant grafana-dashboard.yaml file

## Outcome

- ✅ Impact: Complete monitoring dashboard deployed. Accessible at localhost:3000 as home page. Deploy script updated for automated deployment.
- 🧪 Tests: Verified UID consistency, validated JSON, tested metrics flow, confirmed home page works.
- 📁 Files: Created 6 monitoring files, updated deploy script, deleted 1 redundant file.
- 🔁 Next prompts: Add alerting rules, create custom alerts for critical metrics, document monitoring setup.
- 🧠 Reflection: Home page configuration required multiple approaches. Fixed UID prevents dashboard recreation. User's ConfigMap command pattern is cleaner than YAML-embedded JSON.

## Quick Commands

```bash
# Deploy everything
./scripts/deploy-k8s.sh

# Update dashboard only
kubectl create configmap grafana-dashboard-crm \
  --from-file=crm-dashboard.json=k8s/crm-dashboard.json \
  --namespace=customer-success-fte \
  --dry-run=client -o yaml | kubectl apply -f -

# Access Grafana
kubectl port-forward service/grafana 3000:80 -n customer-success-fte
# Visit: http://localhost:3000 (login: admin/admin)
```
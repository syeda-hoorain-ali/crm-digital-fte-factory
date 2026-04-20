#!/bin/bash
set -e

# Kubernetes Deployment Script
# This script automates the deployment of the customer success FTE system to Kubernetes

# Source environment variables from backend/.env
if [ -f "backend/.env" ]; then
    set -a
    source backend/.env
    set +a
fi

echo "🚀 Starting Kubernetes deployment..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo "ℹ $1"
}

# Step 1: Validate required environment variables
print_info "Step 1: Validating environment variables..."

REQUIRED_VARS=(
    "DATABASE_URL"
    "GEMINI_API_KEY"
    "GMAIL_SERVICE_ACCOUNT_PATH"
    "TWILIO_ACCOUNT_SID"
    "TWILIO_AUTH_TOKEN"
    "TWILIO_APP_NUMBER"
    "TWILIO_WEBHOOK_SECRET"
    "INGRESS_HOSTNAME"
    "CONTAINER_REGISTRY"
    "IMAGE_TAG"
)

MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please set these variables in your .env file and run: source .env"
    exit 1
fi

# Set defaults for optional variables
export GMAIL_SUPPORT_CREDENTIALS_PATH="${GMAIL_SUPPORT_CREDENTIALS_PATH:-}"
export GMAIL_WEBHOOK_SECRET="${GMAIL_WEBHOOK_SECRET:-}"

print_success "All required environment variables are set"

# Step 2: Validate kubectl is installed and configured
print_info "Step 2: Validating kubectl..."

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed. Please install kubectl first."
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    print_error "kubectl is not configured or cluster is not accessible"
    exit 1
fi

print_success "kubectl is configured and cluster is accessible"

# Step 3: Validate manifests exist
print_info "Step 3: Validating manifest files..."

MANIFEST_FILES=(
    "k8s/namespace.yaml"
    "k8s/configmap.yaml"
    "k8s/secrets.yaml"
    "k8s/kafka-statefulset.yaml"
    "k8s/redis-deployment.yaml"
    "k8s/deployment-api.yaml"
    "k8s/deployment-worker.yaml"
    "k8s/service.yaml"
    "k8s/ingress.yaml"
    "k8s/hpa.yaml"
)

for file in "${MANIFEST_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Manifest file not found: $file"
        exit 1
    fi
done

print_success "All manifest files found"

# Step 4: Create namespace
print_info "Step 4: Creating namespace..."

kubectl apply -f k8s/namespace.yaml

print_success "Namespace created"

# Step 5: Create ConfigMap
print_info "Step 5: Creating ConfigMap..."

kubectl apply -f k8s/configmap.yaml

print_success "ConfigMap created"

# Step 6: Create Secret (with environment variable substitution)
print_info "Step 6: Creating Secret..."

# Check if secret already exists
if kubectl get secret fte-secrets -n customer-success-fte &> /dev/null; then
    print_warning "Secret already exists, skipping creation"
else
    envsubst < k8s/secrets.yaml | kubectl apply -f -
fi

print_success "Secret created"

# Step 7: Deploy Kafka
print_info "Step 7: Deploying Kafka..."

kubectl apply -f k8s/kafka-statefulset.yaml

print_success "Kafka deployment created"

# Step 8: Deploy Redis
print_info "Step 8: Deploying Redis..."

kubectl apply -f k8s/redis-deployment.yaml

print_success "Redis deployment created"

# Step 9: Wait for Kafka and Redis to be ready
print_info "Step 9: Waiting for Kafka and Redis to be ready..."

echo "Waiting for Kafka pod..."
kubectl wait --for=condition=ready pod -l app=kafka -n customer-success-fte --timeout=120s || {
    print_warning "Kafka pod not ready yet, checking status..."
    kubectl get pods -n customer-success-fte -l app=kafka
}

echo "Waiting for Redis pod..."
kubectl wait --for=condition=ready pod -l app=redis -n customer-success-fte --timeout=60s || {
    print_warning "Redis pod not ready yet, checking status..."
    kubectl get pods -n customer-success-fte -l app=redis
}

print_success "Kafka and Redis are ready"

# Step 10: Deploy API
print_info "Step 10: Deploying API..."

envsubst < k8s/deployment-api.yaml | kubectl apply -f -

print_success "API deployment created"

# Step 11: Deploy Worker
print_info "Step 11: Deploying Worker..."

envsubst < k8s/deployment-worker.yaml | kubectl apply -f -

print_success "Worker deployment created"

# Step 12: Create Service
print_info "Step 12: Creating Service..."

kubectl apply -f k8s/service.yaml

print_success "Service created"

# Step 13: Create Ingress
print_info "Step 13: Creating Ingress..."

envsubst < k8s/ingress.yaml | kubectl apply -f -

print_success "Ingress created"

# Step 14: Create HorizontalPodAutoscalers
print_info "Step 14: Creating HorizontalPodAutoscalers..."

kubectl apply -f k8s/hpa.yaml

print_success "HorizontalPodAutoscalers created"

# Step 14a: Deploy Prometheus
print_info "Step 14a: Deploying Prometheus..."

kubectl apply -f k8s/prometheus-configmap.yaml
kubectl apply -f k8s/prometheus-deployment.yaml

print_success "Prometheus deployment created"

# Step 14b: Deploy Grafana
print_info "Step 14b: Deploying Grafana..."

# Create Grafana configuration
kubectl apply -f k8s/grafana-ini-configmap.yaml
kubectl apply -f k8s/grafana-configmap.yaml

# Create Grafana dashboard from JSON file (using preferred pattern)
kubectl create configmap grafana-dashboard-crm \
  --from-file=crm-dashboard.json=k8s/crm-dashboard.json \
  --namespace=customer-success-fte \
  --dry-run=client -o yaml | kubectl apply -f -

# Deploy Grafana
kubectl apply -f k8s/grafana-deployment.yaml

print_success "Grafana deployment created"

# Step 14c: Wait for monitoring stack to be ready
print_info "Step 14c: Waiting for monitoring stack to be ready..."

echo "Waiting for Prometheus pod..."
kubectl wait --for=condition=ready pod -l app=prometheus -n customer-success-fte --timeout=60s || {
    print_warning "Prometheus pod not ready yet, checking status..."
    kubectl get pods -n customer-success-fte -l app=prometheus
}

echo "Waiting for Grafana pod..."
kubectl wait --for=condition=ready pod -l app=grafana -n customer-success-fte --timeout=60s || {
    print_warning "Grafana pod not ready yet, checking status..."
    kubectl get pods -n customer-success-fte -l app=grafana
}

print_success "Monitoring stack is ready"

# Step 15: Wait for pods to be ready
print_info "Step 15: Waiting for pods to be ready (this may take 2-3 minutes)..."

echo "Waiting for API pods..."
kubectl wait --for=condition=ready pod -l component=api -n customer-success-fte --timeout=180s || {
    print_warning "API pods not ready yet, checking status..."
    kubectl get pods -n customer-success-fte -l component=api
}

echo "Waiting for worker pods..."
kubectl wait --for=condition=ready pod -l component=message-processor -n customer-success-fte --timeout=180s || {
    print_warning "Worker pods not ready yet, checking status..."
    kubectl get pods -n customer-success-fte -l component=message-processor
}

print_success "Pods are ready"

# Step 16: Verify deployment
print_info "Step 16: Verifying deployment..."

echo ""
echo "=== Deployment Status ==="
kubectl get all -n customer-success-fte

echo ""
echo "=== Pod Status ==="
kubectl get pods -n customer-success-fte

echo ""
echo "=== Service Status ==="
kubectl get svc -n customer-success-fte

echo ""
echo "=== Ingress Status ==="
kubectl get ingress -n customer-success-fte

echo ""
echo "=== HPA Status ==="
kubectl get hpa -n customer-success-fte

# Step 17: Test health endpoint (internal)
print_info "Step 17: Testing health endpoint..."

# Port-forward to test health endpoint
kubectl port-forward -n customer-success-fte svc/customer-success-fte 8080:80 &
PF_PID=$!

sleep 3

if curl -s http://localhost:8080/health > /dev/null; then
    print_success "Health endpoint is responding"
else
    print_warning "Health endpoint not responding yet (may need more time)"
fi

# Kill port-forward
kill $PF_PID 2>/dev/null || true

# Step 18: Display next steps
echo ""
echo "=========================================="
print_success "Deployment complete!"
echo "=========================================="
echo ""
echo "📊 Monitoring Dashboard:"
echo "   To access Grafana dashboard, run:"
echo "   kubectl port-forward service/grafana 3000:80 -n customer-success-fte"
echo "   Then visit: http://localhost:3000"
echo "   Login: admin / admin"
echo ""
echo "📈 Prometheus:"
echo "   kubectl port-forward service/prometheus 9090:9090 -n customer-success-fte"
echo "   Then visit: http://localhost:9090"
echo ""
echo "Next steps:"
echo "1. Wait for TLS certificate to be issued (2-5 minutes):"
echo "   kubectl get certificate -n customer-success-fte fte-tls"
echo ""
echo "2. Test external access:"
echo "   curl https://$INGRESS_HOSTNAME/health"
echo ""
echo "3. Monitor pods:"
echo "   kubectl get pods -n customer-success-fte -w"
echo ""
echo "4. View logs:"
echo "   kubectl logs -n customer-success-fte -l component=api --tail=50"
echo ""
echo "5. Monitor autoscaling:"
echo "   kubectl get hpa -n customer-success-fte -w"
echo ""
echo "=========================================="

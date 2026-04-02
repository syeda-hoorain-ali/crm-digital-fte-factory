#!/bin/bash
set -e

# Kubernetes Cleanup Script
# This script removes all resources created by the deployment script

echo "🧹 Starting Kubernetes cleanup..."

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

# Confirm deletion
print_warning "This will delete ALL resources in the customer-success-fte namespace"
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    print_info "Cleanup cancelled"
    exit 0
fi

# Step 1: Delete HorizontalPodAutoscalers
print_info "Step 1: Deleting HorizontalPodAutoscalers..."

kubectl delete hpa -n customer-success-fte --all --ignore-not-found=true

print_success "HorizontalPodAutoscalers deleted"

# Step 2: Delete Ingress
print_info "Step 2: Deleting Ingress..."

kubectl delete ingress -n customer-success-fte --all --ignore-not-found=true

print_success "Ingress deleted"

# Step 3: Delete Service
print_info "Step 3: Deleting Service..."

kubectl delete service -n customer-success-fte --all --ignore-not-found=true

print_success "Service deleted"

# Step 4: Delete Deployments
print_info "Step 4: Deleting Deployments..."

kubectl delete deployment -n customer-success-fte --all --ignore-not-found=true

print_success "Deployments deleted"

# Step 5: Wait for pods to terminate
print_info "Step 5: Waiting for pods to terminate..."

kubectl wait --for=delete pod -l app=customer-success-fte -n customer-success-fte --timeout=60s || {
    print_warning "Some pods are still terminating, checking status..."
    kubectl get pods -n customer-success-fte
}

print_success "Pods terminated"

# Step 6: Delete Secret
print_info "Step 6: Deleting Secret..."

kubectl delete secret -n customer-success-fte --all --ignore-not-found=true

print_success "Secret deleted"

# Step 7: Delete ConfigMap
print_info "Step 7: Deleting ConfigMap..."

kubectl delete configmap -n customer-success-fte --all --ignore-not-found=true

print_success "ConfigMap deleted"

# Step 8: Delete Namespace
print_info "Step 8: Deleting Namespace..."

kubectl delete namespace customer-success-fte --ignore-not-found=true

print_success "Namespace deleted"

# Step 9: Verify cleanup
print_info "Step 9: Verifying cleanup..."

if kubectl get namespace customer-success-fte &> /dev/null; then
    print_warning "Namespace still exists (may be in Terminating state)"
    kubectl get namespace customer-success-fte
else
    print_success "Namespace fully deleted"
fi

echo ""
echo "=========================================="
print_success "Cleanup complete!"
echo "=========================================="
echo ""
echo "All resources have been removed from the cluster."
echo ""

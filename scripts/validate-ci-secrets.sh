#!/bin/bash

# CI/CD Secrets Validation Script
# This script helps validate that all required GitHub secrets are configured

set -e

echo "================================"
echo "🔍 CI/CD Secrets Validation"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) is not installed${NC}"
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ Not authenticated with GitHub CLI${NC}"
    echo "Run: gh auth login"
    exit 1
fi

echo -e "${GREEN}✅ GitHub CLI is installed and authenticated${NC}"
echo ""

# Required secrets
declare -A SECRETS=(
    ["DOCKERHUB_USERNAME"]="DockerHub username"
    ["DOCKERHUB_TOKEN"]="DockerHub access token"
    ["GCP_PROJECT_ID"]="GCP project ID"
    ["GCP_SA_KEY"]="GCP service account JSON key"
    ["GKE_CLUSTER_NAME"]="GKE cluster name"
    ["GKE_ZONE"]="GKE cluster zone"
    ["PRODUCTION_DATABASE_URL"]="Production database connection string"
    ["NEON_API_KEY"]="Neon API key"
    ["NEON_PROJECT_ID"]="Neon project ID"
    ["NEON_MAIN_BRANCH_ID"]="Neon main branch ID"
    ["GEMINI_API_KEY"]="Gemini API key for AI agent"
    ["GRAFANA_ADMIN_PASSWORD"]="Grafana admin password for monitoring dashboard"
)

echo "📋 Checking required secrets..."
echo ""

MISSING_SECRETS=()
CONFIGURED_SECRETS=()

# Get list of configured secrets
CONFIGURED=$(gh secret list --json name --jq '.[].name')

for SECRET in "${!SECRETS[@]}"; do
    if echo "$CONFIGURED" | grep -q "^${SECRET}$"; then
        echo -e "${GREEN}✅ ${SECRET}${NC} - ${SECRETS[$SECRET]}"
        CONFIGURED_SECRETS+=("$SECRET")
    else
        echo -e "${RED}❌ ${SECRET}${NC} - ${SECRETS[$SECRET]} (MISSING)"
        MISSING_SECRETS+=("$SECRET")
    fi
done

echo ""
echo "================================"
echo ""

if [ ${#MISSING_SECRETS[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 All required secrets are configured!${NC}"
    echo ""
    echo "You can now:"
    echo "  1. Push to main branch to trigger automatic deployment"
    echo "  2. Manually trigger workflows from GitHub Actions tab"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Missing ${#MISSING_SECRETS[@]} secret(s)${NC}"
    echo ""
    echo "Missing secrets:"
    for SECRET in "${MISSING_SECRETS[@]}"; do
        echo "  - $SECRET: ${SECRETS[$SECRET]}"
    done
    echo ""
    echo "To add secrets:"
    echo "  1. Go to: Settings → Secrets and variables → Actions"
    echo "  2. Click 'New repository secret'"
    echo "  3. Add each missing secret"
    echo ""
    echo "Or use GitHub CLI:"
    echo "  gh secret set SECRET_NAME"
    echo ""
    echo "See docs/CI_CD_SETUP.md for detailed setup instructions"
    exit 1
fi
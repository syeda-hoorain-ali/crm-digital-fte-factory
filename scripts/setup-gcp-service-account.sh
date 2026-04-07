#!/bin/bash

# GCP Service Account Setup Script for GitHub Actions
# This script automates the creation of a GCP service account for CI/CD

set -e

echo "================================================"
echo "🔧 GCP Service Account Setup for GitHub Actions"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}⚠️  GitHub CLI (gh) is not installed${NC}"
    echo "Install it from: https://cli.github.com/"
    echo "You'll need to manually add secrets to GitHub"
    GH_AVAILABLE=false
else
    if ! gh auth status &> /dev/null; then
        echo -e "${YELLOW}⚠️  Not authenticated with GitHub CLI${NC}"
        echo "Run: gh auth login"
        GH_AVAILABLE=false
    else
        GH_AVAILABLE=true
    fi
fi

echo ""

# Get project ID
echo -e "${BLUE}📋 Step 1: Select GCP Project${NC}"
echo ""

CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -n "$CURRENT_PROJECT" ]; then
    echo "Current project: $CURRENT_PROJECT"
    read -p "Use this project? (y/n): " USE_CURRENT
    if [[ $USE_CURRENT =~ ^[Yy]$ ]]; then
        PROJECT_ID=$CURRENT_PROJECT
    else
        read -p "Enter GCP project ID: " PROJECT_ID
    fi
else
    read -p "Enter GCP project ID: " PROJECT_ID
fi

echo ""
echo "Using project: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

echo ""
echo -e "${BLUE}📋 Step 2: Create Service Account${NC}"
echo ""

SA_NAME="github-actions-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Check if service account already exists
if gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Service account already exists: $SA_EMAIL${NC}"
    read -p "Continue with existing service account? (y/n): " CONTINUE
    if [[ ! $CONTINUE =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 0
    fi
else
    echo "Creating service account: $SA_NAME"
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="GitHub Actions Deployer" \
        --description="Service account for GitHub Actions CI/CD pipeline"

    echo -e "${GREEN}✅ Service account created${NC}"
fi

echo ""
echo -e "${BLUE}📋 Step 3: Grant IAM Roles${NC}"
echo ""

ROLES=(
    "roles/container.developer"
    "roles/container.clusterAdmin"
    "roles/iam.serviceAccountUser"
)

for ROLE in "${ROLES[@]}"; do
    echo "Granting role: $ROLE"
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$ROLE" \
        --condition=None \
        > /dev/null
done

echo -e "${GREEN}✅ IAM roles granted${NC}"

echo ""
echo -e "${BLUE}📋 Step 4: Create Service Account Key${NC}"
echo ""

KEY_FILE="github-actions-key-$(date +%Y%m%d-%H%M%S).json"

echo "Creating key file: $KEY_FILE"
gcloud iam service-accounts keys create "$KEY_FILE" \
    --iam-account="$SA_EMAIL"

echo -e "${GREEN}✅ Key file created${NC}"

echo ""
echo -e "${BLUE}📋 Step 5: Get GKE Cluster Information${NC}"
echo ""

# List clusters
echo "Available GKE clusters:"
CLUSTER_COUNT=$(gcloud container clusters list --format="value(name)" | wc -l)
gcloud container clusters list --format="table(name,location,status)"

echo ""
read -p "Enter GKE cluster name: " CLUSTER_NAME
read -p "Enter GKE cluster zone/region: " CLUSTER_ZONE

# Verify cluster exists
if ! gcloud container clusters describe "$CLUSTER_NAME" --zone="$CLUSTER_ZONE" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Cluster not found: $CLUSTER_NAME in $CLUSTER_ZONE${NC}"
    echo ""
    echo "The cluster doesn't exist yet. Would you like to create it?"
    echo -e "${YELLOW}⏱️  Note: Cluster creation takes approximately 5-10 minutes${NC}"
    echo ""
    read -p "Create cluster now? (y/n): " CREATE_CLUSTER

    if [[ $CREATE_CLUSTER =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BLUE}🚀 Creating GKE cluster: $CLUSTER_NAME${NC}"
        echo ""

        # Ask for cluster configuration
        echo "Cluster configuration:"
        read -p "Number of nodes (default: 3): " NUM_NODES
        NUM_NODES=${NUM_NODES:-3}

        read -p "Machine type (default: n1-standard-2): " MACHINE_TYPE
        MACHINE_TYPE=${MACHINE_TYPE:-n1-standard-2}

        read -p "Enable autoscaling? (y/n, default: y): " ENABLE_AUTOSCALING
        ENABLE_AUTOSCALING=${ENABLE_AUTOSCALING:-y}

        if [[ $ENABLE_AUTOSCALING =~ ^[Yy]$ ]]; then
            read -p "Min nodes (default: 3): " MIN_NODES
            MIN_NODES=${MIN_NODES:-3}

            read -p "Max nodes (default: 10): " MAX_NODES
            MAX_NODES=${MAX_NODES:-10}

            AUTOSCALING_FLAGS="--enable-autoscaling --min-nodes=$MIN_NODES --max-nodes=$MAX_NODES"
        else
            AUTOSCALING_FLAGS=""
        fi

        echo ""
        echo "Creating cluster with configuration:"
        echo "  Name: $CLUSTER_NAME"
        echo "  Zone: $CLUSTER_ZONE"
        echo "  Nodes: $NUM_NODES"
        echo "  Machine type: $MACHINE_TYPE"
        if [[ $ENABLE_AUTOSCALING =~ ^[Yy]$ ]]; then
            echo "  Autoscaling: $MIN_NODES - $MAX_NODES nodes"
        fi
        echo ""
        echo -e "${YELLOW}⏱️  This will take 5-10 minutes. Please wait...${NC}"
        echo ""

        # Create the cluster
        if gcloud container clusters create "$CLUSTER_NAME" \
            --zone="$CLUSTER_ZONE" \
            --num-nodes="$NUM_NODES" \
            --machine-type="$MACHINE_TYPE" \
            $AUTOSCALING_FLAGS \
            --disk-size=50 \
            --disk-type=pd-standard \
            --enable-ip-alias \
            --network="default" \
            --subnetwork="default" \
            --no-enable-basic-auth \
            --no-issue-client-certificate \
            --enable-stackdriver-kubernetes \
            --addons=HorizontalPodAutoscaling,HttpLoadBalancing \
            --enable-autoupgrade \
            --enable-autorepair \
            --max-surge-upgrade=1 \
            --max-unavailable-upgrade=0; then

            echo ""
            echo -e "${GREEN}✅ Cluster created successfully!${NC}"
            echo ""

            # Get cluster credentials
            echo "Getting cluster credentials..."
            gcloud container clusters get-credentials "$CLUSTER_NAME" --zone="$CLUSTER_ZONE"

            echo -e "${GREEN}✅ Cluster is ready to use${NC}"
        else
            echo ""
            echo -e "${RED}❌ Failed to create cluster${NC}"
            echo "Please check the error message above and try again."
            exit 1
        fi
    else
        echo ""
        echo -e "${YELLOW}⚠️  Cluster creation skipped${NC}"
        echo "You can create the cluster later with:"
        echo ""
        echo "  gcloud container clusters create $CLUSTER_NAME \\"
        echo "    --zone=$CLUSTER_ZONE \\"
        echo "    --num-nodes=3 \\"
        echo "    --machine-type=n1-standard-2 \\"
        echo "    --enable-autoscaling \\"
        echo "    --min-nodes=3 \\"
        echo "    --max-nodes=10"
        echo ""
        echo "Then re-run this script."
        exit 0
    fi
else
    echo -e "${GREEN}✅ Cluster verified${NC}"
fi

echo ""
echo -e "${BLUE}📋 Step 6: Configure GitHub Secrets${NC}"
echo ""

# Read the key file
SA_KEY=$(cat "$KEY_FILE")

if [ "$GH_AVAILABLE" = true ]; then
    echo "Adding secrets to GitHub repository..."

    # Add secrets
    echo "$PROJECT_ID" | gh secret set GCP_PROJECT_ID
    echo "$SA_KEY" | gh secret set GCP_SA_KEY
    echo "$CLUSTER_NAME" | gh secret set GKE_CLUSTER_NAME
    echo "$CLUSTER_ZONE" | gh secret set GKE_ZONE

    echo -e "${GREEN}✅ Secrets added to GitHub${NC}"
else
    echo -e "${YELLOW}⚠️  GitHub CLI not available. Add these secrets manually:${NC}"
    echo ""
    echo "Go to: Settings → Secrets and variables → Actions → New repository secret"
    echo ""
    echo "1. GCP_PROJECT_ID"
    echo "   Value: $PROJECT_ID"
    echo ""
    echo "2. GCP_SA_KEY"
    echo "   Value: (contents of $KEY_FILE)"
    echo ""
    echo "3. GKE_CLUSTER_NAME"
    echo "   Value: $CLUSTER_NAME"
    echo ""
    echo "4. GKE_ZONE"
    echo "   Value: $CLUSTER_ZONE"
    echo ""
fi

echo ""
echo -e "${BLUE}📋 Step 7: Security Cleanup${NC}"
echo ""

echo -e "${YELLOW}⚠️  IMPORTANT: Secure the key file${NC}"
echo ""
echo "The service account key file contains sensitive credentials."
echo "Key file location: $KEY_FILE"
echo ""
read -p "Delete the key file now? (recommended) (y/n): " DELETE_KEY

if [[ $DELETE_KEY =~ ^[Yy]$ ]]; then
    rm "$KEY_FILE"
    echo -e "${GREEN}✅ Key file deleted${NC}"
else
    echo -e "${YELLOW}⚠️  Remember to delete $KEY_FILE after adding to GitHub${NC}"
    echo "Run: rm $KEY_FILE"
fi

echo ""
echo "================================================"
echo -e "${GREEN}🎉 GCP Service Account Setup Complete!${NC}"
echo ""
echo "Summary:"
echo "  Project ID: $PROJECT_ID"
echo "  Service Account: $SA_EMAIL"
echo "  GKE Cluster: $CLUSTER_NAME"
echo "  GKE Zone: $CLUSTER_ZONE"
echo ""
echo "Next steps:"
echo "  1. Verify secrets in GitHub: gh secret list"
echo "  2. Run: ./scripts/validate-ci-secrets.sh"
echo "  3. Set up remaining secrets (DockerHub, Database, Neon)"
echo "  4. Test deployment: gh workflow run '1. Build and Push Docker Image'"
echo ""
#!/bin/bash

# Neon Database Setup Script for GitHub Actions
# This script helps configure Neon database secrets for CI/CD

set -e

echo "=========================================="
echo "🐘 Neon Database Setup for GitHub Actions"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if neonctl is installed
if ! command -v neonctl &> /dev/null; then
    echo -e "${YELLOW}⚠️  Neon CLI (neonctl) is not installed${NC}"
    echo "Install it with: npm install -g neonctl"
    echo ""
    echo "You can still continue and get values from Neon Console:"
    echo "https://console.neon.tech"
    echo ""
    NEONCTL_AVAILABLE=false
else
    NEONCTL_AVAILABLE=true
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
echo -e "${BLUE}📋 Step 1: Get Neon API Key${NC}"
echo ""
echo "1. Go to: https://console.neon.tech/app/settings/api-keys"
echo "2. Click 'Generate new API key'"
echo "3. Copy the API key"
echo ""
read -sp "Enter Neon API Key: " NEON_API_KEY
echo ""

if [ -z "$NEON_API_KEY" ]; then
    echo -e "${RED}❌ API key is required${NC}"
    exit 1
fi

echo -e "${GREEN}✅ API key received${NC}"

echo ""
echo -e "${BLUE}📋 Step 2: Get Neon Project ID${NC}"
echo ""

if [ "$NEONCTL_AVAILABLE" = true ]; then
    echo "Fetching projects from Neon..."
    export NEON_API_KEY

    # List projects
    neonctl projects list

    echo ""
    read -p "Enter Project ID (or press Enter to use first project): " PROJECT_ID

    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(neonctl projects list --output json | jq -r '.[0].id')
        echo "Using first project: $PROJECT_ID"
    fi
else
    echo "Get your project ID from:"
    echo "https://console.neon.tech/app/projects"
    echo ""
    echo "Or from the URL: https://console.neon.tech/app/projects/YOUR_PROJECT_ID"
    echo ""
    read -p "Enter Neon Project ID: " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Project ID is required${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Project ID: $PROJECT_ID${NC}"

echo ""
echo -e "${BLUE}📋 Step 3: Get Main Branch ID${NC}"
echo ""

if [ "$NEONCTL_AVAILABLE" = true ]; then
    echo "Fetching branches from project..."

    # List branches
    neonctl branches list --project-id "$PROJECT_ID"

    echo ""
    read -p "Enter Main Branch ID (or press Enter to auto-detect): " MAIN_BRANCH_ID

    if [ -z "$MAIN_BRANCH_ID" ]; then
        MAIN_BRANCH_ID=$(neonctl branches list --project-id "$PROJECT_ID" --output json | jq -r '.[] | select(.name == "main") | .id')
        if [ -z "$MAIN_BRANCH_ID" ]; then
            # Try "master" if "main" not found
            MAIN_BRANCH_ID=$(neonctl branches list --project-id "$PROJECT_ID" --output json | jq -r '.[] | select(.name == "master") | .id')
        fi
        echo "Auto-detected main branch: $MAIN_BRANCH_ID"
    fi
else
    echo "Fetching branches from Neon API..."
    echo ""

    # Fetch branches using API
    BRANCHES_RESPONSE=$(curl -s -X GET \
        "https://console.neon.tech/api/v2/projects/$PROJECT_ID/branches" \
        -H "Authorization: Bearer $NEON_API_KEY" \
        -H "Accept: application/json")

    # Check if API call was successful
    if echo "$BRANCHES_RESPONSE" | jq -e '.branches' > /dev/null 2>&1; then
        # List branches for user to see
        echo "Available branches:"
        echo "$BRANCHES_RESPONSE" | jq -r '.branches[] | "  - \(.name) (ID: \(.id))"'
        echo ""

        # Auto-detect main branch
        MAIN_BRANCH_ID=$(echo "$BRANCHES_RESPONSE" | jq -r '.branches[] | select(.name == "main") | .id')

        if [ -z "$MAIN_BRANCH_ID" ]; then
            # Try "master" if "main" not found
            MAIN_BRANCH_ID=$(echo "$BRANCHES_RESPONSE" | jq -r '.branches[] | select(.name == "master") | .id')
        fi

        if [ -z "$MAIN_BRANCH_ID" ]; then
            # Try "production" if "master" not found
            MAIN_BRANCH_ID=$(echo "$BRANCHES_RESPONSE" | jq -r '.branches[] | select(.name == "production") | .id')
        fi

        if [ -n "$MAIN_BRANCH_ID" ]; then
            echo "Auto-detected main branch ID: $MAIN_BRANCH_ID"
            read -p "Use this branch? (y/n, or enter different ID): " BRANCH_CHOICE

            if [[ ! $BRANCH_CHOICE =~ ^[Yy]$ ]] && [ -n "$BRANCH_CHOICE" ]; then
                MAIN_BRANCH_ID="$BRANCH_CHOICE"
            fi
        else
            echo -e "${YELLOW}⚠️  Could not auto-detect 'main' or 'master' branch${NC}"
            read -p "Enter Main Branch ID from the list above: " MAIN_BRANCH_ID
        fi
    else
        echo -e "${RED}❌ Failed to fetch branches from Neon API${NC}"
        echo "Response: $BRANCHES_RESPONSE"
        echo ""
        echo "Please enter the branch ID manually."
        echo "You can find it at: https://console.neon.tech/app/projects/$PROJECT_ID"
        echo ""
        read -p "Enter Main Branch ID: " MAIN_BRANCH_ID
    fi
fi

if [ -z "$MAIN_BRANCH_ID" ]; then
    echo -e "${RED}❌ Main branch ID is required${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Main Branch ID: $MAIN_BRANCH_ID${NC}"

echo ""
echo -e "${BLUE}📋 Step 4: Get Production Database URL${NC}"
echo ""

if [ "$NEONCTL_AVAILABLE" = true ]; then
    echo "Fetching connection string..."

    # Get connection string
    PROD_DB_URL=$(neonctl connection-string --project-id "$PROJECT_ID" --branch-id "$MAIN_BRANCH_ID")

    echo "Connection string retrieved (masked)"
    echo -e "${GREEN}✅ Production database URL obtained${NC}"
else
    echo "Fetching connection string from Neon API..."
    echo ""

    # First, fetch available roles for the branch
    ROLES_RESPONSE=$(curl -s -X GET \
        "https://console.neon.tech/api/v2/projects/$PROJECT_ID/branches/$MAIN_BRANCH_ID/roles" \
        -H "Authorization: Bearer $NEON_API_KEY" \
        -H "Accept: application/json")

    # Get the first role (usually the default role)
    ROLE_NAME=$(echo "$ROLES_RESPONSE" | jq -r '.roles[0].name')

    if [ -z "$ROLE_NAME" ] || [ "$ROLE_NAME" == "null" ]; then
        echo -e "${YELLOW}⚠️  Could not auto-detect role name${NC}"
        read -p "Enter role name: " ROLE_NAME
    else
        echo "Using role: $ROLE_NAME"
    fi

    # Ask for database name (default is 'neondb')
    read -p "Database name (default: neondb): " DATABASE_NAME
    DATABASE_NAME=${DATABASE_NAME:-neondb}

    # Get connection string using API
    CONNECTION_RESPONSE=$(curl -s -X GET \
        "https://console.neon.tech/api/v2/projects/$PROJECT_ID/connection_uri?branch_id=$MAIN_BRANCH_ID&database_name=$DATABASE_NAME&role_name=$ROLE_NAME" \
        -H "Authorization: Bearer $NEON_API_KEY" \
        -H "Accept: application/json")

    # Check if API call was successful
    if echo "$CONNECTION_RESPONSE" | jq -e '.uri' > /dev/null 2>&1; then
        PROD_DB_URL=$(echo "$CONNECTION_RESPONSE" | jq -r '.uri')

        if [ -n "$PROD_DB_URL" ] && [ "$PROD_DB_URL" != "null" ]; then
            # Mask the connection string in logs
            echo "::add-mask::$PROD_DB_URL"
            echo "Connection string retrieved (masked for security)"
            echo -e "${GREEN}✅ Production database URL obtained${NC}"
        else
            echo -e "${RED}❌ Failed to get connection URI from response${NC}"
            echo ""
            echo "Please enter it manually from:"
            echo "https://console.neon.tech/app/projects/$PROJECT_ID"
            echo ""
            echo "Format: postgresql://user:password@host/dbname?sslmode=require"
            echo ""
            read -sp "Enter Production Database URL: " PROD_DB_URL
            echo ""
        fi
    else
        echo -e "${RED}❌ Failed to fetch connection string from Neon API${NC}"
        echo "Response: $CONNECTION_RESPONSE"
        echo ""
        echo "Please enter it manually from:"
        echo "https://console.neon.tech/app/projects/$PROJECT_ID"
        echo ""
        echo "Format: postgresql://user:password@host/dbname?sslmode=require"
        echo ""
        read -sp "Enter Production Database URL: " PROD_DB_URL
        echo ""
    fi
fi

if [ -z "$PROD_DB_URL" ]; then
    echo -e "${RED}❌ Production database URL is required${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}📋 Step 5: Verify Neon API Access${NC}"
echo ""

echo "Testing Neon API connection..."

API_TEST=$(curl -s -X GET \
    "https://console.neon.tech/api/v2/projects/$PROJECT_ID" \
    -H "Authorization: Bearer $NEON_API_KEY" \
    -H "Accept: application/json")

if echo "$API_TEST" | jq -e '.project.id' > /dev/null 2>&1; then
    PROJECT_NAME=$(echo "$API_TEST" | jq -r '.project.name')
    echo -e "${GREEN}✅ API connection successful${NC}"
    echo "Project: $PROJECT_NAME"
else
    echo -e "${RED}❌ API connection failed${NC}"
    echo "Response: $API_TEST"
    exit 1
fi

echo ""
echo -e "${BLUE}📋 Step 6: Configure GitHub Secrets${NC}"
echo ""

if [ "$GH_AVAILABLE" = true ]; then
    echo "Adding secrets to GitHub repository..."

    # Add secrets
    echo "$NEON_API_KEY" | gh secret set NEON_API_KEY
    echo "$PROJECT_ID" | gh secret set NEON_PROJECT_ID
    echo "$MAIN_BRANCH_ID" | gh secret set NEON_MAIN_BRANCH_ID
    echo "$PROD_DB_URL" | gh secret set PRODUCTION_DATABASE_URL

    echo -e "${GREEN}✅ Secrets added to GitHub${NC}"
else
    echo -e "${YELLOW}⚠️  GitHub CLI not available. Add these secrets manually:${NC}"
    echo ""
    echo "Go to: Settings → Secrets and variables → Actions → New repository secret"
    echo ""
    echo "1. NEON_API_KEY"
    echo "   Value: (your Neon API key)"
    echo ""
    echo "2. NEON_PROJECT_ID"
    echo "   Value: $PROJECT_ID"
    echo ""
    echo "3. NEON_MAIN_BRANCH_ID"
    echo "   Value: $MAIN_BRANCH_ID"
    echo ""
    echo "4. PRODUCTION_DATABASE_URL"
    echo "   Value: (your production database URL)"
    echo ""
fi

echo ""
echo -e "${BLUE}📋 Step 7: Test Branch Creation${NC}"
echo ""

read -p "Test creating a temporary Neon branch? (y/n): " TEST_BRANCH

if [[ $TEST_BRANCH =~ ^[Yy]$ ]]; then
    echo "Creating test branch..."

    TEST_BRANCH_NAME="ci-test-$(date +%Y%m%d-%H%M%S)"

    CREATE_RESPONSE=$(curl -s -X POST \
        "https://console.neon.tech/api/v2/projects/$PROJECT_ID/branches" \
        -H "Authorization: Bearer $NEON_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"branch\": {
                \"name\": \"$TEST_BRANCH_NAME\",
                \"parent_id\": \"$MAIN_BRANCH_ID\"
            }
        }")

    TEST_BRANCH_ID=$(echo "$CREATE_RESPONSE" | jq -r '.branch.id')

    if [ "$TEST_BRANCH_ID" != "null" ] && [ -n "$TEST_BRANCH_ID" ]; then
        echo -e "${GREEN}✅ Test branch created: $TEST_BRANCH_NAME${NC}"
        echo "Branch ID: $TEST_BRANCH_ID"

        # Delete test branch
        read -p "Delete test branch? (y/n): " DELETE_TEST
        if [[ $DELETE_TEST =~ ^[Yy]$ ]]; then
            curl -s -X DELETE \
                "https://console.neon.tech/api/v2/projects/$PROJECT_ID/branches/$TEST_BRANCH_ID" \
                -H "Authorization: Bearer $NEON_API_KEY" > /dev/null
            echo -e "${GREEN}✅ Test branch deleted${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to create test branch${NC}"
        echo "Response: $CREATE_RESPONSE"
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 Neon Database Setup Complete!${NC}"
echo ""
echo "Summary:"
echo "  Project ID: $PROJECT_ID"
echo "  Main Branch ID: $MAIN_BRANCH_ID"
echo "  API Access: ✅ Verified"
echo ""
echo "Next steps:"
echo "  1. Verify secrets in GitHub: gh secret list"
echo "  2. Run: ./scripts/validate-ci-secrets.sh"
echo "  3. Set up remaining secrets (DockerHub, GCP)"
echo "  4. Test workflow: gh workflow run '4. Test with Neon Branch'"
echo ""
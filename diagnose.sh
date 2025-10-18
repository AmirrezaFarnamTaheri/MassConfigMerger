#!/bin/bash

# ConfigStream Diagnostic Script
# This script helps identify issues with your deployment

echo "================================================"
echo "ConfigStream Diagnostic Tool"
echo "================================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to check URL
check_url() {
    local url=$1
    local description=$2

    echo -n "Checking $description... "

    # Use curl with specific options for debugging
    response=$(curl -s -o /dev/null -w "%{http_code}" -H "Cache-Control: no-cache" "$url")

    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓${NC} (HTTP $response)"
        return 0
    elif [ "$response" = "404" ]; then
        echo -e "${RED}✗${NC} (HTTP $response - Not Found)"
        return 1
    else
        echo -e "${YELLOW}⚠${NC} (HTTP $response)"
        return 1
    fi
}

# Function to check JSON validity
check_json() {
    local file=$1
    local description=$2

    echo -n "Validating $description... "

    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC} (File not found)"
        return 1
    fi

    if python3 -m json.tool "$file" > /dev/null 2>&1; then
        # Get some stats
        if [[ "$file" == *"proxies.json" ]]; then
            count=$(python3 -c "import json; print(len(json.load(open('$file'))))" 2>/dev/null || echo "error")
            echo -e "${GREEN}✓${NC} (Valid JSON, $count proxies)"
        else
            echo -e "${GREEN}✓${NC} (Valid JSON)"
        fi
        return 0
    else
        echo -e "${RED}✗${NC} (Invalid JSON)"
        python3 -m json.tool "$file" 2>&1 | head -5
        return 1
    fi
}

echo "1. Checking Local Files"
echo "------------------------"

# Check if output directory exists
if [ -d "output" ]; then
    echo -e "${GREEN}✓${NC} output/ directory exists"

    # Check individual files
    check_json "output/proxies.json" "proxies.json"
    check_json "output/statistics.json" "statistics.json"
    check_json "output/metadata.json" "metadata.json"
else
    echo -e "${RED}✗${NC} output/ directory not found"
fi

echo ""
echo "2. Checking GitHub Configuration"
echo "---------------------------------"

# Check if we're in a git repository
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Git repository detected"

    # Get repository info
    remote_url=$(git config --get remote.origin.url)
    echo "  Remote: $remote_url"

    # Extract username and repo from URL
    if [[ $remote_url =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
        username="${BASH_REMATCH[1]}"
        repo="${BASH_REMATCH[2]}"
        echo "  User: $username"
        echo "  Repo: $repo"

        # Store for later use
        GITHUB_USER="$username"
        GITHUB_REPO="$repo"
    fi

    # Check current branch
    current_branch=$(git branch --show-current)
    echo "  Current branch: $current_branch"

    if [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ]; then
        echo -e "  ${YELLOW}⚠${NC} Not on main/master branch"
    fi

    # Check for uncommitted changes
    if git diff --quiet && git diff --staged --quiet; then
        echo -e "  ${GREEN}✓${NC} No uncommitted changes"
    else
        echo -e "  ${YELLOW}⚠${NC} Uncommitted changes detected"
    fi
else
    echo -e "${RED}✗${NC} Not a git repository"
fi

echo ""
echo "3. Checking GitHub Actions"
echo "---------------------------"

if [ -f ".github/workflows/merge.yml" ]; then
    echo -e "${GREEN}✓${NC} Workflow file exists"

    # Check if workflow has required permissions
    if grep -q "contents: write" .github/workflows/merge.yml; then
        echo -e "  ${GREEN}✓${NC} Write permissions configured"
    else
        echo -e "  ${RED}✗${NC} Missing write permissions"
    fi

    # Check schedule
    if grep -q "cron:" .github/workflows/merge.yml; then
        schedule=$(grep -A1 "cron:" .github/workflows/merge.yml | tail -1 | xargs)
        echo -e "  ${GREEN}✓${NC} Schedule configured: $schedule"
    else
        echo -e "  ${YELLOW}⚠${NC} No schedule found"
    fi
else
    echo -e "${RED}✗${NC} Workflow file not found"
fi

echo ""
echo "4. Checking GitHub Pages Deployment"
echo "------------------------------------"

if [ ! -z "$GITHUB_USER" ] && [ ! -z "$GITHUB_REPO" ]; then
    pages_url="https://${GITHUB_USER}.github.io/${GITHUB_REPO}/"

    echo "Testing GitHub Pages URLs:"
    check_url "$pages_url" "Homepage"
    check_url "${pages_url}output/metadata.json" "Metadata endpoint"
    check_url "${pages_url}output/proxies.json" "Proxies endpoint"
    check_url "${pages_url}output/statistics.json" "Statistics endpoint"

    # Check if metadata is recent
    echo ""
    echo -n "Checking data freshness... "
    metadata_url="${pages_url}output/metadata.json"
    metadata=$(curl -s -H "Cache-Control: no-cache" "$metadata_url" 2>/dev/null)

    if [ ! -z "$metadata" ]; then
        generated_at=$(echo "$metadata" | python3 -c "import json, sys; print(json.load(sys.stdin).get('generated_at', 'unknown'))" 2>/dev/null)

        if [ "$generated_at" != "unknown" ]; then
            echo -e "${GREEN}✓${NC} Last updated: $generated_at"

            # Check if it's recent (within 6 hours)
            current_timestamp=$(date +%s)
            if command -v python3 > /dev/null; then
                data_timestamp=$(python3 -c "from datetime import datetime; print(int(datetime.fromisoformat('$generated_at'.replace('Z', '+00:00')).timestamp()))" 2>/dev/null || echo "0")
                age_hours=$(( (current_timestamp - data_timestamp) / 3600 ))

                if [ $age_hours -lt 6 ]; then
                    echo -e "  ${GREEN}✓${NC} Data is fresh ($age_hours hours old)"
                else
                    echo -e "  ${YELLOW}⚠${NC} Data is stale ($age_hours hours old)"
                fi
            fi
        else
            echo -e "${YELLOW}⚠${NC} Could not parse update time"
        fi
    else
        echo -e "${RED}✗${NC} Could not fetch metadata"
    fi
else
    echo -e "${YELLOW}⚠${NC} Could not determine GitHub Pages URL"
fi

echo ""
echo "5. Checking Python Environment"
echo "-------------------------------"

# Check Python
if command -v python3 > /dev/null; then
    python_version=$(python3 --version)
    echo -e "${GREEN}✓${NC} Python installed: $python_version"
else
    echo -e "${RED}✗${NC} Python3 not found"
fi

# Check if package is installed
if python3 -c "import configstream" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} ConfigStream package installed"

    # Check if CLI works
    if command -v configstream > /dev/null; then
        echo -e "  ${GREEN}✓${NC} CLI command available"
    else
        echo -e "  ${YELLOW}⚠${NC} CLI command not in PATH"
    fi
else
    echo -e "${RED}✗${NC} ConfigStream package not installed"
    echo "  Run: pip install -e ."
fi

echo ""
echo "6. Testing API Endpoints Locally"
echo "---------------------------------"

# Start a simple HTTP server in background to test
if command -v python3 > /dev/null; then
    echo "Starting local test server..."
    python3 -m http.server 8888 > /dev/null 2>&1 &
    SERVER_PID=$!
    sleep 2

    # Test local endpoints
    check_url "http://localhost:8888/output/metadata.json" "Local metadata"
    check_url "http://localhost:8888/output/proxies.json" "Local proxies"

    # Clean up
    kill $SERVER_PID 2>/dev/null
    echo "Local server stopped"
else
    echo -e "${YELLOW}⚠${NC} Cannot test local server (Python not available)"
fi

echo ""
echo "================================================"
echo "Diagnostic Summary"
echo "================================================"

# Provide recommendations based on findings
echo ""
echo "Recommended Actions:"
echo "--------------------"

if [ ! -d "output" ]; then
    echo "1. Create output directory: mkdir -p output"
fi

if [ ! -f "output/proxies.json" ]; then
    echo "2. Run initial merge: configstream merge --sources sources.txt --output output/"
fi

if ! python3 -c "import configstream" 2>/dev/null; then
    echo "3. Install package: pip install -e ."
fi

echo ""
echo "To manually trigger the workflow:"
echo "  1. Go to: https://github.com/${GITHUB_USER}/${GITHUB_REPO}/actions"
echo "  2. Click on 'Merge and Retest VPN Subscriptions'"
echo "  3. Click 'Run workflow'"
echo ""

echo "To view recent workflow runs:"
echo "  https://github.com/${GITHUB_USER}/${GITHUB_REPO}/actions/workflows/merge.yml"
echo ""

echo "Diagnostic complete!"
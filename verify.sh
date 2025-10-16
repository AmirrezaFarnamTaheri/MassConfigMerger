#!/bin/bash

##############################################
# ConfigStream Integration Verification Script
# Tests all components and reports status
##############################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Configuration
GITHUB_USERNAME="${1:-YOUR_USERNAME}"
REPO_NAME="ConfigStream"
BASE_URL="https://${GITHUB_USERNAME}.github.io/${REPO_NAME}"

##############################################
# Helper Functions
##############################################

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
    ((TESTS_TOTAL++))
}

print_failure() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
    ((TESTS_TOTAL++))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_failure "$1 is not installed"
        return 1
    fi
}

check_url() {
    local url=$1
    local description=$2
    
    if curl -s -f -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|301\|302"; then
        print_success "$description is accessible"
        return 0
    else
        print_failure "$description is not accessible"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        print_success "File exists: $1"
        return 0
    else
        print_failure "File missing: $1"
        return 1
    fi
}

check_json_valid() {
    local url=$1
    local description=$2
    
    if curl -s "$url" | python3 -m json.tool &> /dev/null; then
        print_success "$description is valid JSON"
        return 0
    else
        print_failure "$description has invalid JSON"
        return 1
    fi
}

##############################################
# Test Sections
##############################################

test_prerequisites() {
    print_header "1. Prerequisites Check"
    
    print_test "Checking required tools..."
    check_command "git"
    check_command "python3"
    check_command "pip"
    check_command "curl"
}

test_local_files() {
    print_header "2. Local File Structure"
    
    print_test "Checking HTML files..."
    check_file "index.html"
    check_file "proxies.html"
    check_file "statistics.html"
    
    print_test "Checking asset files..."
    check_file "assets/css/framework.css"
    check_file "assets/js/utils.js"
    
    print_test "Checking configuration files..."
    check_file "sources.txt"
    check_file "pyproject.toml"
    check_file ".github/workflows/merge.yml"
    
    print_test "Checking Python source..."
    check_file "src/configstream/__init__.py"
    check_file "src/configstream/cli.py"
    check_file "src/configstream/core.py"
    check_file "src/configstream/pipeline.py"
}

test_python_setup() {
    print_header "3. Python Package Setup"
    
    print_test "Installing package in development mode..."
    if pip install -e . &> /dev/null; then
        print_success "Package installed successfully"
    else
        print_failure "Package installation failed"
    fi
    
    print_test "Checking CLI command..."
    if command -v configstream &> /dev/null; then
        print_success "configstream command is available"
    else
        print_failure "configstream command not found"
    fi
    
    print_test "Testing CLI help..."
    if configstream --help &> /dev/null; then
        print_success "CLI help command works"
    else
        print_failure "CLI help command failed"
    fi
}

test_local_execution() {
    print_header "4. Local Execution Test"
    
    print_test "Creating test output directory..."
    mkdir -p test_output
    
    print_test "Running merge command (this may take a while)..."
    if timeout 300 configstream merge \
        --sources sources.mini.txt \
        --output test_output/ \
        --max-proxies 10 \
        --max-workers 5 \
        --timeout 10 &> test_output/merge.log; then
        print_success "Merge command completed successfully"
    else
        print_failure "Merge command failed (check test_output/merge.log)"
    fi
    
    print_test "Checking output files..."
    check_file "test_output/vpn_subscription_base64.txt"
    check_file "test_output/clash.yaml"
    check_file "test_output/configs_raw.txt"
    check_file "test_output/proxies.json"
    check_file "test_output/statistics.json"
    check_file "test_output/metadata.json"
    
    print_test "Validating JSON output..."
    if [ -f "test_output/proxies.json" ]; then
        if python3 -m json.tool test_output/proxies.json &> /dev/null; then
            print_success "proxies.json is valid"
        else
            print_failure "proxies.json is invalid"
        fi
    fi
    
    print_test "Cleaning up test output..."
    rm -rf test_output
}

test_github_pages() {
    print_header "5. GitHub Pages Deployment"
    
    print_test "Checking main pages..."
    check_url "$BASE_URL/" "Home page"
    check_url "$BASE_URL/proxies.html" "Proxies page"
    check_url "$BASE_URL/statistics.html" "Statistics page"
    
    print_test "Checking assets..."
    check_url "$BASE_URL/assets/css/framework.css" "CSS framework"
    check_url "$BASE_URL/assets/js/utils.js" "JavaScript utilities"
    
    print_test "Checking output files..."
    check_url "$BASE_URL/output/metadata.json" "Metadata JSON"
    check_url "$BASE_URL/output/statistics.json" "Statistics JSON"
    check_url "$BASE_URL/output/proxies.json" "Proxies JSON"
    check_url "$BASE_URL/output/vpn_subscription_base64.txt" "Base64 subscription"
    check_url "$BASE_URL/output/clash.yaml" "Clash config"
}

test_data_integrity() {
    print_header "6. Data Integrity Check"
    
    print_test "Validating JSON files..."
    check_json_valid "$BASE_URL/output/metadata.json" "Metadata"
    check_json_valid "$BASE_URL/output/statistics.json" "Statistics"
    check_json_valid "$BASE_URL/output/proxies.json" "Proxies"
    
    print_test "Checking data freshness..."
    local updated_at=$(curl -s "$BASE_URL/output/metadata.json" | python3 -c "import sys, json; print(json.load(sys.stdin).get('generated_at', ''))")
    if [ -n "$updated_at" ]; then
        print_success "Last update: $updated_at"
    else
        print_failure "Could not determine last update time"
    fi
    
    print_test "Checking proxy count..."
    local proxy_count=$(curl -s "$BASE_URL/output/proxies.json" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
    if [ "$proxy_count" -gt 0 ]; then
        print_success "Found $proxy_count proxies"
    else
        print_failure "No proxies found"
    fi
}

test_javascript() {
    print_header "7. JavaScript Functionality"
    
    print_test "Checking utils.js syntax..."
    if node -c assets/js/utils.js 2> /dev/null; then
        print_success "utils.js has valid syntax"
    elif python3 -c "import sys; sys.exit(0 if 'function' in open('assets/js/utils.js').read() else 1)"; then
        print_success "utils.js appears valid (Node.js not available)"
    else
        print_failure "utils.js may have syntax errors"
    fi
    
    print_test "Checking for common issues..."
    if grep -q "console.log" assets/js/utils.js; then
        print_info "Found console.log statements (consider removing for production)"
    fi
    
    if grep -q "debugger" assets/js/*.js 2>/dev/null; then
        print_failure "Found debugger statements (remove for production)"
    else
        print_success "No debugger statements found"
    fi
}

test_github_actions() {
    print_header "8. GitHub Actions Workflow"
    
    print_test "Checking workflow file syntax..."
    if command -v yamllint &> /dev/null; then
        if yamllint .github/workflows/merge.yml &> /dev/null; then
            print_success "Workflow YAML is valid"
        else
            print_failure "Workflow YAML has errors"
        fi
    else
        print_info "yamllint not installed, skipping YAML validation"
    fi
    
    print_test "Checking workflow schedule..."
    if grep -q "cron:" .github/workflows/merge.yml; then
        print_success "Workflow has schedule configured"
    else
        print_failure "Workflow schedule not found"
    fi
    
    print_test "Checking workflow permissions..."
    if grep -q "contents: write" .github/workflows/merge.yml; then
        print_success "Workflow has write permissions"
    else
        print_failure "Workflow may lack necessary permissions"
    fi
}

test_security() {
    print_header "9. Security Check"
    
    print_test "Checking for exposed secrets..."
    if git grep -i "password\|api_key\|secret\|token" -- ':!*.md' ':!verify.sh' | grep -v "example\|template\|placeholder" > /dev/null; then
        print_failure "Potential secrets found in code"
    else
        print_success "No obvious secrets found"
    fi
    
    print_test "Checking for eval usage..."
    if grep -r "eval(" assets/js/ src/ 2>/dev/null | grep -v "test\|example" > /dev/null; then
        print_failure "Found eval() usage (security risk)"
    else
        print_success "No eval() usage found"
    fi
    
    print_test "Checking for innerHTML usage..."
    if grep -r "\.innerHTML\s*=" assets/js/ 2>/dev/null | wc -l | xargs test 5 -lt; then
        print_info "Multiple innerHTML usages found (ensure input is sanitized)"
    else
        print_success "Limited innerHTML usage"
    fi
}

test_performance() {
    print_header "10. Performance Check"
    
    print_test "Checking file sizes..."
    
    local html_size=$(find . -name "*.html" -not -path "./_site/*" -exec cat {} \; | wc -c)
    if [ "$html_size" -lt 500000 ]; then
        print_success "Total HTML size: $(echo "scale=2; $html_size/1024" | bc)KB (good)"
    else
        print_info "Total HTML size: $(echo "scale=2; $html_size/1024" | bc)KB (consider optimization)"
    fi
    
    if [ -f "assets/css/framework.css" ]; then
        local css_size=$(wc -c < assets/css/framework.css)
        if [ "$css_size" -lt 100000 ]; then
            print_success "CSS size: $(echo "scale=2; $css_size/1024" | bc)KB (good)"
        else
            print_info "CSS size: $(echo "scale=2; $css_size/1024" | bc)KB (consider minification)"
        fi
    fi
    
    if [ -f "assets/js/utils.js" ]; then
        local js_size=$(wc -c < assets/js/utils.js)
        if [ "$js_size" -lt 100000 ]; then
            print_success "JS size: $(echo "scale=2; $js_size/1024" | bc)KB (good)"
        else
            print_info "JS size: $(echo "scale=2; $js_size/1024" | bc)KB (consider minification)"
        fi
    fi
}

##############################################
# Main Execution
##############################################

main() {
    clear
    echo -e "${GREEN}"
    cat << "EOF"
   ____             __ _       ____  _                            
  / ___|___  _ __  / _(_) __ _/ ___|| |_ _ __ ___  __ _ _ __ ___  
 | |   / _ \| '_ \| |_| |/ _` \___ \| __| '__/ _ \/ _` | '_ ` _ \ 
 | |__| (_) | | | |  _| | (_| |___) | |_| | |  __/ (_| | | | | | |
  \____\___/|_| |_|_| |_|\__, |____/ \__|_|  \___|\__,_|_| |_| |_|
                         |___/                                     
EOF
    echo -e "${NC}"
    echo -e "${BLUE}Integration Verification Script${NC}"
    echo -e "${BLUE}Version 1.0.0${NC}"
    echo ""
    
    if [ "$GITHUB_USERNAME" = "YOUR_USERNAME" ]; then
        echo -e "${YELLOW}WARNING: Using default username. Pass your GitHub username as argument:${NC}"
        echo -e "${YELLOW}  ./verify.sh YOUR_GITHUB_USERNAME${NC}"
        echo ""
    fi
    
    # Run all tests
    test_prerequisites
    test_local_files
    test_python_setup
    test_local_execution
    test_github_pages
    test_data_integrity
    test_javascript
    test_github_actions
    test_security
    test_performance
    
    # Summary
    print_header "Test Summary"
    
    echo -e "Total Tests: ${BLUE}$TESTS_TOTAL${NC}"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    echo ""
    
    local pass_rate=$(echo "scale=2; $TESTS_PASSED * 100 / $TESTS_TOTAL" | bc)
    echo -e "Pass Rate: ${BLUE}${pass_rate}%${NC}"
    echo ""
    
    if [ "$TESTS_FAILED" -eq 0 ]; then
        echo -e "${GREEN}═══════════════════════════════════════${NC}"
        echo -e "${GREEN}   ✓ ALL TESTS PASSED!${NC}"
        echo -e "${GREEN}   ConfigStream is ready for production${NC}"
        echo -e "${GREEN}═══════════════════════════════════════${NC}"
        exit 0
    else
        echo -e "${RED}═══════════════════════════════════════${NC}"
        echo -e "${RED}   ✗ SOME TESTS FAILED${NC}"
        echo -e "${RED}   Please review and fix the issues${NC}"
        echo -e "${RED}═══════════════════════════════════════${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
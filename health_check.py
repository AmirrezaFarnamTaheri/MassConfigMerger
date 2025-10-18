#!/usr/bin/env python3
"""
Health check script for ConfigStream deployment
Run this periodically to ensure everything is working
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

def check_local_files():
    """Check if local output files exist and are valid"""
    issues = []
    output_dir = Path("output")

    if not output_dir.exists():
        issues.append("Output directory missing")
        return issues

    required_files = ["proxies.json", "statistics.json", "metadata.json"]
    for file_name in required_files:
        file_path = output_dir / file_name
        if not file_path.exists():
            issues.append(f"{file_name} missing")
        else:
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    if file_name == "proxies.json" and len(data) == 0:
                        issues.append("No proxies in proxies.json")
            except json.JSONDecodeError:
                issues.append(f"{file_name} is not valid JSON")

    return issues

def check_data_freshness():
    """Check if data is recent"""
    metadata_file = Path("output/metadata.json")
    if not metadata_file.exists():
        return ["Metadata file missing"]

    try:
        with open(metadata_file) as f:
            metadata = json.load(f)

        generated_at = metadata.get("generated_at")
        if not generated_at:
            return ["No generation timestamp in metadata"]

        # Parse the timestamp
        generated_time = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age = now - generated_time

        if age > timedelta(hours=6):
            hours_old = int(age.total_seconds() / 3600)
            return [f"Data is {hours_old} hours old (should update every 3 hours)"]

    except Exception as e:
        return [f"Error checking freshness: {e}"]

    return []

def check_github_pages(username, repo):
    """Check if GitHub Pages is serving fresh data"""
    base_url = f"https://{username}.github.io/{repo}"
    issues = []

    endpoints = [
        "/output/metadata.json",
        "/output/proxies.json",
        "/output/statistics.json"
    ]

    for endpoint in endpoints:
        url = base_url + endpoint
        try:
            response = requests.get(url, timeout=10, headers={"Cache-Control": "no-cache"})
            if response.status_code != 200:
                issues.append(f"{endpoint} returned {response.status_code}")
            elif endpoint == "/output/metadata.json":
                # Check freshness of deployed data
                data = response.json()
                generated_at = data.get("generated_at")
                if generated_at:
                    generated_time = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                    age = datetime.now(timezone.utc) - generated_time
                    if age > timedelta(hours=6):
                        hours_old = int(age.total_seconds() / 3600)
                        issues.append(f"Deployed data is {hours_old} hours old")
        except requests.RequestException as e:
            issues.append(f"Failed to fetch {endpoint}: {e}")
        except json.JSONDecodeError:
            issues.append(f"{endpoint} returned invalid JSON")

    return issues

def main():
    """Run all health checks"""
    print("🏥 ConfigStream Health Check\n")

    all_issues = []

    # Check local files
    print("Checking local files...")
    issues = check_local_files()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ All local files OK")

    # Check data freshness
    print("\nChecking data freshness...")
    issues = check_data_freshness()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ Data is fresh")

    # Check GitHub Pages (replace with your username/repo)
    print("\nChecking GitHub Pages deployment...")
    # You need to update these with your actual GitHub username and repo name
    USERNAME = "YOUR_GITHUB_USERNAME"
    REPO = "ConfigStream"

    if USERNAME != "YOUR_GITHUB_USERNAME":
        issues = check_github_pages(USERNAME, REPO)
        if issues:
            all_issues.extend(issues)
            for issue in issues:
                print(f"  ❌ {issue}")
        else:
            print("  ✅ GitHub Pages serving fresh data")
    else:
        print("  ⏭️  Skipped (update USERNAME in script)")

    # Summary
    print("\n" + "="*50)
    if all_issues:
        print(f"❌ Found {len(all_issues)} issue(s):")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
        sys.exit(1)
    else:
        print("✅ All systems operational!")
        sys.exit(0)

if __name__ == "__main__":
    main()
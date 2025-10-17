#!/usr/bin/env python3
"""Verification script to test the setup"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def main():
    checks = [
        ("pytest tests/", "Running tests"),
        ("configstream --help", "CLI command available"),
        ("python -c 'import configstream'", "Package importable"),
    ]

    # Check required files exist
    required_files = [
        ".github/workflows/generate-configs.yml",
        "index.html",
        "pyproject.toml",
        "README.md",
    ]

    print("📁 Checking required files...")
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            return False

    # Run command checks
    all_passed = all(run_command(cmd, desc) for cmd, desc in checks)

    if all_passed:
        print("\n🎉 All checks passed! Your setup is ready.")
        return True
    else:
        print("\n⚠️  Some checks failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

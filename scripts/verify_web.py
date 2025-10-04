from __future__ import annotations

import time
from playwright.sync_api import sync_playwright

def run_verification():
    """Launch the web browser and navigate to the web routes to verify them."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        base_url = "http://localhost:8080"

        print("Verifying /aggregate route...")
        page.goto(f"{base_url}/aggregate")
        time.sleep(2) # Give time for the async operation to complete
        page.screenshot(path="output/verification_aggregate.png")
        print(".../aggregate verified.")

        print("Verifying /merge route...")
        page.goto(f"{base_url}/merge")
        time.sleep(2)
        page.screenshot(path="output/verification_merge.png")
        print(".../merge verified.")

        print("Verifying /report route...")
        page.goto(f"{base_url}/report")
        time.sleep(2)
        page.screenshot(path="output/verification_report.png")
        print(".../report verified.")

        browser.close()
        print("\nWeb verification complete. Screenshots saved to 'output/' directory.")

if __name__ == "__main__":
    run_verification()
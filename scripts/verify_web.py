from __future__ import annotations

from playwright.sync_api import sync_playwright


def run_verification():
    """Launch the web browser and navigate to the web routes to verify them."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        base_url = "http://localhost:8080"

        print("Verifying /aggregate route...")
        page.goto(f"{base_url}/aggregate")
        page.wait_for_load_state("networkidle", timeout=30000)  # Wait up to 30s
        page.screenshot(path="output/verification_aggregate.png")
        print(".../aggregate verified.")

        print("Verifying /merge route...")
        page.goto(f"{base_url}/merge")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.screenshot(path="output/verification_merge.png")
        print(".../merge verified.")

        print("Verifying /report route...")
        page.goto(f"{base_url}/report")
        page.wait_for_load_state("networkidle", timeout=30000)
        page.screenshot(path="output/verification_report.png")
        print(".../report verified.")

        browser.close()
        print("\nWeb verification complete. Screenshots saved to 'output/' directory.")


if __name__ == "__main__":
    run_verification()
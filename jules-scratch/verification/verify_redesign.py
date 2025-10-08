from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the dashboard
        page.goto("http://localhost:8080/")

        # Wait for the main container to be visible to ensure the page has loaded
        expect(page.locator(".container")).to_be_visible()

        # Take a screenshot of the dashboard
        page.screenshot(path="jules-scratch/verification/dashboard.png")

        # Find the link and wait for it to be visible
        history_link = page.get_by_role("link", name="📜 Full History")
        expect(history_link).to_be_visible()

        # Navigate to the history page
        history_link.click()

        # Wait for the history table to be visible
        expect(page.locator("table[aria-label='Complete proxy history']")).to_be_visible()

        # Take a screenshot of the history page
        page.screenshot(path="jules-scratch/verification/history.png")

        browser.close()

if __name__ == "__main__":
    run()
from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch()
    page = browser.new_page()

    # Navigate to the dashboard
    page.goto("http://localhost:8080/")

    # Wait for the header to be visible to ensure the page has loaded
    header = page.locator("header.header")
    expect(header).to_be_visible()

    # Take a screenshot of the dashboard
    page.screenshot(path="jules-scratch/verification/dashboard.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
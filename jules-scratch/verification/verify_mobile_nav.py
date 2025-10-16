from playwright.sync_api import sync_playwright
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone 8 viewport

        # Go to the locally built file
        page.goto(f"file://{os.getcwd()}/index.html")

        # Click the mobile nav toggle
        page.click('#mobile-nav-toggle')

        page.wait_for_timeout(500)  # Wait for animations to complete
        page.screenshot(path='jules-scratch/verification/mobile_nav.png')
        browser.close()

run()
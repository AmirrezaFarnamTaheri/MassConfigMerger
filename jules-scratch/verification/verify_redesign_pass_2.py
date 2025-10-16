from playwright.sync_api import sync_playwright, Page, expect
import os

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Capture console messages
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))

    # Get the absolute path to the index.html file
    file_path = os.path.abspath("index.html")

    # Go to the local HTML file and wait for the load event
    page.goto(f"file://{file_path}", wait_until="load")

    # Set viewport to a mobile size
    page.set_viewport_size({"width": 375, "height": 667})

    # Wait for the mobile navigation toggle to be visible
    toggle_button = page.locator("#mobile-nav-toggle")
    expect(toggle_button).to_be_visible()

    # Click the mobile navigation toggle
    toggle_button.click()

    # Expect the nav to have the 'active' class
    expect(page.locator("#main-nav")).to_have_class("nav active")

    # Take a screenshot
    page.screenshot(path="jules-scratch/verification/verification_pass_2.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
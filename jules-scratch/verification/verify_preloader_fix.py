import asyncio
from playwright.async_api import async_playwright, expect

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Construct the full path to the HTML file
        import os
        file_path = os.path.abspath("index.html")

        await page.goto(f"file://{file_path}")

        # Wait for the preloader to disappear
        preloader = page.locator("#preloader")
        await expect(preloader).to_be_hidden(timeout=10000)

        # Wait for the main content to be loaded and visible
        hero_section = page.locator(".hero")
        await expect(hero_section).to_be_visible(timeout=5000)

        # Take a screenshot
        await page.screenshot(path="jules-scratch/verification/verification.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
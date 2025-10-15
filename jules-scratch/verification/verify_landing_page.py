import asyncio
from playwright.async_api import async_playwright, expect
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Get the absolute path to the index.html file
        file_path = os.path.abspath('index.html')

        # Go to the local HTML file
        await page.goto(f'file://{file_path}')

        # Check that the main heading is visible
        heading = page.get_by_role("heading", name="ConfigStream")
        await expect(heading).to_be_visible()

        # Check that the "Base64 Subscription" download card is present
        base64_card = page.get_by_role("link", name="Base64 Subscription")
        await expect(base64_card).to_be_visible()

        # Take a screenshot for visual verification
        await page.screenshot(path="jules-scratch/verification/verification.png")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
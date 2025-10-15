import asyncio
from playwright.async_api import async_playwright, expect
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        file_path = os.path.abspath('index.html')
        await page.goto(f'file://{file_path}')

        # Check for the new header
        header = page.get_by_role("heading", name="Welcome to ConfigStream")
        await expect(header).to_be_visible()

        # Check that the logo is visible
        logo = page.locator(".logo")
        await expect(logo).to_be_visible()

        # Check for the status section
        status_section = page.locator(".status-section")
        await expect(status_section).to_be_visible()

        # Check for one of the new download cards
        download_card = page.get_by_role("link", name="Base64 Subscription")
        await expect(download_card).to_be_visible()

        # Take a screenshot for visual verification
        await page.screenshot(path="jules-scratch/verification/final_fixes_verification.png", full_page=True)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
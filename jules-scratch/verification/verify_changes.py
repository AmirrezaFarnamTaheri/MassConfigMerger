import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Verify index.html
        index_path = "file://" + os.path.abspath("index.html")
        await page.goto(index_path)
        await page.wait_for_timeout(2000)  # Wait for animations
        await page.screenshot(path="jules-scratch/verification/index_page.png")

        # Verify statistics.html empty state
        stats_path = "file://" + os.path.abspath("statistics.html")
        await page.goto(stats_path)

        # Make the empty state visible for the screenshot
        await page.evaluate("document.getElementById('chartsContainer').classList.add('hidden')")
        await page.evaluate("document.getElementById('chartsEmptyState').classList.remove('hidden')")
        await page.wait_for_timeout(1000) # Wait for animations

        await page.screenshot(path="jules-scratch/verification/statistics_empty_state.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
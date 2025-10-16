import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Get the absolute path to the project directory
        project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        # Index page
        await page.goto(f"file://{project_dir}/index.html")
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path="jules-scratch/verification/01-index.png")

        # Proxies page
        await page.goto(f"file://{project_dir}/proxies.html")
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path="jules-scratch/verification/02-proxies.png")

        # Statistics page
        await page.goto(f"file://{project_dir}/statistics.html")
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path="jules-scratch/verification/03-statistics.png")

        # About page
        await page.goto(f"file://{project_dir}/about.html")
        await page.wait_for_load_state('networkidle')
        await page.screenshot(path="jules-scratch/verification/04-about.png")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
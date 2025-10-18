import asyncio
from playwright.async_api import async_playwright, expect
from playwright._impl._errors import TimeoutError

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        # Listen for console messages
        msgs = []
        page.on("console", lambda msg: msgs.append(msg.text))

        # Go to the index page
        await page.goto("http://localhost:8888/index.html", wait_until="domcontentloaded")

        try:
            # Wait for the preloader to be hidden
            await page.wait_for_selector("#preloader.hidden", timeout=10000)
            print("✅ Preloader is hidden.")

            # Verify the logo animation
            logo = page.locator(".logo-animated")
            await expect(logo).to_be_visible()

            # Wait for the animation to finish
            await page.wait_for_timeout(6000)

            # Check the color of the logo
            await logo.evaluate("element => element.classList.add('animation-complete')")
            color = await logo.evaluate("element => window.getComputedStyle(element).color")
            assert color == "rgb(0, 0, 0)" # black
            print("✅ Logo color changed to black.")

            # Wait for the cache manager to initialize
            await page.wait_for_function("() => globalThis.ConfigStreamCache && typeof cacheManager !== 'undefined'", timeout=10000)
            print("✅ Cache manager and config are available.")

            # Check for the service worker registration message in the console
            await asyncio.sleep(2) # Give the service worker time to register
            assert any("Service Worker registered successfully" in msg for msg in msgs)
            print("✅ Service Worker registration message found in console.")

            # Take a screenshot
            await page.screenshot(path="jules-scratch/verification/verification.png")
            print("📸 Screenshot taken.")

        except (TimeoutError, AssertionError) as e:
            print(f"❌ Verification script failed: {e}")

        finally:
            print("\n--- Captured Console Logs ---")
            if msgs:
                for msg in msgs:
                    print(f"  - {msg}")
            else:
                print("  (No console messages were captured)")
            print("---------------------------\n")
            await browser.close()
            # Re-assert to ensure the script fails if the condition wasn't met
            assert any("Service Worker registered successfully" in msg for msg in msgs), "Verification failed."

if __name__ == "__main__":
    asyncio.run(main())
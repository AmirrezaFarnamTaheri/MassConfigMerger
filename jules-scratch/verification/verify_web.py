from playwright.sync_api import sync_playwright, expect

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            print("Navigating to /aggregate...")
            # Use a long timeout as this can take a while
            page.goto("http://localhost:5000/aggregate", timeout=240000)
            print("Aggregation finished.")

            print("Navigating to /merge...")
            # Use a long timeout as this can take a while
            page.goto("http://localhost:5000/merge", timeout=240000)
            print("Merge finished.")

            print("Navigating to /report...")
            page.goto("http://localhost:5000/report")

            # Expect the report to contain a title
            expect(page.locator("h1")).to_have_text("VPN Report")

            page.screenshot(path="jules-scratch/verification/verification.png")
            print("Screenshot taken.")
        except Exception as e:
            print(f"An error occurred: {e}")
            page.screenshot(path="jules-scratch/verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run()
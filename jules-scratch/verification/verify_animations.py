import asyncio
import http.server
import socketserver
import threading
import os
from playwright.async_api import async_playwright, expect

PORT = 8000

# This allows the address to be reused, preventing "Address already in use" errors.
socketserver.TCPServer.allow_reuse_address = True

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.getcwd(), **kwargs)

async def main():
    httpd = socketserver.TCPServer(("", PORT), Handler)

    # Run server in a background thread
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print("serving at port", PORT)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 1. Verify index.html
            await page.goto(f"http://localhost:{PORT}/index.html")
            await expect(page.locator("#loading-screen")).to_be_hidden(timeout=15000)
            await expect(page.locator("#totalConfigs")).not_to_have_class("loading", timeout=10000)
            await asyncio.sleep(1.5)
            await page.screenshot(path="jules-scratch/verification/01_index_page.png")

            await browser.close()
    finally:
        print("Shutting down server...")
        httpd.shutdown()
        httpd.server_close()
        server_thread.join()
        print("Server shut down.")


if __name__ == "__main__":
    asyncio.run(main())
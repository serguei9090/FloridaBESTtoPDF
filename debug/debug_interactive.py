"""
Interactive Debugger for FloridaBESTtoPDF
Opens a visible browser with the same URL, viewport, and CSS injections as the main script.
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


def get_target_url(page_num=39):
    script_dir = Path(__file__).parent
    # Try loading .env from the debug folder first, then parent if needed
    load_dotenv(script_dir / ".env")
    load_dotenv(script_dir.parent / ".env")
    template = os.getenv(
        "BASE_URL_TEMPLATE",
        "https://bim.easyaccessmaterials.com/programs/fl2023/{grade}/page{page:04d}.xhtml",
    )
    grade = os.getenv("DEFAULT_GRADE", "grade1")

    url = template.replace("{grade}", grade)
    if "{page" in url:
        # Simple replacement for the format string
        import re

        url = re.sub(r"\{page:0\d+d\}", f"{page_num:04d}", url)
        url = url.replace("{page}", str(page_num))
    return url


def start_debug(page_num=39):
    url = get_target_url(page_num)

    with sync_playwright() as pw:
        print(f"🚀 Launching browser for URL: {url}")
        browser = pw.chromium.launch(headless=False, args=["--force-color-profile=srgb"])
        context = browser.new_context()
        page = context.new_page()

        # Match main.py viewport
        page.set_viewport_size({"width": 1240, "height": 1754})

        # Navigate
        page.goto(url, wait_until="networkidle")
        time.sleep(1)

        # Logic from main.py: Detect container
        detected_selector = page.evaluate(
            """
            () => {
                const container = document.querySelector('[id^="PageContainer"]');
                return container ? `#${container.id}` : null;
            }
            """
        )
        selector = detected_selector or "#PageContainer3"
        print(f"📍 Detected container: {selector}")

        # Logic from main.py: Inject CSS
        print("💉 Injecting CSS...")
        page.add_style_tag(
            content="""
            html, body {
                margin: 0 !important;
                padding: 0 !important;
                background: #ffffff !important;
            }
            """
        )

        print("\n✨ Browser is ready!")
        print("- You can inspect the page (F12)")
        print("- You can see how the CSS affects the layout")
        print("- Press Ctrl+C in this terminal or close the browser window when done.")

        # Keep window open until closed
        try:
            while True:
                time.sleep(1)
                # Check if page is closed
                if page.is_closed():
                    break
        except KeyboardInterrupt:
            print("\n👋 Closing browser...")
        finally:
            browser.close()


if __name__ == "__main__":
    import sys

    page_to_test = 39
    if len(sys.argv) > 1:
        try:
            page_to_test = int(sys.argv[1])
        except ValueError:
            pass

    start_debug(page_to_test)

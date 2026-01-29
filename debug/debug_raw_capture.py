"""
Debug script to capture the PageContainer as a PNG WITHOUT any CSS injections.
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
        import re

        url = re.sub(r"\{page:0\d+d\}", f"{page_num:04d}", url)
        url = url.replace("{page}", str(page_num))
    return url


def capture_raw(page_num=39):
    url = get_target_url(page_num)
    # Save inside the 'debug' folder where the script lives
    script_dir = Path(__file__).parent
    out_dir = script_dir / "debug_output"
    out_dir.mkdir(exist_ok=True)

    with sync_playwright() as pw:
        print(f"🚀 Launching browser for URL: {url}")
        browser = pw.chromium.launch(headless=True, args=["--force-color-profile=srgb"])
        page = browser.new_page()

        # Match main.py viewport
        page.set_viewport_size({"width": 1240, "height": 1754})

        # Navigate
        page.goto(url, wait_until="networkidle")
        time.sleep(2)  # Give it a bit more time for all assets

        # Dynamically detect the PageContainer
        selector = page.evaluate(
            """
            () => {
                const container = document.querySelector('[id^="PageContainer"]');
                return container ? `#${container.id}` : null;
            }
            """
        )

        if not selector:
            print("❌ PageContainer not found!")
            browser.close()
            return

        print(f"📍 Detected container: {selector}")

        # Get bounding box for clipping
        box = page.locator(selector).bounding_box()

        if box:
            out_path = out_dir / f"raw_capture_p{page_num}_{selector[1:]}.png"
            print("📸 Capturing screenshot (No CSS injected)...")
            page.screenshot(path=str(out_path), clip=box)
            print(f"✅ Saved to: {out_path}")
        else:
            print("❌ Could not determine bounding box for container.")

        browser.close()


if __name__ == "__main__":
    import sys

    page_to_test = 39
    if len(sys.argv) > 1:
        try:
            page_to_test = int(sys.argv[1])
        except ValueError:
            pass

    capture_raw(page_to_test)

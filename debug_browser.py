"""
Debug script to open browser and inspect the page with same settings as main.py
"""
from playwright.sync_api import sync_playwright
import time

# Page to debug
PAGE_URL = "https://bim.easyaccessmaterials.com/programs/fl2023/grade1/page0039.xhtml"

def debug_page():
    with sync_playwright() as pw:
        # Launch HEADED browser (visible)
        browser = pw.chromium.launch(
            headless=False,
            args=["--force-color-profile=srgb"]
        )
        
        page = browser.new_page()
        
        # Same viewport as main.py
        page.set_viewport_size({"width": 1240, "height": 1754})
        
        print(f"Loading: {PAGE_URL}")
        page.goto(PAGE_URL, wait_until="networkidle", timeout=30000)
        
        # Wait for content
        time.sleep(1)
        
        # Get page selector info
        selector = '#PageContainer3'
        bg_info = page.evaluate(
            f"""
            () => {{
                const el = document.querySelector('{selector}') || document.body;
                if (!el) return null;
                const style = window.getComputedStyle(el);
                return {{
                    hasEl: !!document.querySelector('{selector}'),
                    backgroundImage: style.backgroundImage || null,
                    width: el.getBoundingClientRect().width,
                    height: el.getBoundingClientRect().height,
                    x: el.getBoundingClientRect().x,
                    y: el.getBoundingClientRect().y
                }};
            }}
            """
        )
        
        print("\n=== Element Info ===")
        print(f"Selector: {selector}")
        print(f"Found: {bg_info.get('hasEl') if bg_info else 'No'}")
        print(f"Background: {bg_info.get('backgroundImage') if bg_info else 'None'}")
        print(f"Dimensions: {bg_info.get('width')}x{bg_info.get('height')}")
        print(f"Position: ({bg_info.get('x')}, {bg_info.get('y')})")
        
        # Apply the same CSS as main.py
        print("\n=== Applying CSS Injections ===")
        page.add_style_tag(
            content=f"""
            html, body {{ margin: 0 !important; padding: 0 !important; background: #ffffff !important; }}
            img {{ max-width: 100% !important; height: auto !important; display: block !important; margin: 0 auto !important; }}
            .content-wrapper, main, article {{ width: 100% !important; max-width: none !important; margin: 0 !important; padding: 0 !important; background: #ffffff !important; }}
            {selector} {{ background-position: center !important; background-repeat: no-repeat !important; background-size: contain !important; }}
            """
        )
        
        print("\nBrowser is open. Inspect the page in the browser window.")
        print("The CSS injections from main.py have been applied.")
        print("\nPress Enter to close the browser...")
        input()
        
        browser.close()

if __name__ == "__main__":
    debug_page()

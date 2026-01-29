"""
Debug script to compare rendering with and without CSS injections
"""
from playwright.sync_api import sync_playwright
import time
from pathlib import Path

PAGE_URL = "https://bim.easyaccessmaterials.com/programs/fl2023/grade1/page0039.xhtml"
OUTPUT_DIR = Path("debug_screenshots")
OUTPUT_DIR.mkdir(exist_ok=True)

def capture_with_without_css():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page()
        page.set_viewport_size({"width": 1240, "height": 1754})
        
        print(f"Loading: {PAGE_URL}")
        page.goto(PAGE_URL, wait_until="networkidle", timeout=30000)
        time.sleep(1)
        
        # Screenshot 1: Original page (no CSS)
        print("\n1. Taking screenshot WITHOUT CSS injections...")
        selector = '#PageContainer3'
        
        try:
            box = page.locator(selector).bounding_box()
            if box:
                page.screenshot(
                    path=str(OUTPUT_DIR / "01_original.png"),
                    clip={
                        "x": int(box["x"]),
                        "y": int(box["y"]),
                        "width": int(box["width"]),
                        "height": int(box["height"])
                    }
                )
                print(f"   Saved: {OUTPUT_DIR / '01_original.png'}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Screenshot 2: With main.py CSS
        print("\n2. Applying main.py CSS injections...")
        page.add_style_tag(
            content=f"""
            html, body {{ margin: 0 !important; padding: 0 !important; background: #ffffff !important; }}
            img {{ max-width: 100% !important; height: auto !important; display: block !important; margin: 0 auto !important; }}
            .content-wrapper, main, article {{ width: 100% !important; max-width: none !important; margin: 0 !important; padding: 0 !important; background: #ffffff !important; }}
            {selector} {{ background-position: center !important; background-repeat: no-repeat !important; background-size: contain !important; }}
            """
        )
        
        time.sleep(0.5)
        
        try:
            box = page.locator(selector).bounding_box()
            if box:
                page.screenshot(
                    path=str(OUTPUT_DIR / "02_with_main_css.png"),
                    clip={
                        "x": int(box["x"]),
                        "y": int(box["y"]),
                        "width": int(box["width"]),
                        "height": int(box["height"])
                    }
                )
                print(f"   Saved: {OUTPUT_DIR / '02_with_main_css.png'}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Screenshot 3: With TestA.py approach (print media)
        print("\n3. Testing with print media emulation...")
        page.emulate_media(media="print")
        time.sleep(0.5)
        
        try:
            box = page.locator(selector).bounding_box()
            if box:
                page.screenshot(
                    path=str(OUTPUT_DIR / "03_with_print_media.png"),
                    clip={
                        "x": int(box["x"]),
                        "y": int(box["y"]),
                        "width": int(box["width"]),
                        "height": int(box["height"])
                    }
                )
                print(f"   Saved: {OUTPUT_DIR / '03_with_print_media.png'}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Get computed styles for debugging
        print("\n4. Checking computed styles on text elements...")
        text_styles = page.evaluate("""
            () => {
                const container = document.querySelector('#PageContainer3');
                if (!container) return null;
                
                const texts = container.querySelectorAll('p, div, span, text');
                const styles = [];
                
                for (let i = 0; i < Math.min(5, texts.length); i++) {
                    const el = texts[i];
                    const computed = window.getComputedStyle(el);
                    styles.push({
                        tag: el.tagName,
                        position: computed.position,
                        display: computed.display,
                        top: computed.top,
                        left: computed.left,
                        transform: computed.transform,
                        textContent: el.textContent.substring(0, 30)
                    });
                }
                
                return styles;
            }
        """)
        
        if text_styles:
            for idx, style in enumerate(text_styles):
                print(f"\n   Element {idx + 1}:")
                for key, value in style.items():
                    print(f"      {key}: {value}")
        
        browser.close()
        
        print(f"\n✅ Screenshots saved to: {OUTPUT_DIR}/")
        print("Compare the three images to identify the issue.")

if __name__ == "__main__":
    capture_with_without_css()

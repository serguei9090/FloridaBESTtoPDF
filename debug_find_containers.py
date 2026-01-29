"""
Quick script to find available containers on the page
"""
from playwright.sync_api import sync_playwright
import time

PAGE_URL = "https://bim.easyaccessmaterials.com/programs/fl2023/grade1/page0039.xhtml"

def find_containers():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.set_viewport_size({"width": 1240, "height": 1754})
        
        print(f"Loading: {PAGE_URL}")
        page.goto(PAGE_URL, wait_until="networkidle", timeout=30000)
        time.sleep(1)
        
        # Find all container elements
        containers = page.evaluate("""
            () => {
                const elements = document.querySelectorAll('[id], [class*="container"], [class*="page"], [class*="content"]');
                const info = [];
                
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 100 && rect.height > 100) {  // Only significant elements
                        info.push({
                            tag: el.tagName,
                            id: el.id || '',
                            classes: el.className || '',
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            x: Math.round(rect.x),
                            y: Math.round(rect.y)
                        });
                    }
                });
                
                return info;
            }
        """)
        
        print("\n=== Found Containers (>100x100px) ===")
        for idx, el in enumerate(containers[:15]):  # Show first 15
            print(f"\n{idx + 1}. {el['tag']}")
            if el['id']:
                print(f"   ID: {el['id']}")
            if el['classes']:
                print(f"   Classes: {el['classes']}")
            print(f"   Size: {el['width']}x{el['height']}")
            print(f"   Pos: ({el['x']}, {el['y']})")
        
        browser.close()

if __name__ == "__main__":
    find_containers()

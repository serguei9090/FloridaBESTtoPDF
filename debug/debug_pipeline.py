"""
Complete pipeline using the 'raw' capture method (no CSS injections).
Captures PNG, applies B&W (optional), and generates PDF.
"""
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from PIL import Image, ImageEnhance, ImageOps

try:
    import img2pdf
except ImportError:
    img2pdf = None

def get_target_url(page_num=39):
    load_dotenv()
    template = os.getenv("BASE_URL_TEMPLATE", "https://bim.easyaccessmaterials.com/programs/fl2023/{grade}/page{page:04d}.xhtml")
    grade = os.getenv("DEFAULT_GRADE", "grade1")
    
    url = template.replace("{grade}", grade)
    if "{page" in url:
        import re
        url = re.sub(r'\{page:0\d+d\}', f"{page_num:04d}", url)
        url = url.replace("{page}", str(page_num))
    return url

def apply_bw_effect(input_path: Path, output_path: Path):
    print(f"🌓 Applying B&W effect to {input_path.name}...")
    with Image.open(input_path) as img:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        # Same logic as main.py
        img = ImageEnhance.Brightness(img).enhance(0.7)
        img = ImageEnhance.Contrast(img).enhance(1.6)
        img = ImageOps.grayscale(img)
        img.save(output_path, "PNG", compress_level=6)

def run_pipeline(page_num=39):
    url = get_target_url(page_num)
    # Save inside the 'debug' folder where the script lives
    script_dir = Path(__file__).parent
    out_dir = script_dir / "output_debug"
    out_dir.mkdir(exist_ok=True)
    
    raw_dir = out_dir / "raw"
    proc_dir = out_dir / "processed"
    pdf_dir = out_dir / "pdfs"
    
    for d in [raw_dir, proc_dir, pdf_dir]:
        d.mkdir(exist_ok=True)
    
    with sync_playwright() as pw:
        print(f"🚀 Launching browser for URL: {url}")
        browser = pw.chromium.launch(headless=True, args=["--force-color-profile=srgb"])
        page = browser.new_page()
        page.set_viewport_size({"width": 1240, "height": 1754})
        
        page.goto(url, wait_until="networkidle")
        time.sleep(2)
        
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
        box = page.locator(selector).bounding_box()
        
        if box:
            img_path = raw_dir / f"page{page_num:04d}.png"
            print(f"📸 Capturing RAW image...")
            page.screenshot(path=str(img_path), clip=box)
            
            # 2. Process to B&W
            bw_path = proc_dir / f"page{page_num:04d}_bw.png"
            apply_bw_effect(img_path, bw_path)
            
            # 3. Create PDF
            if img2pdf:
                # Color PDF
                color_pdf = pdf_dir / f"page{page_num:04d}_color.pdf"
                print(f"📄 Creating Color PDF...")
                with open(color_pdf, "wb") as f:
                    f.write(img2pdf.convert(str(img_path)))
                
                # B&W PDF
                bw_pdf = pdf_dir / f"page{page_num:04d}_bw.pdf"
                print(f"📄 Creating B&W PDF...")
                with open(bw_pdf, "wb") as f:
                    f.write(img2pdf.convert(str(bw_path)))
                
                print(f"\n✅ All set! Files created in '{out_dir}/'")
                print(f"- RAW: {img_path}")
                print(f"- B&W: {bw_path}")
                print(f"- Color PDF: {color_pdf}")
                print(f"- B&W PDF: {bw_pdf}")
            else:
                print("⚠️ img2pdf not installed, skipping PDF step.")
        
        browser.close()

if __name__ == "__main__":
    import sys
    p = 39
    if len(sys.argv) > 1:
        try: p = int(sys.argv[1])
        except: pass
    run_pipeline(p)

"""
URL page iterator utility

Given a URL like:
  https://bim.easyaccessmaterials.com/programs/fl2023/gradek/page0001.xhtml

This script replaces the last numeric sequence in the URL with a zero-padded page
number and exports the pages as PNG images.

Usage examples:
  python test.py "https://.../page0001.xhtml" --start 1 --count 5 --out-dir imgs
  python test.py "https://.../page0001.xhtml" --start 1 --end 20 --img-format png

If the URL doesn't contain digits, you can instead provide a pattern using
{page} and a width: ".../page{page:04d}.xhtml" (then width derives from format)
"""

from __future__ import annotations

import argparse
import re
import sys
import os
from pathlib import Path
from typing import Iterator, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: 'python-dotenv' not installed. Skipping .env loading.", file=sys.stderr)

try:
    import requests
except Exception:
    requests = None  # optional; only required for --check-head

try:
    from PIL import Image, ImageEnhance, ImageOps
except ImportError:
    Image = None
    print("Warning: 'Pillow' not installed. Black-white processing will be disabled.", file=sys.stderr)

try:
    import img2pdf
except ImportError:
    img2pdf = None
    print("Warning: 'img2pdf' not installed. PDF generation will be disabled.", file=sys.stderr)


def replace_last_number(url: str, n: int, width: Optional[int] = None) -> str:
    """Replace the last contiguous digit-sequence in `url` with n, zero-padded.

    If width is None, the width is taken from the length of that digit sequence.
    Raises ValueError if no digit sequence is present.
    """
    matches = list(re.finditer(r"\d+", url))
    if not matches:
        raise ValueError("No numeric sequence found in URL to replace")
    last = matches[-1]
    original = last.group(0)
    if width is None:
        width = len(original)
    return url[: last.start()] + str(n).zfill(width) + url[last.end() :]


def generate_urls(
    template_url: str, start: int, end: Optional[int] = None, count: Optional[int] = None
) -> Iterator[str]:
    """Generate URLs from start to end (inclusive) or start..start+count-1.

    If template_url contains a format placeholder like {page:04d}, use that.
    Otherwise replace the last numeric sequence.
    """
    # detect python-style format placeholder
    if "{page" in template_url:
        # find width if provided
        fmt_match = re.search(r"\{page(?::0?(\d+)d)?\}", template_url)
        if fmt_match:
            width = int(fmt_match.group(1)) if fmt_match.group(1) else 0
        else:
            width = 0

        if end is None and count is None:
            raise ValueError("Either --end or --count must be provided when using {page}")
        if end is None:
            end = start + (count or 0) - 1

        for i in range(start, end + 1):
            if width:
                yield template_url.format(page=i)
            else:
                # no explicit width, just insert integer
                yield template_url.replace("{page}", str(i))
        return

    # otherwise, replace last numeric sequence
    # determine original width from last numeric sequence
    matches = list(re.finditer(r"\d+", template_url))
    if not matches:
        raise ValueError(
            "Template URL contains no digits and no {page} placeholder. Provide one of those."
        )
    original = matches[-1].group(0)
    width = len(original)

    if end is None and count is None:
        raise ValueError("Either --end or --count must be provided")
    if end is None:
        end = start + (count or 0) - 1

    for i in range(start, end + 1):
        yield replace_last_number(template_url, i, width)


def head_check(url: str, timeout: float = 6.0) -> int:
    """Return HTTP status for HEAD (falls back to GET if HEAD not allowed).
    If requests isn't installed, raise RuntimeError.
    """
    if requests is None:
        raise RuntimeError("requests library not available; install it to use --check-head")
    try:
        r = requests.head(url, allow_redirects=True, timeout=timeout)
        return r.status_code
    except Exception:
        # try GET as fallback
        try:
            r = requests.get(url, stream=True, timeout=timeout)
            r.close()
            return r.status_code
        except Exception:
            return 0


def apply_white_black_effect(input_path: Path, output_path: Path) -> bool:
    """Apply Photoshop-like black & white effect: brightness/contrast adjustment + grayscale.
    
    Steps:
    1. Reduce brightness by ~30% (Photoshop -57)
    2. Increase contrast by ~60% (Photoshop 65)
    3. Convert to grayscale
    """
    if Image is None:
        print("Pillow not available, skipping black-white processing.", file=sys.stderr)
        return False
    
    try:
        with Image.open(input_path) as img:
            # Convert to RGB if needed (handles RGBA, P mode, etc.)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            # Step 1: Apply brightness reduction (~30% darker)
            enhancer_b = ImageEnhance.Brightness(img)
            img = enhancer_b.enhance(0.7)
            
            # Step 2: Apply contrast boost (~60% increase)
            enhancer_c = ImageEnhance.Contrast(img)
            img = enhancer_c.enhance(1.6)
            
            # Step 3: Convert to grayscale
            img = ImageOps.grayscale(img)
            
            # Save as PNG
            img.save(output_path, "PNG", compress_level=6)
        return True
    except Exception as e:
        print(f"Black-white processing error for {input_path}: {e}", file=sys.stderr)
        return False


def convert_images_to_pdf(image_dir: Path, pdf_dir: Path, merge_all: bool = False, output_name: str = "combined.pdf") -> bool:
    """Convert images to PDFs. Optionally merge all into one PDF."""
    if img2pdf is None:
        print("img2pdf not available, skipping PDF generation.", file=sys.stderr)
        return False
    
    try:
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all PNG images sorted by filename
        images = sorted(image_dir.glob("*.png"))
        if not images:
            print(f"No images found in {image_dir}", file=sys.stderr)
            return False
        
        if merge_all:
            # Combine all images into a single PDF
            output_path = pdf_dir / output_name
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert([str(img) for img in images]))
            print(f"Created combined PDF: {output_path}")
        else:
            # Create individual PDFs
            for img_path in images:
                pdf_path = pdf_dir / f"{img_path.stem}.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(img2pdf.convert(str(img_path)))
                print(f"Created PDF: {pdf_path}")
        
        return True
    except Exception as e:
        print(f"PDF generation error: {e}", file=sys.stderr)
        return False


def clear_output_directories(dirs: list[Path]) -> None:
    """Clear all PNG and PDF files from the specified directories."""
    for directory in dirs:
        if not directory.exists():
            continue
        
        # Clear PNG files
        for png_file in directory.glob("*.png"):
            try:
                png_file.unlink()
                print(f"Deleted: {png_file}")
            except Exception as e:
                print(f"Failed to delete {png_file}: {e}", file=sys.stderr)
        
        # Clear PDF files
        for pdf_file in directory.glob("*.pdf"):
            try:
                pdf_file.unlink()
                print(f"Deleted: {pdf_file}")
            except Exception as e:
                print(f"Failed to delete {pdf_file}: {e}", file=sys.stderr)


def generate_image_playwright(
    url: str,
    out_path: Path,
    img_format: str = "png",
    timeout: int = 30000,
    page_selector: Optional[str] = None,
    clip_padding: int = 0,
    full_page: bool = False,
    inject_css: bool = True,
) -> bool:
    """Render page to image using Playwright. img_format: 'png' or 'jpeg'."""
    try:
        from playwright.sync_api import sync_playwright
        import time

        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--force-color-profile=srgb"])
            page = browser.new_page()
            # viewport close to A4 ratio for consistent scaling
            page.set_viewport_size({"width": 1240, "height": 1754})

            page.goto(url, wait_until="networkidle", timeout=timeout)

            # Wait a bit for dynamic content
            time.sleep(1)

            # Dynamically detect the PageContainer (e.g., #PageContainer39, #PageContainer40, etc.)
            if page_selector:
                selector = page_selector
            else:
                # Try to find PageContainer with any number
                detected_selector = page.evaluate(
                    """
                    () => {
                        // Look for PageContainer with any number
                        const container = document.querySelector('[id^="PageContainer"]');
                        return container ? `#${container.id}` : null;
                    }
                    """
                )
                selector = detected_selector or '#PageContainer3'  # Fallback to old default
            
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

            # Inject CSS to ensure white page background fallback and proper image scaling
            if inject_css:
                page.add_style_tag(
                    content=f"""
                    html, body {{ margin: 0 !important; padding: 0 !important; background: #ffffff !important; }}
                    img {{ display: block !important; }}
                    .content-wrapper, main, article {{ width: 100% !important; max-width: none !important; margin: 0 !important; padding: 0 !important; background: #ffffff !important; }}
                    {selector} {{ background-position: top left !important; background-repeat: no-repeat !important; background-size: contain !important; }}
                    """
                )

            # If there is a background image on PageContainer3, ensure it is preserved and sized to cover the element
            clip = None
            if bg_info and bg_info.get("backgroundImage") and bg_info.get("backgroundImage") != 'none':
                # Extract URL from background-image value
                bg_url = None
                m = None
                try:
                    import re as _re

                    m = _re.search(r'url\((?:"|\')?(.*?)(?:"|\')?\)', bg_info["backgroundImage"])
                except Exception:
                    m = None
                if m:
                    bg_url = m.group(1)

                if bg_url and inject_css:
                    # Force the background-image explicitly and make it cover the element
                    page.add_style_tag(content=f"{selector} {{ background-image: url('{bg_url}') !important; background-size: cover !important; background-color: #ffffff !important; }}")

                # Clip to the element's bounding box so screenshot contains only the page
                try:
                    box = page.locator(selector).bounding_box()
                    if box:
                        # bounding_box values can be float; convert to ints
                        clip = {"x": int(box["x"]), "y": int(box["y"]), "width": int(box["width"]), "height": int(box["height"]) }
                except Exception:
                    clip = None

            # Take screenshot
            screenshot_args = {
                "path": str(out_path),
                "type": "jpeg" if img_format.lower() in ("jpeg", "jpg") else "png",
                "full_page": full_page
            }
            
            if img_format.lower() in ("jpeg", "jpg"):
                screenshot_args["quality"] = 90

            if not full_page and clip:
                # Add padding to clip area if specified
                screenshot_args["clip"] = {
                    "x": float(clip["x"] - clip_padding),
                    "y": float(clip["y"] - clip_padding),
                    "width": float(clip["width"] + (clip_padding * 2)),
                    "height": float(clip["height"] + (clip_padding * 2))
                }

            page.screenshot(**screenshot_args)
            browser.close()
        return True
    except Exception as e:
        print(f"Image generation error: {e}", file=sys.stderr)
        return False


def main(argv: Optional[list[str]] = None) -> int:
    # Load defaults from env
    env_base_url_template = os.getenv("BASE_URL_TEMPLATE")
    env_default_grade = os.getenv("DEFAULT_GRADE")
    env_start = os.getenv("START_PAGE")
    env_end = os.getenv("END_PAGE")
    env_count = os.getenv("COUNT")
    env_img_format = os.getenv("IMG_FORMAT", "png")
    
    # Processing flags
    clear_output_at_start = os.getenv("CLEAR_OUTPUT_AT_START", "false").lower() == "true"
    enable_white_black = os.getenv("ENABLE_WHITE_BLACK", "false").lower() == "true"
    enable_pdf = os.getenv("ENABLE_PDF", "false").lower() == "true"
    enable_color_pdf = os.getenv("ENABLE_COLOR_PDF", "false").lower() == "true"
    enable_one_pdf = os.getenv("ENABLE_ONE_PDF", "false").lower() == "true"
    
    # PDF naming
    pdf_name = os.getenv("PDF_NAME", "combined")
    
    # Output directories
    env_out_dir_raw = os.getenv("OUTPUT_DIR_RAW", "output/imgs_raw")
    env_out_dir_processed = os.getenv("OUTPUT_DIR_PROCESSED", "output/imgs_processed")
    env_out_dir_pdf = os.getenv("OUTPUT_DIR_PDF", "output/pdfs")
    
    # Clear output directories if enabled
    if clear_output_at_start:
        print("=== Clearing output directories ===")
        clear_output_directories([
            Path(env_out_dir_raw),
            Path(env_out_dir_processed),
            Path(env_out_dir_pdf)
        ])

    # Construct default URL if possible
    default_url = None
    if env_base_url_template:
        try:
            # If we represent grade in the template, utilize it.
            # Example: https://.../{grade}/page{page:04d}.xhtml
            # We partially format it to inject the grade, leaving {page} for later.
            # However, standard python format() might complain about unused keys or missing {page} arg if we don't be careful.
            # So we use a simple replace if {grade} exists.
            if "{grade}" in env_base_url_template and env_default_grade:
                default_url = env_base_url_template.replace("{grade}", env_default_grade)
            else:
                default_url = env_base_url_template
        except Exception:
             pass

    p = argparse.ArgumentParser(description="Generate iterated page URLs and export to images")
    p.add_argument("url", nargs="?", default=default_url, help="Template URL or URL containing a numeric page to replace")
    p.add_argument("--start", "-s", type=int, default=int(env_start) if env_start else None, help="Start page (default: value found in URL or 1)")
    p.add_argument("--end", "-e", type=int, default=int(env_end) if env_end else None, help="End page (inclusive)")
    p.add_argument("--count", "-c", type=int, default=int(env_count) if env_count else None, help="Number of pages to generate")
    p.add_argument("--print-only", action="store_true", help="Only print URLs (default)")
    p.add_argument("--check-head", action="store_true", help="Perform HEAD request and print status codes (requires requests)")
    p.add_argument("--limit", "-l", type=int, help="Stop early after this many URLs printed/generated")
    p.add_argument("--out-dir", type=str, default=env_out_dir_raw, help="Output directory for generated images")
    p.add_argument("--img-format", type=str, default=env_img_format, choices=["png","jpeg"], help="Image format (PNG or JPEG)")
    p.add_argument("--img-prefix", type=str, default="page", help="Filename prefix for generated images")
    p.add_argument("--clip-padding", type=int, default=0, help="Add padding in pixels around clipped content")
    p.add_argument("--img-fullpage", action="store_true", help="Capture full page instead of clipping to content")
    p.add_argument("--skip-existing", action="store_true", help="Skip image creation when output file already exists")
    p.add_argument(
        "--disable-css-injection",
        action="store_true",
        help="Do not inject fallback CSS before screenshotting (capture the page as-is)",
    )
    args = p.parse_args(argv)

    if not args.url:
        # Check if we tried to load from env but failed
        if not env_base_url_template:
            print("Error: BASE_URL_TEMPLATE not found in environment (check .env file).", file=sys.stderr)
        if not env_default_grade:
            print("Error: DEFAULT_GRADE not found in environment (check .env file).", file=sys.stderr)
            
        p.error("URL is required. Provide it as an argument or ensure .env is configured correctly.")
        return 1
        
    url = args.url

    # try to deduce start from URL's last number if present
    m = list(re.finditer(r"\d+", url))
    if args.start is not None:
        start = args.start
    elif m:
        start = int(m[-1].group(0))
    else:
        start = 1

    if args.end is None and args.count is None and args.limit is None:
        # default to small demo if nothing provided
        end = start + 9
    else:
        end = args.end

    count = args.count

    gen = generate_urls(url, start, end=end, count=count)

    printed = 0
    
    # Create output directory if we're generating images
    out_dir_path = None
    if not args.print_only:
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            print("Playwright is required for image export. Install playwright and browsers.", file=sys.stderr)
            return 3
            
        out_dir_path = Path(args.out_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)
    for u in gen:
        if args.check_head:
            try:
                status = head_check(u)
            except RuntimeError as exc:
                print("Error: ", exc, file=sys.stderr)
                return 2
            print(f"{u}  -> {status}")
        else:
            print(u)

        # extract last numeric group to use for filename and for selector
        m = list(re.finditer(r"\d+", u))
        if m:
            raw_page = m[-1].group(0)            # e.g. '0003'
            page_str = raw_page                  # keep padded form for filenames
            page_index = str(int(raw_page))      # numeric form without leading zeros for selector
        else:
            page_str = str(printed + 1)
            page_index = page_str

        page_selector = f"#PageContainer{page_index}"

        # Generate image
        if not args.print_only:
            img_name = f"{args.img_prefix}{page_str}.{('jpg' if args.img_format == 'jpeg' else 'png')}"
            img_path = out_dir_path / img_name
            if args.skip_existing and img_path.exists():
                print(f"Skipping existing {img_path}")
            else:
                img_success = generate_image_playwright(
                    u, 
                    img_path, 
                    img_format=args.img_format, 
                    page_selector=page_selector,
                    clip_padding=args.clip_padding,
                    full_page=args.img_fullpage,
                    inject_css=not args.disable_css_injection,
                )
                if img_success:
                    print(f"Wrote image: {img_path}")
                else:
                    print(f"Failed to write image for {u}", file=sys.stderr)

        printed += 1
        if args.limit and printed >= args.limit:
            break

    # === POST-PROCESSING PIPELINE ===
    # After downloading all images, apply optional transformations
    
    if not args.print_only:
        # Determine source directory for processing
        source_dir = Path(args.out_dir)
        
        # Step 1: Apply black-white transformation if enabled
        if enable_white_black:
            print("\n=== Applying black-white transformation ===")
            processed_dir = Path(env_out_dir_processed)
            processed_dir.mkdir(parents=True, exist_ok=True)
            
            raw_images = sorted(source_dir.glob(f"*.{args.img_format}"))
            for img_path in raw_images:
                output_path = processed_dir / img_path.name
                if apply_white_black_effect(img_path, output_path):
                    print(f"Processed: {output_path}")
        
        # Step 2: Generate PDFs
        pdf_dir = Path(env_out_dir_pdf)
        
        # Generate color PDF if enabled
        if enable_color_pdf:
            print("\n=== Generating Color PDF ===")
            color_pdf_name = f"{pdf_name}_color.pdf" if enable_one_pdf else None
            convert_images_to_pdf(
                image_dir=Path(args.out_dir),  # Use raw images
                pdf_dir=pdf_dir,
                merge_all=enable_one_pdf,
                output_name=color_pdf_name or "combined_color.pdf"
            )
        
        # Generate B&W PDF if enabled
        if enable_pdf and enable_white_black:
            print("\n=== Generating Black-White PDF ===")
            bw_pdf_name = f"{pdf_name}_bw.pdf" if enable_one_pdf else None
            convert_images_to_pdf(
                image_dir=Path(env_out_dir_processed),  # Use processed images
                pdf_dir=pdf_dir,
                merge_all=enable_one_pdf,
                output_name=bw_pdf_name or "combined_bw.pdf"
            )
        elif enable_pdf and not enable_white_black:
            # If only PDF enabled without B&W processing, use raw images
            print("\n=== Generating PDF ===")
            pdf_filename = f"{pdf_name}.pdf" if enable_one_pdf else None
            convert_images_to_pdf(
                image_dir=Path(args.out_dir),
                pdf_dir=pdf_dir,
                merge_all=enable_one_pdf,
                output_name=pdf_filename or "combined.pdf"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# empty
"""
URL page iterator utility

Given a URL like:
  https://bim.easyaccessmaterials.com/programs/fl2023/gradek/page0001.xhtml

This script replaces the last numeric sequence in the URL with a zero-padded page
number and prints or (optionally) HEAD-checks each generated URL.

Usage examples:
  python test.py "https://.../page0001.xhtml" --start 1 --count 5
  python test.py "https://.../page0001.xhtml" --start 1 --end 20 --check-head

If the URL doesn't contain digits, you can instead provide a pattern using
{page} and a width: ".../page{page:04d}.xhtml" (then width derives from format)
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator

try:
    import requests
except Exception:
    requests = None  # optional; only required for --check-head

import shutil
import subprocess
from pathlib import Path


def replace_last_number(url: str, n: int, width: int | None = None) -> str:
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
    template_url: str, start: int, end: int | None = None, count: int | None = None
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


def _has_executable(name: str) -> bool:
    return shutil.which(name) is not None


def pdf_backend_available(backend: str) -> bool:
    """Check if a given backend is available on the system."""
    backend = backend.lower()
    if backend == "playwright":
        try:
            return True
        except Exception:
            return False
    if backend == "weasyprint":
        try:
            return True
        except Exception:
            return False
    if backend == "wkhtmltopdf":
        return _has_executable("wkhtmltopdf")
    return False


def choose_backend(preferred: str = "auto") -> str | None:
    if preferred != "auto":
        return preferred if pdf_backend_available(preferred) else None
    # auto: prefer playwright, then weasyprint, then wkhtmltopdf
    for b in ("playwright", "weasyprint", "wkhtmltopdf"):
        if pdf_backend_available(b):
            return b
    return None


def generate_pdf_wkhtmltopdf(url: str, out_path: Path) -> bool:
    cmd = ["wkhtmltopdf", "--enable-local-file-access", url, str(out_path)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def generate_pdf_weasyprint(url: str, out_path: Path) -> bool:
    try:
        from weasyprint import HTML

        HTML(url).write_pdf(str(out_path))
        return True
    except Exception:
        return False


def generate_pdf_playwright(url: str, out_path: Path, timeout: int = 30000) -> bool:
    try:
        import time

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                args=["--force-color-profile=srgb", "--force-color-profile=display"]
            )
            page = browser.new_page()

            # A4-ish viewport (helps with scaling, but not strictly required)
            page.set_viewport_size({"width": 1240, "height": 1754})

            page.goto(url, wait_until="networkidle", timeout=timeout)

            # Inject CSS to kill the gray background, remove margins, and maximize content
            page.add_style_tag(
                content="""
                @page { size: A4; margin: 0; }
                html, body {
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #ffffff !important;
                }
                img {
                    max-width: 100% !important;
                    height: auto !important;
                    display: block !important;
                    margin: 0 auto !important;
                }
                .content-wrapper, main, article {
                    width: 100% !important;
                    max-width: none !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #ffffff !important;
                }
                """
            )

            # Set print media for better print-like rendering
            page.emulate_media(media="print")

            time.sleep(2)  # let images/fonts settle

            page.pdf(
                path=str(out_path),
                width="210mm",  # A4 width
                height="297mm",  # A4 height
                print_background=True,
                prefer_css_page_size=False,  # use the width/height above
                scale=1.0,
                margin={
                    "top": "0mm",
                    "bottom": "0mm",
                    "left": "0mm",
                    "right": "0mm",
                },
            )
            browser.close()
        return True
    except Exception as e:
        print(f"PDF generation error: {e}", file=sys.stderr)
        return False


def generate_image_playwright(
    url: str, out_path: Path, img_format: str = "png", timeout: int = 30000
) -> bool:
    """Render page to image using Playwright. img_format: 'png' or 'jpeg'."""
    try:
        import time

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--force-color-profile=srgb"])
            page = browser.new_page()

            # viewport close to A4 ratio for consistent scaling
            page.set_viewport_size({"width": 1240, "height": 1754})

            page.goto(url, wait_until="networkidle", timeout=timeout)

            # Inject CSS to remove gray background and margins
            page.add_style_tag(
                content="""
                html, body {
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #ffffff !important;
                }
                img {
                    max-width: 100% !important;
                    height: auto !important;
                    display: block !important;
                    margin: 0 auto !important;
                }
                .content-wrapper, main, article {
                    width: 100% !important;
                    max-width: none !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    background: #ffffff !important;
                }
                """
            )
            page.emulate_media(media="print")
            time.sleep(1)

            # Use fullPage to capture entire document; alternatively clip to viewport
            screenshot_kwargs = {"path": str(out_path), "full_page": True}
            if img_format.lower() in ("jpeg", "jpg"):
                screenshot_kwargs.update({"type": "jpeg", "quality": 90})
            else:
                screenshot_kwargs.update({"type": "png"})

            page.screenshot(**screenshot_kwargs)
            browser.close()
        return True
    except Exception as e:
        print(f"Image generation error: {e}", file=sys.stderr)
        return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate iterated page URLs")
    p.add_argument("url", help="Template URL or URL containing a numeric page to replace")
    p.add_argument(
        "--start",
        "-s",
        type=int,
        default=None,
        help="Start page (default: value found in URL or 1)",
    )
    p.add_argument("--end", "-e", type=int, help="End page (inclusive)")
    p.add_argument("--count", "-c", type=int, help="Number of pages to generate")
    p.add_argument("--print-only", action="store_true", help="Only print URLs (default)")
    p.add_argument(
        "--check-head",
        action="store_true",
        help="Perform HEAD request and print status codes (requires requests)",
    )
    p.add_argument(
        "--limit", "-l", type=int, help="Stop early after this many URLs printed/generated"
    )
    p.add_argument(
        "--to-pdf", action="store_true", help="Render each page to PDF using available backend"
    )
    p.add_argument(
        "--out-dir", type=str, default="pdfs", help="Output directory for generated PDFs"
    )
    p.add_argument(
        "--to-png",
        action="store_true",
        help="Render each page to an image (PNG/JPEG) using Playwright",
    )
    p.add_argument(
        "--img-format",
        type=str,
        default="png",
        choices=["png", "jpeg"],
        help="Image format when using --to-png",
    )
    p.add_argument(
        "--img-prefix", type=str, default="page", help="Filename prefix for generated images"
    )
    p.add_argument(
        "--pdf-backend",
        type=str,
        default="auto",
        help="PDF backend: auto, playwright, weasyprint, wkhtmltopdf",
    )
    p.add_argument(
        "--pdf-prefix", type=str, default="page", help="Filename prefix for generated PDFs"
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip PDF creation when output file already exists",
    )
    args = p.parse_args(argv)

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
    backend = None
    out_dir_path = None
    if args.to_pdf:
        backend = choose_backend(args.pdf_backend)
        if backend is None:
            print(
                "No PDF backend available. Install Playwright, WeasyPrint, "
                "or wkhtmltopdf, or specify --pdf-backend.",
                file=sys.stderr,
            )
            return 3
        out_dir_path = Path(args.out_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)
    # prepare image output dir (use same out-dir if specified)
    if args.to_png:
        # require Playwright for PNG export
        if not pdf_backend_available("playwright"):
            print(
                "Playwright backend required for --to-png. Install playwright and browsers.",
                file=sys.stderr,
            )
            return 4
        # ensure out dir exists
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

        # optionally generate PDF
        if args.to_pdf:
            # extract last numeric group to use for filename
            m = list(re.finditer(r"\d+", u))
            if m:
                page_str = m[-1].group(0)
            else:
                # fallback to sequential number
                page_str = str(printed + 1)

            out_name = f"{args.pdf_prefix}{page_str}.pdf"
            out_path = out_dir_path / out_name
            if args.skip_existing and out_path.exists():
                print(f"Skipping existing {out_path}")
            else:
                success = False
                if backend == "playwright":
                    success = generate_pdf_playwright(u, out_path)
                elif backend == "weasyprint":
                    success = generate_pdf_weasyprint(u, out_path)
                elif backend == "wkhtmltopdf":
                    success = generate_pdf_wkhtmltopdf(u, out_path)

                if success:
                    print(f"Wrote PDF: {out_path}")
                else:
                    print(f"Failed to write PDF for {u} using {backend}", file=sys.stderr)

        # optionally generate image
        if args.to_png:
            # extract last numeric group to use for filename
            m = list(re.finditer(r"\d+", u))
            if m:
                page_str = m[-1].group(0)
            else:
                page_str = str(printed + 1)

            fmt = args.img_format if args.img_format == "png" else "jpg"
            img_name = f"{args.img_prefix}{page_str}.{fmt}"
            img_path = out_dir_path / img_name
            if args.skip_existing and img_path.exists():
                print(f"Skipping existing {img_path}")
            else:
                img_success = generate_image_playwright(u, img_path, img_format=args.img_format)
                if img_success:
                    print(f"Wrote image: {img_path}")
                else:
                    print(f"Failed to write image for {u}", file=sys.stderr)

        printed += 1
        if args.limit and printed >= args.limit:
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

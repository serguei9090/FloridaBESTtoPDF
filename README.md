# FloridaBESTtoPDF

A set of utilities to extract pages from Florida B.E.S.T. educational materials (EasyAccessMaterials) and convert them into images (PNG/JPG) or PDFs.

## 🌟 Features

- **Smart Image Extraction (`main.py`)**: 
  - Captures high-quality screenshots of textbook pages.
  - **Dynamic Container Detection**: Automatically finds the correct page content container (e.g., `#PageContainer39`, `#PageContainer40`) for every page.
  - Automatically handles dynamic numbering (e.g., `page0001.xhtml`).
  - Ensures proper scaling and high-fidelity layout capture.
  - Configurable via `.env` file or command-line arguments.
  - Supports dual PDF generation (Color and Black & White) simultaneously.

## 🛠️ Prerequisites

- **Python 3.7+**
- **Playwright** (for rendering pages)

## 📦 Installation (with uv)

This project uses `uv` for dependency management.

1.  **Install `uv`** (if not already installed):
    ```bash
    # On Windows (PowerShell)
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    # On macOS/Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Sync Dependencies**:
    In the project directory, run:
    ```bash
    uv sync
    ```

3.  **Install Playwright Browsers**:
    ```bash
    uv run playwright install chromium
    ```

## ⚙️ Configuration

You can configure default settings using a `.env` file to avoid typing long URLs every time.

1.  Create a `.env` file in the project root (see `.env.template` or below).
2.  Define your variables:

    ```ini
    # .env
    BASE_URL_TEMPLATE=https://bim.easyaccessmaterials.com/programs/fl2023/{grade}/page{page:04d}.xhtml
    DEFAULT_GRADE=gradek
    START_PAGE=1
    COUNT=5
    Last_Page=802
    
    # Processing options - enable advanced features
    CLEAR_OUTPUT_AT_START=true  # Clean output directories before starting
    ENABLE_WHITE_BLACK=true     # Apply black-white transformation
    ENABLE_PDF=true             # Generate B&W PDF (requires ENABLE_WHITE_BLACK)
    ENABLE_COLOR_PDF=true       # Generate color PDF from raw images
    ENABLE_ONE_PDF=true         # Combine all images into one PDF
    
    # PDF naming (used when ENABLE_ONE_PDF=true)
    PDF_NAME=grade1_book        # Base name for PDF files
    
    # Output directories
    OUTPUT_DIR_RAW=output/imgs_raw           # Raw downloaded images
    OUTPUT_DIR_PROCESSED=output/imgs_processed  # Processed (B&W) images
    OUTPUT_DIR_PDF=output/pdfs               # PDF output
    ```

**PDF Naming:**
- When both `ENABLE_PDF` and `ENABLE_COLOR_PDF` are true, two PDFs are generated:
  - `{PDF_NAME}_color.pdf` - Color version from raw images
  - `{PDF_NAME}_bw.pdf` - Black & white version from processed images
- Individual PDFs (when `ENABLE_ONE_PDF=false`) use default naming

## 🎨 Processing Pipeline

The script supports a powerful multi-stage processing pipeline:

1.  **Image Download**: Downloads pages as PNG images to `OUTPUT_DIR_RAW`
2.  **Black-White Transformation** (optional): Applies Photoshop-like effects:
    -   Brightness reduction (~30%)
    -   Contrast boost (~60%)
    -   Grayscale conversion
    -   Outputs to `OUTPUT_DIR_PROCESSED`
3.  **PDF Generation** (optional): Converts images to PDF format
    -   **Color PDF** (`ENABLE_COLOR_PDF`): Generate PDF from raw images
    -   **Black-White PDF** (`ENABLE_PDF` + `ENABLE_WHITE_BLACK`): Generate PDF from processed images
    -   **Merged PDFs** (`ENABLE_ONE_PDF`): Combine all images into single PDFs with custom names
    -   Outputs to `OUTPUT_DIR_PDF`

Enable/disable any stage using the `.env` configuration flags.

## 🚀 Usage

### Extract Images (`main.py`)

Run the script using `uv run`:

**Using defaults from `.env`:**
```bash
uv run main.py
```

**Overriding defaults:**
```bash
# Extract 20 pages starting from page 50
uv run main.py --start 50 --count 20

# Change grade level manually
uv run main.py "https://bim.easyaccessmaterials.com/programs/fl2023/grade2/page0001.xhtml"
```

**Options:**
- `--start <N>`: Start page number.
- `--end <N>`: End page number.
- `--count <N>`: How many pages to process.
- `--out-dir <dir>`: Directory to save images (default: `output/imgs_raw`).
- `--check-head`: Verify URLs exist before processing.
- `--disable-css-injection`: Capture raw page rendering without any CSS modifications.

### 🧹 Linting and Formatting (Ruff)

This project uses **Ruff** for high-performance Python linting and formatting.

**Format code:**
```bash
uv run ruff format .
```

**Check for lint errors:**
```bash
uv run ruff check .
```

**Auto-fix lint errors:**
```bash
uv run ruff check . --fix
```

### 🔍 Debugging Tools (`debug/`)

A dedicated `debug/` folder contains specialized scripts for troubleshooting and testing:

- **`debug_interactive.py`**: Opens a visible browser window with the same CSS and settings as `main.py` for manual inspection.
- **`debug_pipeline.py`**: Runs the complete capture and PDF generation pipeline for a single page using the most stable "raw" capture method.
- **`debug_raw_capture.py`**: Quickly captures a specific page container without any modifications to verify raw layout.

To run a debug script:
```bash
uv run python debug/debug_pipeline.py 39
```

Debug outputs are saved inside `debug/debug_output/` and `debug/output_debug/`.

## 📁 File Structure

- `main.py`: Main Utility - Advanced image extraction with dynamic container detection and dual PDF generation.
- `.env`: Configuration file for defaults and processing options.
- `output/`: Main export directory (images, processed files, PDFs).
- `debug/`: Contained playground for debug scripts and troubleshooting outputs.
- `deprec/`: Folder for deprecated or experimental scripts.
- `pyproject.toml`: Project configuration and Ruff settings.

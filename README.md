# FloridaBESTtoPDF

A set of utilities to extract pages from Florida B.E.S.T. educational materials (EasyAccessMaterials) and convert them into images (PNG/JPG) or PDFs.

## 🌟 Features

- **Smart Image Extraction (`main.py`)**: 
  - Captures high-quality screenshots of textbook pages.
  - Automatically handles dynamic numbering (e.g., `page0001.xhtml`).
  - Removes gray backgrounds and ensures proper scaling.
  - Clips specific content containers (e.g., `#PageContainer3`) to avoid capturing empty margins.
  - Configurable via `.env` file or command-line arguments.

- **PDF/Image Conversion (`TestA.py`)**: 
  - Converts URLs to PDF using multiple backends: **Playwright**, **WeasyPrint**, or **wkhtmltopdf**.
  - Can also generate full-page screenshots.

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

1.  Create a `.env` file in the project root (see `.env.example` or below).
2.  Define your variables:

    ```ini
    # .env
    BASE_URL_TEMPLATE=https://bim.easyaccessmaterials.com/programs/fl2023/{grade}/page{page:04d}.xhtml
    DEFAULT_GRADE=gradek
    START_PAGE=1
    COUNT=5
    # OUTPUT_DIR=imgs
    ```

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
- `--out-dir <dir>`: Directory to save images (default: `imgs`).
- `--check-head`: Verify URLs exist before processing.

## 📁 File Structure

- `main.py`: Main Utility - Advanced image extraction with smart clipping.
- `.env`: Configuration file for defaults.
- `deprec/`: Deprecated utilities (e.g., `TestA.py`).

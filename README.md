# 🔬 AACR Abstract Scraper

This project scrapes abstract information from the AACR Annual Meeting pages hosted on [abstractsonline.com](https://www.abstractsonline.com). It performs a full pipeline: estimating sessions, extracting links, and retrieving abstracts and authors, saving results in `.tsv` format for downstream analysis.

---

## 🚀 Features

- Estimate number of pages per session type
- Scrape links to individual abstract presentations
- Retrieve titles, authors, and abstract text (even if JavaScript-rendered)
- Save results incrementally with checkpointing and log tracking
- Designed for GitHub Codespaces or local Python environments

---

## 🧰 Requirements

- Python 3.8+
- Google Chrome (installed or managed via `webdriver_manager`)
- `pip install -r requirements.txt`

Recommended:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🔧 Usage

All output is written to the `output/aacr` directory by default, and logs are saved per run with timestamped filenames.

### Estimate session sizes
```bash
python aacr_scraper.py --estimate
```

### Run full scraping pipeline (estimate + links + abstracts)
```bash
python aacr_scraper.py --build-all
```

You can control scraper limits:
```bash
python aacr_scraper.py --build-all --max-pages 10 --max-calls-per-scraper-session 20 --wait 120
```

### Test-only commands
```bash
python aacr_scraper.py --test-landing-page
python aacr_scraper.py --test-get-links
python aacr_scraper.py --test-get-abstracts
```

---

## ⚙️ Command-line Arguments

| Flag                                 | Description |
|--------------------------------------|-------------|
| `--estimate`                         | Estimate pages for each AACR session type |
| `--build-all`                        | Full pipeline: estimate → links → abstracts |
| `--test-get-links`                   | Test `get_links` with one page |
| `--test-get-abstracts`               | Test `get_abstracts` and save rendered HTML |
| `--test-landing-page`                | Render and save the first session page |
| `--max-pages`                        | Max pages per scraper function call (default: 10) |
| `--max-calls-per-scraper-session`   | Max iterations per scraper step (default: 20) |
| `--wait`                             | Time (seconds) between calls during `--build-all` |
| `--output`                           | Base output directory (default: `output/aacr`) |
| `--debug`                            | Enable debug mode for verbose logging |

---

## 📁 Output Files

| File | Description |
|------|-------------|
| `session_estimates.tsv`     | Page count per session type |
| `processed_session_pages.tsv` | Tracking file for which pages have been processed |
| `aacr_links.tsv`            | Abstract links, titles, and retrieval status |
| `aacr_abstracts.tsv`        | Full abstract info: title, authors, abstract text |
| `log.txt` / `log_<timestamp>.txt` | Per-run logs with progress and errors |
| `html_dumps/`               | Fallback HTML snapshots for debugging |

---

## 🐛 Troubleshooting

- Chrome must be installed or automatically managed by `webdriver_manager`.
- Scraper uses a headless browser; ensure sandboxing issues are addressed if running locally.
- Retry logic is in place, but occasionally, abstract pages may fail due to rendering delays or embargoes.

---

## 🔄 Coming Soon (Ideas)

- Retry embargoed or failed abstracts on later runs
- Add proxy support to rotate IPs
- Embed author affiliation parsing
- Integrate with a database or downstream NLP analysis

---

## 👨‍🔬 Maintainer

Developed by Ian Donaldson with assistance from ChatGPT ("River").  
For bugs, questions, or contributions — feel free to open an issue or reach out!


# **SITC Parser**

This repository contains a Python-based web scraper that extracts abstracts and metadata from the **Society for Immunotherapy of Cancer (SITC) conference website**. The script uses **Selenium WebDriver** (with stealth techniques) and **BeautifulSoup** for structured data extraction.  This is a minimal project that demonstrates some of the central tools and methods required for a web scraper project.

---

## **1. Setting Up the Environment in GitHub Codespaces**

If you are using **GitHub Codespaces**, the environment is pre-configured using a **devcontainer setup**.

### **How it Works**
- The **`.devcontainer/`** directory contains:
  - **`devcontainer.json`** → Configures the development environment inside Codespaces.
  - **`Dockerfile`** (if applicable) → Defines the container image.
- The **`requirements.txt`** file lists all necessary **Python dependencies**, which are installed automatically.
- The setup also creates a **virtual environment (`venv`)** to ensure package consistency and isolation from the global Python environment.

### **Steps to Get Started**
1. **Open the Repository in GitHub Codespaces**
   - Click the **“Code”** button in GitHub.
   - Select **“Codespaces”** and create a new codespace.

2. **Wait for the Dev Container to Initialize**
   - The **`.devcontainer/devcontainer.json`** will:
     - Install **Python 3**, **Chromium**, **Chromedriver**, and required system libraries.
     - Set up a **virtual environment (`venv`)** automatically.
     - Install all dependencies listed in `requirements.txt`.

3. **Verify the Environment Setup**

   Use Cmd/Ctrl + Shift + P -> View Creation Log to see full logs
   
   Run the following commands inside the Codespace terminal to check installations:
   ```bash
   python3 --version
   pip --version
   chromedriver --version
   ```
   If valid versions appear, the setup is complete.

---

## **2. Setting Up a Standalone Linux Environment**

If you are working on a **Linux machine**, you can set up the environment using **`install_dependencies.sh`** or manually configuring it using `setup.sh`.

### **Method 1: Using `install_dependencies.sh` (Recommended)**
```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```
This script will:
- Install **Python, pip, Chromium, and ChromeDriver**.
- Set up a **virtual environment (`venv`)** for package isolation.
- Install required dependencies from `requirements.txt`.

### **Method 2: Using `setup.sh` Manually**
If you prefer to manually set up the environment, follow these steps:
```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip chromium-chromedriver
python3 -m venv sitc_env
source sitc_env/bin/activate
pip install -r requirements.txt
```
This approach manually installs the necessary tools and sets up a reproducible virtual environment (`venv`).

---

## **3. Basic Usage of `sitc_parser.py`**

To run the SITC parser, execute the following command inside the virtual environment:
```bash
python sitc_parser.py
```

### **Output Files**
- **`sitc_title_auth_link.tsv`** → Contains abstract numbers, titles, authors, and DOI links.
- **`link_abstract.tsv`** → Contains DOI links and structured abstracts (Background, Methods, Results, Conclusions).

These outputs can be analyzed using **pandas** or any spreadsheet software.

---

## **4. Developing a Project for Reproducibility (Codespace & Standalone)**

### **Key Steps for a Reproducible Environment**

#### **(a) Use a Bash Script to Record Installations**
Keep track of dependencies and system setup using a script like `install_dependencies.sh`. This ensures all installations are recorded and can be repeated consistently.

#### **(b) Use `venv` for Package Isolation**
Why?
- Prevents conflicts with system-installed packages.
- Ensures reproducibility across different environments.

How to use `venv`:
```bash
python3 -m venv sitc_env
source sitc_env/bin/activate
```
After activation, all package installations (`pip install`) will be stored inside `sitc_env`.

#### **(c) Create a `requirements.txt` File**
Once the correct configuration is determined, generate a list of installed packages:
```bash
pip freeze > requirements.txt
```
This file can then be used to install dependencies on a new machine:
```bash
pip install -r requirements.txt
```

#### **(d) Create and Use `.devcontainer` for Codespaces**
Once the project is stable, add a **`.devcontainer/`** directory to ensure automatic environment setup for Codespaces users.
- Use `devcontainer.json` to specify dependencies.
- Automate the setup so developers can start coding immediately without manual configuration.

---

## **5. Development Challenges & Lessons Learned**

During the development of this project, several key blockers had to be addressed:

### **(a) Chrome & ChromeDriver Configuration**
- Initially, there were issues with **headless Chrome mode** and **Chromedriver pathing**.
- Solution: **Explicitly specify `chromedriver` path** and **use `selenium-stealth` to bypass bot detection**.

### **(b) Identifying Correct HTML Tags**
- Extracting abstracts required **trial and error** to find the correct **CSS selectors and HTML structure**.
- Solution: **Save raw HTML pages** to debug and adjust parsing logic dynamically.

### **(c) Critical Packages & Why They Were Needed**
- **Selenium** → Automates web interactions to retrieve abstracts.
- **Selenium-Stealth** → Helps bypass anti-bot mechanisms.
- **BeautifulSoup** → Parses HTML for structured data extraction.
- **pandas** → Stores results in a structured format.

### **(d) Other Key Lessons**
- **Use `time.sleep()` intelligently** → Some pages require extra wait time to load dynamic content.
- **Log key variables** → Debugging output (e.g., `print(doi_link)`) helped pinpoint issues.
- **Ensure ChromeDriver matches Chrome version** → Version mismatches caused WebDriver errors.

By following these best practices, the project can be **easily replicated and deployed** on **both Codespaces and standalone Linux environments**. 🚀


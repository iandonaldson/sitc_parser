# 🛠️ AACR Abstract Scraper — Development Guide

This document provides an overview of the core functions in the AACR scraper codebase, their parameters and outputs, followed by a development retrospective, highlighting design choices, problem-solving decisions, and future directions.

---

## 🔍 Function Index

### `set_output_paths(base_path)`
**Purpose**: Generate a dictionary of standardized paths for logs, checkpoints, and output files.  
**Params**:  
- `base_path`: Path object pointing to output directory root.  
**Returns**: Dictionary with keys like `"log"`, `"aacr_links"`, `"aacr_abstracts"` etc.

---

### `get_chrome_options()`
**Purpose**: Configure Chrome options with randomized user agents and window sizes.  
**Returns**: `ChromeOptions` object.

---

### `setup_driver(service, options)`
**Purpose**: Create and return a Selenium driver with stealth settings.  
**Params**:  
- `service`: `webdriver.chrome.service.Service`  
- `options`: Chrome options object  
**Returns**: Selenium WebDriver object.

---

### `safe_get(driver, url, retries=3, wait=10)`
**Purpose**: Attempt to navigate to a URL, retrying on timeouts.  
**Params**:  
- `driver`, `url`, `retries`, `wait`  
**Returns**: Boolean indicating success.

---

### `test_landing_page(driver, url, paths)`
**Purpose**: Save the rendered HTML of the first session page.  
**Params**:  
- `driver`, `url`, `paths` (includes where to save the file)  
**Returns**: None

---

### `fetch_aacr_title_link_from_html(driver, url, session_name, dump_dir, retries=3)`
**Purpose**: Extract presentation links and titles from session pages.  
**Params**:  
- `driver`, `url`, `session_name`, `dump_dir`, `retries`  
**Returns**: DataFrame with columns `["link", "title", "retrieved"]`

---

### `get_total_pages(service, options, url, session_name, dump_dir, retries=3)`
**Purpose**: Determine how many paginated results exist for a session.  
**Returns**: Integer page count or -1 on failure.

---

### `estimate_all_sessions(session_urls, service, options, paths)`
**Purpose**: Save page count estimates for all session types.  
**Returns**: None. Writes `session_estimates.tsv`.

---

### `get_links(...)`
**Purpose**: Navigate each page of each session, extract new abstract links, update `aacr_links.tsv`.  
**Returns**: None. Checkpointed.

---

### `get_abstracts(...)`
**Purpose**: Load individual abstract pages, extract title, authors, abstract text.  
**Returns**: None. Writes/updates `aacr_abstracts.tsv`.

---

### `reset_processed_sessions(paths, session_list)`
**Purpose**: Mark sessions as unprocessed in the tracking file.  
**Returns**: None. Backs up and updates `processed_session_pages.tsv`.

---

### `sync_links_with_abstracts(paths)`
**Purpose**: Mark `retrieved=False` for links not found in `aacr_abstracts.tsv`.  
**Returns**: None.

---

### `reset_embargoed_abstracts(abstracts_path, links_path, reset_missing=False)`
**Purpose**: Reset `retrieved=False` for embargoed or optionally blank abstracts.  
**Returns**: None.

---

## 🧠 Development Retrospective

### a) Key Design Choices

- ✅ **Randomized Profiles**: User agents and viewport dimensions change per run to avoid detection.
- ✅ **Stealth Browser Mode**: `selenium-stealth` masks bot-like behavior.
- ✅ **Checkpointing**: Writes to disk after every step so long jobs can be resumed.
- ✅ **Incremental Output**: TSV format chosen for ease of debugging and compatibility with pandas/Excel.

---

### b) Crux Problems and Solutions

| Challenge | Solution |
|----------|----------|
| Abstract pages randomly failed to render | Added JS-based fallback polling after WebDriverWait |
| Long jobs consumed memory or crashed | Introduced `kill_chromedriver()` and `drop_caches` restarts |
| Silent link failures | `sync_links_with_abstracts()` ensures completeness |
| Missing abstracts due to embargo | `reset_embargoed_abstracts()` allows intelligent retries |
| No obvious way to recover mid-session | `reset_processed_sessions()` + CLI options allow scoped resets |

---

### c) Potential Future Improvements

- 🌐 Add **proxy rotation** to extend scraping sessions and reduce IP throttling
- 📦 Support output to **SQLite or Parquet** instead of TSV
- 🔄 Implement **multi-threading or async IO** for parallel abstract fetching
- 🤖 Train an NLP pipeline to auto-extract **gene-drug-trial** relationships
- 🧪 Add automated **unit tests** and dry-run/test modes

---

### 🧑‍🔬 Maintainer Notes

Created and maintained by Ian Donaldson  
Contributions by ChatGPT ("River")  
Tooling: Python 3, Selenium, pandas, ChromeDriver, BeautifulSoup, `selenium-stealth`

---

For more, see the [README.md](README.md).

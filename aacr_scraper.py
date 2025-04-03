import argparse
import time
import random
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
import sys
import re
import os
import contextlib
import io

try:
    import ssl
except ModuleNotFoundError:
    print("❌ SSL module not found. This environment may be missing required OpenSSL libraries.")
    sys.exit(1)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

class TeeLogger:
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log = open(file_path, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def get_chrome_options():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-features=NetworkService")
    options.add_argument("--remote-debugging-pipe")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return options

def setup_driver(service, options):
    driver = webdriver.Chrome(service=service, options=options)
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver

def safe_get(driver, url, retries=3, wait=10):
    for attempt in range(retries):
        try:
            driver.set_page_load_timeout(60)
            driver.get(url)
            return True
        except TimeoutException:
            print(f"⏱️ Timeout on attempt {attempt + 1} for {url}")
            time.sleep(wait)
    return False

def test_landing_page(driver, url, output_path):
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "test_landing_page.html"

    print(f"Loading landing page: {url}")
    driver.get(url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "body")))
    time.sleep(5)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"✅ Rendered HTML saved to {output_file}")

def fetch_aacr_title_link_from_html(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    base_url = "https://www.abstractsonline.com/pp8/#!/20273/presentation/"

    data = []
    for h1 in soup.find_all("h1", class_="name"):
        data_id = h1.get("data-id")
        title_tag = h1.select_one("span.bodyTitle")
        if data_id and title_tag:
            link = f"{base_url}{data_id}"
            title = title_tag.get_text(strip=True)
            data.append({"link": link, "title": title})

    df = pd.DataFrame(data)
    df["retrieved"] = False
    return df

def extract_session_name(url):
    match = re.search(r"@[^=/]+=(.*?)/", url)
    if match:
        return match.group(1).replace("%20", " ")
    return "Unknown"

def get_total_pages(service, options, url, session_name, dump_dir, retries=3):
    for attempt in range(1, retries + 1):
        driver = setup_driver(service, options)
        try:
            success = safe_get(driver, url)
            if not success:
                raise TimeoutException("Page load timeout")

            WebDriverWait(driver, 20).until(
                EC.text_to_be_present_in_element((By.TAG_NAME, "h1"), "Displaying results")
            )
            time.sleep(2)

            print(f"[DEBUG] Attempt {attempt}: Displaying results located.")
            headings = driver.execute_script("return [...document.querySelectorAll('h1')].map(e => e.innerText)")
            for text in headings:
                print(f"[DEBUG] H1 content: {text}")
                if text.startswith("Displaying results"):
                    match = re.search(r"of (\d[\d,]*)", text)
                    if match:
                        total_results = int(match.group(1).replace(",", ""))
                        return (total_results - 1) // 10 + 1

        except Exception as e:
            print(f"[WARNING] Attempt {attempt} failed for session '{session_name}': {e}")
            html = driver.page_source
            dump_file = dump_dir / f"{session_name.replace(' ', '_')}.html"
            with open(dump_file, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[DEBUG] Dumped HTML for {session_name} to {dump_file}")
        finally:
            driver.quit()

    return -1

def estimate_all_sessions(session_urls, service, options, output_path):
    output_path.mkdir(parents=True, exist_ok=True)
    dump_dir = output_path / "html_dumps"
    dump_dir.mkdir(exist_ok=True)

    estimates_path = output_path / "session_estimates.tsv"
    session_data = []

    if estimates_path.exists():
        print(f"[INFO] Reloading existing estimates from {estimates_path}")
        previous_df = pd.read_csv(estimates_path, sep="\t")
        previous_sessions = dict(zip(previous_df["session"], previous_df["pages"]))
    else:
        previous_sessions = {}

    for session_url in session_urls:
        session_name = extract_session_name(session_url)
        print(f"🔍 Estimating session: {session_name}")

        if session_name in previous_sessions and previous_sessions[session_name] > 0:
            print(f"[SKIP] Already estimated: {session_name} ({previous_sessions[session_name]} pages)")
            session_data.append({"session": session_name, "pages": previous_sessions[session_name]})
            continue

        total_pages = get_total_pages(service, options, session_url, session_name, dump_dir)
        print(f"📄 Estimated pages: {total_pages}")
        session_data.append({"session": session_name, "pages": total_pages})

    df = pd.DataFrame(session_data)
    df.to_csv(estimates_path, sep="\t", index=False)
    print(f"📊 Session estimates saved to {estimates_path}")

def main():
    parser = argparse.ArgumentParser(description="AACR Abstract Scraper")
    parser.add_argument("--test-landing-page", action="store_true", help="Load and save the first landing page's DOM")
    parser.add_argument("--output", type=str, default="output/aacr", help="Path to save outputs")
    parser.add_argument("--parse-html", action="store_true", help="Extract links and titles from saved HTML file")
    parser.add_argument("--html-path", type=str, default="output/aacr/aacr_test_landing_page.html", help="Path to saved HTML file to parse")
    parser.add_argument("--estimate", action="store_true", help="Estimate pages for each session type")
    args = parser.parse_args()

    session_urls = [
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Clinical%20Trials%20Minisymposium/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Clinical%20Trials%20Plenary%20Session/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@AACRPrimaryCategoryAll=ClinicalPosters/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Late-Breaking%20Minisymposium/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Late-Breaking%20Poster%20Session/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Minisymposium/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Poster%20Session/1"
    ]

    output_path = Path(args.output)
    log_path = output_path / "log.txt"
    output_path.mkdir(parents=True, exist_ok=True)

    sys.stdout = TeeLogger(log_path)
    service = Service(ChromeDriverManager().install())
    options = get_chrome_options()

    if args.test_landing_page:
        driver = setup_driver(service, options)
        test_landing_page(driver, session_urls[0], output_path)
        driver.quit()
        return

    if args.parse_html:
        df = fetch_aacr_title_link_from_html(args.html_path)
        df.to_csv(output_path / "aacr_links.tsv", sep="\t", index=False)
        print("✅ Extracted links and titles saved to output/aacr/aacr_links.tsv")
        return

    if args.estimate:
        estimate_all_sessions(session_urls, service, options, output_path)
        return

if __name__ == "__main__":
    main()

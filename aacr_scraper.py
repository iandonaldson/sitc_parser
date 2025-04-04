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
            if DEBUG:
                print(f"[DEBUG] safe_get got {url}")
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

def fetch_aacr_title_link_from_html_x(html_path):
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

def fetch_aacr_title_link_from_html_x(service, options, url, session_name, dump_dir, retries=3):
    for attempt in range(retries):
        try:
            driver = setup_driver(service, options)
            success = safe_get(driver, url)
            if not success:
                raise Exception(f"Failed to load {url} after retries")

            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "body")))
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            base_url = "https://www.abstractsonline.com/pp8/#!/20273/presentation/"
            data = []

            for h1 in soup.find_all("h1", class_="name"):
                data_id = h1.get("data-id")
                title_tag = h1.select_one("span.bodyTitle")
                if data_id and title_tag:
                    link = f"{base_url}{data_id}"
                    title = title_tag.get_text(strip=True)
                    data.append({
                        "session": session_name,
                        "link": link,
                        "title": title,
                        "retrieved": False
                    })

            return pd.DataFrame(data)

        except Exception as e:
            print(f"❌ Error fetching page {url}: {e}")
            dump_dir = Path(dump_dir)
            dump_dir.mkdir(parents=True, exist_ok=True)
            file_name = f"{session_name.replace(' ', '_')}_{url.split('/')[-1]}.html"
            dump_path = dump_dir / file_name
            with open(dump_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source if 'driver' in locals() else f"Failed to render {url}")
        finally:
            if 'driver' in locals():
                driver.quit()

    return pd.DataFrame(columns=["session", "link", "title", "retrieved"])

def fetch_aacr_title_link_from_html(service, options, url, session_name, dump_dir, retries=3):
    if DEBUG:
        print(f"[DEBUG] Trying to fetch url {url} for session {session_name}.")
    driver = setup_driver(service, options)

    try:
        success = safe_get(driver, url)
        if not success:
            raise Exception("Page load failed after retries")

        time.sleep(10)  # ensure JS executes
        soup = BeautifulSoup(driver.page_source, "html.parser")

        base_url = "https://www.abstractsonline.com/pp8/#!/20273/presentation/"
        data = []
        for h1 in soup.find_all("h1", class_="name"):
            data_id = h1.get("data-id")
            title_tag = h1.select_one("span.bodyTitle")
            if data_id and title_tag:
                link = f"{base_url}{data_id}"
                title = title_tag.get_text(strip=True)
                data.append({"link": link, "title": title, "retrieved": False})

        df = pd.DataFrame(data, columns=["link", "title", "retrieved"])
        return df

    except Exception as e:
        print(f"⚠️ Exception in fetch_aacr_title_link_from_html: {e}")
        page_num = url.split("/")[-1]
        safe_session = re.sub(r"\W+", "_", session_name)
        dump_file = dump_dir / f"{safe_session}_PAGE{page_num}.html"
        with open(dump_file, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        if DEBUG:
            print(f"[DEBUG] ❌ Saved failed HTML to {dump_file}")
        return pd.DataFrame(columns=["link", "title", "retrieved"])

    finally:
        driver.quit()

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

            if DEBUG:
                print(f"[DEBUG] Attempt {attempt}: Displaying results located.")
            headings = driver.execute_script("return [...document.querySelectorAll('h1')].map(e => e.innerText)")
            for text in headings:
                if DEBUG:
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
            if DEBUG:
                print(f"[DEBUG] Dumped HTML for {session_name} to {dump_file}")
        finally:
            driver.quit()

    return -1

def estimate_all_sessions(session_urls, service, options, output_path):
    output_path.mkdir(parents=True, exist_ok=True)
    estimates_file = output_path / "session_estimates.tsv"
    session_ok_file = output_path / "session_estimates_OK"

    existing_estimates = pd.DataFrame()
    if estimates_file.exists():
        existing_estimates = pd.read_csv(estimates_file, sep="\t")

    session_data = []
    retried_sessions = []

    for session_url in session_urls:
        session_name = extract_session_name(session_url)
        existing_row = existing_estimates[existing_estimates["session"] == session_name]

        if not existing_row.empty and existing_row.iloc[0]["pages"] > 0:
            session_data.append({"session": session_name, "pages": existing_row.iloc[0]["pages"]})
            continue

        print(f"🔍 Estimating session: {session_name}")
        total_pages = get_total_pages(service, options, session_url)
        print(f"📄 Estimated pages: {total_pages}")

        session_data.append({"session": session_name, "pages": total_pages})
        retried_sessions.append(session_name)

    df = pd.DataFrame(session_data)
    df.to_csv(estimates_file, sep="\t", index=False)
    print(f"📊 Session estimates saved to {estimates_file}")

    if not retried_sessions:
        session_ok_file.touch()
        print(f"✅ All sessions had valid page estimates. Flag file created: {session_ok_file}")

def get_links(session_urls, service, options, output_path, max_pages=1000):
    processed_path = output_path / "processed_session_pages.tsv"
    links_path = output_path / "aacr_links.tsv"
    estimates_path = output_path / "session_estimates.tsv"
    dump_dir = output_path / "html_dumps"
    dump_dir.mkdir(parents=True, exist_ok=True)

    if processed_path.exists():
        processed_df = pd.read_csv(processed_path, sep="\t")
    else:
        if not estimates_path.exists():
            print("❌ session_estimates.tsv not found.")
            return
        estimates_df = pd.read_csv(estimates_path, sep="\t")
        processed_df = pd.DataFrame([
            {"session": row["session"], "page": page, "processed": False}
            for _, row in estimates_df.iterrows()
            for page in range(1, row["pages"] + 1)
        ])
        processed_df.to_csv(processed_path, sep="\t", index=False)

    if links_path.exists():
        aacr_links = pd.read_csv(links_path, sep="\t")
    else:
        aacr_links = pd.DataFrame(columns=["session", "link", "title", "retrieved"])

    seen_links = set(aacr_links["link"])
    new_links = []

    for idx, row in processed_df.iterrows():
        session_name, page_num, processed = row["session"], row["page"], row["processed"]
        if processed or page_num > max_pages:
            continue

        url_base = next((u for u in session_urls if extract_session_name(u) == session_name), None)
        if not url_base:
            print(f"⚠️ No URL found for session {session_name}")
            continue
        url = re.sub(r"/\d+$", f"/{page_num}", url_base)

        try:
            df = fetch_aacr_title_link_from_html(service, options, url, session_name, dump_dir)
            df["session"] = session_name
            df = df[~df["link"].isin(seen_links)]
            new_links.append(df)
            processed_df.loc[idx, "processed"] = True
        except Exception as e:
            print(f"❌ Failed to fetch page {page_num} of {session_name}: {e}")

    if new_links:
        combined_df = pd.concat([aacr_links] + new_links, ignore_index=True)
        links_path.rename(links_path.with_suffix(".bak")) if links_path.exists() else None
        combined_df.to_csv(links_path, sep="\t", index=False)
        print(f"✅ Updated aacr_links.tsv with {sum(len(df) for df in new_links)} new entries")

    processed_path.rename(processed_path.with_suffix(".bak")) if processed_path.exists() else None
    processed_df.to_csv(processed_path, sep="\t", index=False)
    print(f"📌 Checkpoint saved to {processed_path}")


def main():
    parser = argparse.ArgumentParser(description="AACR Abstract Scraper")
    parser.add_argument("--test-landing-page", action="store_true", help="Load and save the first landing page's DOM")
    parser.add_argument("--test-get-links", action="store_true", help="Run get_links with max_pages=1")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--output", type=str, default="output/aacr", help="Path to save outputs")
    parser.add_argument("--parse-html", action="store_true", help="Extract links and titles from saved HTML file")
    parser.add_argument("--html-path", type=str, default="output/aacr/aacr_test_landing_page.html", help="Path to saved HTML file to parse")
    parser.add_argument("--estimate", action="store_true", help="Estimate pages for each session type")
    parser.add_argument("--build_all", action="store_true", help="Estimate and scrape all AACR sessions")
    args = parser.parse_args()

    import datetime  

    session_urls = [
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Clinical%20Trials%20Minisymposium/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Clinical%20Trials%20Plenary%20Session/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@AACRPrimaryCategoryAll=ClinicalPosters/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Late-Breaking%20Minisymposium/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Late-Breaking%20Poster%20Session/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Minisymposium/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Poster%20Session/1"
    ]

    global DEBUG
    DEBUG = args.debug
    output_path = Path(args.output)
    log_path = output_path / "log.txt"
    output_path.mkdir(parents=True, exist_ok=True)

    sys.stdout = TeeLogger(log_path)
    service = Service(ChromeDriverManager().install())
    options = get_chrome_options()

    start_time = datetime.datetime.now()
    print(f"🚀 Started AACR scraper at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

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
    
    if args.test_get_links:
        get_links(session_urls, service, options, output_path, max_pages=640)

    if args.build_all:
        session_ok_file = output_path / "session_estimates_OK"
        attempts = 0
        while not session_ok_file.exists() and attempts < 3:
            print(f"🚧 Running estimate_all_sessions (attempt {attempts + 1})...")
            estimate_all_sessions(session_urls, service, options, output_path)
            attempts += 1
        if not session_ok_file.exists():
            print("❌ Failed to estimate all sessions after 3 attempts.")
            return
        else:
            print("✅ Session estimates OK — ready to scrape.")
        # Optionally continue to scrape all sessions here

    # cleanup
    end_time = datetime.datetime.now()
    elapsed = end_time - start_time
    print(f"✅ Finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')} (Elapsed time: {elapsed})")

    # Rename log.txt to include a timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_backup_path = output_path / f"log_{timestamp}.txt"
    log_path.rename(log_backup_path)



if __name__ == "__main__":
    main()

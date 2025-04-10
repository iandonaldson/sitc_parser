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


import psutil

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

def set_output_paths(base_path):
    logs_path = base_path / "logs"
    logs_path.mkdir(parents=True, exist_ok=True)  # Ensure it exists
    return {
        "output" : base_path,
        "log": logs_path / "log.txt",
        "get_links_finished": base_path / "GET_LINKS_FINISHED",
        "session_estimates_ok": base_path / "SESSION_ESTIMATES_FINISHED",
        "get_abstracts_finished": base_path / "GET_ABSTRACTS_FINISHED",
        "session_estimates": base_path / "session_estimates.tsv",
        "processed_pages": base_path / "processed_session_pages.tsv",
        "aacr_links": base_path / "aacr_links.tsv",
        "aacr_abstracts": base_path / "aacr_abstracts.tsv",
        "html_dumps": base_path / "html_dumps"
    }

def get_chrome_options():
    # Randomize user agent, window size, and optionally incognito mode
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
    USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.89 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.92 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",]
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"user-agent={user_agent}")
    width = random.choice([1024, 1280, 1366, 1440, 1920])
    height = random.choice([768, 800, 900, 1080, 1200])
    options.add_argument(f"--window-size={width},{height}")
    if random.choice([True, False]):
        options.add_argument("--incognito")
    if DEBUG:
        print(f"[DEBUG] Using user agent: {user_agent}")
        print(f"[DEBUG] Window size: {width}x{height}")
    # prevent memory bloat
    # options.add_argument("--single-process")
    options.add_argument("--memory-pressure-off")
    return options

def setup_driver(service, options):
    driver = webdriver.Chrome(service=service, options=options)
    stealth(driver,
        languages=random.choice([["en-US", "en"], ["en-GB", "en"], ["fr-FR", "fr"]]),
        vendor="Google Inc.",
        platform=random.choice(["Win32", "Linux x86_64", "MacIntel"]),
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver

def kill_chromedriver():
    for proc in psutil.process_iter(['pid', 'name']):
        if 'chromedriver' in proc.info['name']:
            try:
                proc.kill()
            except Exception as e:
                print(f"[DEBUG] Could not kill {proc.info['pid']}: {e}")

def log_memory():
    mem = psutil.virtual_memory()
    print(f"[DEBUG] Total: {mem.total >> 20} MB | Used: {mem.used >> 20} MB | Free: {mem.free >> 20} MB | Avail: {mem.available >> 20} MB")

def restart_driver(service, options, label=""):
    print(f"🔄 Restarting driver{f' ({label})' if label else ''} ...")
    try:
        driver.quit()
    except Exception as e:
        print(f"⚠️ Failed to quit driver cleanly: {e}")
    kill_chromedriver()
    log_memory()
    os.system("sudo sh -c 'echo 3 >/proc/sys/vm/drop_caches'")
    driver = setup_driver(service, options)
    print("✅ Driver restarted.")
    log_memory()
    print("🌙 Sleeping for 15 seconds before resuming...")
    time.sleep(15)
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

def test_landing_page(driver, url, paths):
    output_path = paths["output"]
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "test_landing_page.html"

    print(f"Loading landing page: {url}")
    driver.get(url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "body")))
    time.sleep(5)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"✅ Rendered HTML saved to {output_file}")

def fetch_aacr_title_link_from_html(driver, url, session_name, dump_dir, retries=3):
    if DEBUG:
        print(f"[DEBUG] Trying to fetch url {url} for session {session_name}.")

    for attempt in range(1, retries + 1):
        try:
            success = safe_get(driver, url)
            if not success:
                raise Exception("Page load failed after retries")

            try:
                WebDriverWait(driver, 30).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "h1.name[data-id]")) >= 10
                )
                if DEBUG:
                    print(f"[DEBUG] WebDriverWait succeeded on attempt {attempt}")
            except TimeoutException:
                # once this starts happening there is no recovery
                print(f"WebDriverWait timed out - bailing.")
                break

            time.sleep(5)
            # JS fallback loop
            for i in range(10):
                count = driver.execute_script("return document.querySelectorAll('h1.name').length;")
                if count > 0:
                    if DEBUG:
                        print(f"[DEBUG] Found {count} links via JS after {i + 1} tries.")
                    break
                if DEBUG:
                    print(f"[DEBUG] Waiting for links... attempt {i + 1}")
                time.sleep(2)

            # Scrape data using JavaScript
            data = driver.execute_script("""
                return [...document.querySelectorAll('h1.name')].map(el => {
                    return {
                        id: el.getAttribute('data-id'),
                        title: (el.querySelector('span.bodyTitle') || {}).innerText || ""
                    };
                });
            """)

            df = pd.DataFrame([
                {
                    "link": f"https://www.abstractsonline.com/pp8/#!/20273/presentation/{item['id']}",
                    "title": item["title"].strip(),
                    "retrieved": False
                }
                for item in data if item["id"] and item["title"]
            ])

            return df

        except Exception as e:
            print(f"⚠️ Exception in fetch_aacr_title_link_from_html (attempt {attempt}): {e}")
            page_num = url.split("/")[-1]
            safe_session = re.sub(r"\W+", "_", session_name)
            dump_file = dump_dir / f"{safe_session}_PAGE{page_num}_attempt{attempt}.html"
            with open(dump_file, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            if DEBUG:
                print(f"[DEBUG] ❌ Saved failed HTML to {dump_file}")


    # Return empty DataFrame if all attempts fail
    return pd.DataFrame(columns=["link", "title", "retrieved"])



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


def estimate_all_sessions(session_urls, service, options, paths):
    paths["output"].mkdir(parents=True, exist_ok=True)
    estimates_file = paths["session_estimates"] 

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
        total_pages = get_total_pages(service, options, session_url, session_name, paths["html_dumps"])
        print(f"📄 Estimated pages: {total_pages}")
        session_data.append({"session": session_name, "pages": total_pages})
        retried_sessions.append(session_name)

    df = pd.DataFrame(session_data)
    if estimates_file.exists():
        estimates_file.rename(estimates_file.with_suffix(".bak"))
    df.to_csv(estimates_file, sep="\t", index=False)
    print(f"📊 Session estimates saved to {estimates_file}")

    if not retried_sessions:
        paths["session_estimates_ok"].touch()
        print(f"✅ All sessions had valid page estimates. Flag file created: {paths['session_estimates_ok']}")

def get_links(session_urls, service, options, paths, max_pages=100):
    processed_path = paths["processed_pages"]
    links_path = paths["aacr_links"]
    estimates_path = paths["session_estimates"]
    dump_dir = paths["html_dumps"]
    dump_dir.mkdir(parents=True, exist_ok=True)
    finished_path = paths["get_links_finished"]
    driver = setup_driver(service, options)
    # limit driver restarts
    restart_attempts = 0
    max_restart_attempts = 10

    # Load estimates if not already loaded
    if not estimates_path.exists():
        print("❌ session_estimates.tsv not found.")
        return
    estimates_df = pd.read_csv(estimates_path, sep="\t")

    # Load processed or create using estimates.  For persistent tracking of progress
    if processed_path.exists():
        processed_df = pd.read_csv(processed_path, sep="\t")
    else:
        processed_df = pd.DataFrame([
            {"session": row["session"], "page": page, "processed": False}
            for _, row in estimates_df.iterrows()
            for page in range(1, row["pages"] + 1)
        ])
        processed_df.to_csv(processed_path, sep="\t", index=False)

    # Load pre-exisiting progress or create new links file
    if links_path.exists():
        aacr_links = pd.read_csv(links_path, sep="\t")
    else:
        aacr_links = pd.DataFrame(columns=["session", "link", "title", "retrieved"])

    seen_links = set(aacr_links["link"])
    new_links = []
    pages_visited = 0

    # Iterate over processed file and get links for each page
    for idx, row in processed_df.iterrows():
        session_name, page_num, processed = row["session"], row["page"], row["processed"]
        if processed or pages_visited > max_pages:
            continue
        else:
            pages_visited += 1

        url_base = next((u for u in session_urls if extract_session_name(u) == session_name), None)
        if not url_base:
            print(f"⚠️ No URL found for session {session_name}")
            continue
        url = re.sub(r"/\d+$", f"/{page_num}", url_base)

        # Determine if this is the last page
        expected_pages_row = estimates_df[estimates_df["session"] == session_name]
        total_pages = expected_pages_row.iloc[0]["pages"] if not expected_pages_row.empty else None
        is_last_page = total_pages is not None and page_num == total_pages
        
        try:
            df = fetch_aacr_title_link_from_html(driver, url, session_name, dump_dir)
            # were all 10 expected links retrieved? mark the page as processed
            if len(df) == 10 or is_last_page:
                processed_df.loc[idx, "processed"] = True
            else:
                print(f"⚠️ Only retrieved {len(df)} links from page {page_num} of session '{session_name}' (expected 10).")
            # has the connection fallen over - try to recover
            if len(df) == 0:
                restart_attempts += 1
                if restart_attempts >= max_restart_attempts:
                    print(f"❌ Giving up on page {page_num} of session '{session_name}' after {max_restart_attempts} restart attempts.")
                    continue
                else:
                    driver = restart_driver(service, options, label=f"session={session_name}, page={page_num}")

            # prep df with just new links and add
            df["session"] = session_name    
            df = df[~df["link"].isin(seen_links)]
            new_links.append(df)
        except Exception as e:
            print(f"❌ Failed to fetch page {page_num} of {session_name}: {e}")

    if new_links:
        combined_df = pd.concat([aacr_links] + new_links, ignore_index=True)
        if links_path.exists():
            links_path.rename(links_path.with_suffix(".bak"))
        combined_df.to_csv(links_path, sep="\t", index=False)
        total_new = sum(len(x) for x in new_links)
        print(f"✅ Updated aacr_links.tsv with {total_new} new entries")

    if processed_path.exists():
        processed_path.rename(processed_path.with_suffix(".bak"))
    processed_df.to_csv(processed_path, sep="\t", index=False)
    print(f"📌 Checkpoint saved to {processed_path}")

    if processed_df["processed"].all():
        finished_path.touch()
        print(f"✅ All pages have been processed. Flag file created: {finished_path}")
    else:
        remaining = (~processed_df["processed"]).sum()
        print(f"ℹ️ {remaining} pages remaining unprocessed.")

    driver.quit()

def get_abstracts(service, options, paths, max_pages=100, save_html=False):

    links_path = paths["aacr_links"]
    abstracts_path = paths["aacr_abstracts"]
    finished_flag = paths["get_abstracts_finished"]

    if not links_path.exists():
        print(f"❌ {links_path} not found.")
        return

    links_df = pd.read_csv(links_path, sep="\t")
    pending = links_df[links_df["retrieved"] == False]
    print(f"🔎 {len(pending)} abstracts pending retrieval.")

    if pending.empty:
        finished_flag.touch()
        print(f"✅ All abstracts retrieved. Flag file created: {finished_flag}")
        return

    if abstracts_path.exists():
        abstracts_df = pd.read_csv(abstracts_path, sep="\t")
    else:
        abstracts_df = pd.DataFrame(columns=["link", "title", "session", "authors", "abstract", "status"])

    new_rows = []
    start_time = time.time()  # ⏱️ Start batch timer
    for idx, row in pending.head(max_pages).iterrows():
        link = row["link"]
        title = row["title"]
        session = row["session"]

        print(f"🧲 Fetching abstract {idx +1} for link: {link}")

        try:
            driver = setup_driver(service, options)
            success = safe_get(driver, link)
            if not success:
                raise Exception("Page load failed")

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.ID, "body"))
            )
            time.sleep(6)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            authors = "N/A"
            abstract = "N/A"
            dl_tag = soup.find("dl")
            if dl_tag:
                dt_tags = dl_tag.find_all("dt")
                dd_tags = dl_tag.find_all("dd")

                for dt, dd in zip(dt_tags, dd_tags):
                    label = dt.get_text(strip=True).lower()
                    if "presenter" in label or "author" in label:
                        authors = dd.get_text(separator=" ", strip=True)
                    elif "abstract" in label:
                        abstract = dd.get_text(separator=" ", strip=True)

            new_rows.append({
                "link": link,
                "title": title,
                "session": session,
                "authors": authors,
                "abstract": abstract,
                "status": "complete"
            })
            links_df.loc[links_df["link"] == link, "retrieved"] = True

            if save_html:
                fallback_file = paths["output"] / f"abstract_fallback_{idx + 1}.html"
                with open(fallback_file, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                if DEBUG:
                    print(f"[DEBUG] Saved HTML for abstract page to {fallback_file}")

        except Exception as e:
            print(f"❌ Failed to fetch abstract for {title}: {e}")
            new_rows.append({
                "link": link,
                "title": title,
                "session": session,
                "authors": "",
                "abstract": "",
                "status": "retry"
            })

        finally:
            driver.quit()
            time.sleep(random.uniform(2, 4))

    elapsed_time = time.time() - start_time  # ⏱️ End batch timer
    if new_rows:
        avg_time = elapsed_time / len(new_rows)
        remaining = links_df["retrieved"].value_counts().get(False, 0)
        est_total = int(avg_time * remaining)
        est_min, est_sec = divmod(est_total, 60)
        print(f"⏳ Avg time/abstract: {avg_time:.1f} sec — Estimated time remaining: {est_min} min {est_sec} sec")

    if new_rows:
        updated_df = pd.DataFrame(new_rows)
        if abstracts_path.exists():
            abstracts_path.rename(abstracts_path.with_suffix(".bak"))
            abstracts_df = pd.concat([abstracts_df, updated_df], ignore_index=True)
            abstracts_df.drop_duplicates(subset=["link"], inplace=True)
        else:
            abstracts_df = updated_df

        abstracts_df.to_csv(abstracts_path, sep="\t", index=False)
        print(f"📄 Abstracts updated and saved to {abstracts_path}")

    print(f"✅ {len(new_rows)} abstracts processed.")    

    links_path.rename(links_path.with_suffix(".bak"))
    links_df.to_csv(links_path, sep="\t", index=False)
    print(f"📌 Updated aacr_links.tsv with retrieval status.")

    if links_df["retrieved"].all():
        finished_flag.touch()
        print(f"✅ All abstracts have been retrieved. Flag file created: {finished_flag}")

def reset_processed_sessions(paths, session_list):
    processed_path = paths["processed_pages"]
    links_finished_flag = paths["get_links_finished"]
    abstracts_finished_flag = paths["get_abstracts_finished"]
    
    if not processed_path.exists():
        print(f"⚠️ {processed_path} does not exist. Nothing to reset.")
        return
    
    df = pd.read_csv(processed_path, sep="\t")
    original_processed = df["processed"].sum()

    if session_list.strip().lower() == "all":
        df["processed"] = False
        print("🔄 Reset 'processed' flag for all sessions.")
    else:
        target_sessions = [s.strip() for s in session_list.split(",")]
        matched_sessions = df["session"].isin(target_sessions)
        if not matched_sessions.any():
            print(f"⚠️ No matching sessions found for: {target_sessions}")
            return
        df.loc[matched_sessions, "processed"] = False
        print(f"🔄 Reset 'processed' flag for sessions: {', '.join(target_sessions)}")

    # Backup and save updated file
    processed_path.rename(processed_path.with_suffix(".bak"))
    df.to_csv(processed_path, sep="\t", index=False)
    print(f"📁 Changes saved to {processed_path}")

    # Remove GET_LINKS_FINISHED and GET_ABSTRACTS_FINISHED flag if we reset any rows
    if df["processed"].sum() < original_processed:
        if links_finished_flag.exists():
            links_finished_flag.unlink()
            print(f"❌ Removed {links_finished_flag} because some sessions were reset.")
        if abstracts_finished_flag.exists():
            abstracts_finished_flag.unlink()
            print(f"❌ Removed {abstracts_finished_flag} because some sessions were reset.")




def main():
    parser = argparse.ArgumentParser(description="AACR Abstract Scraper")
    parser.add_argument("--test-landing-page", action="store_true", help="Load and save the first landing page's DOM")
    parser.add_argument("--test-get-links", action="store_true", help="Run get_links with max_pages=1")
    parser.add_argument("--test-get-abstracts", action="store_true", help="Test get_abstracts with 1 page and save HTML")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--output", type=str, default="output/aacr", help="Path to save outputs")
    parser.add_argument("--estimate", action="store_true", help="Estimate pages for each session type")
    parser.add_argument("--build-all", action="store_true", help="Estimate and scrape all AACR sessions")
    parser.add_argument("--max-calls-per-scraper-session", type=int, default=500, help="Max get_abstracts attempts to process all session pages")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to get in each call to get_links or get_abstracts.")
    parser.add_argument("--wait", type=int, default=12, help="Wait time between get_abstracts attempts.")
    parser.add_argument("--reset-processed-sessions", type=str, help="Comma-separated list of session names to reset in processed_session_pages.tsv or 'all'")

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
    output_path.mkdir(parents=True, exist_ok=True)
    global paths
    paths = set_output_paths(output_path)

    sys.stdout = TeeLogger(paths["log"])
    service = Service(ChromeDriverManager().install())
    options = get_chrome_options()

    start_time = datetime.datetime.now()
    print(f"🚀 Started AACR scraper at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    if args.test_landing_page:
        driver = setup_driver(service, options)
        test_landing_page(driver, session_urls[0], paths)
        driver.quit()
        return
    
    if args.estimate:
        estimate_all_sessions(session_urls, service, options, paths)
        return
       
    if args.test_get_links:
        get_links(session_urls, service, options, paths, max_pages=10)

    if args.test_get_abstracts:
        get_abstracts(service, options, paths, max_pages=1, save_html=True)
        return

    if args.reset_processed_sessions:
        reset_processed_sessions(paths, args.reset_processed_sessions)

    if args.build_all:

        max_calls = args.max_calls_per_scraper_session
        max_pages = args.max_pages
        wait = args.wait

        # estimate_all_sessions
        attempts = 0
        while not paths["session_estimates_ok"].exists() and attempts < 3:
            print(f"🚧 Running estimate_all_sessions (attempt {attempts + 1})...")
            estimate_all_sessions(session_urls, service, options, paths)
            attempts += 1
        if not paths["session_estimates_ok"].exists():
            print("❌ Failed to estimate all sessions after 3 attempts.")
            return
        else:
            print("✅ Session estimates OK — ready to get links.")
        
        # get_links
        calls = 0
        while not paths["get_links_finished"].exists() and calls < max_calls:
            print(f"🚧 Running get_links (attempt {calls + 1})...")
            service = Service(ChromeDriverManager().install())
            options = get_chrome_options()
            get_links(session_urls, service, options, paths, max_pages=max_pages)
            calls += 1
            print(f"Sleeping for {wait} seconds")
            time.sleep(wait)

        if not paths["get_links_finished"].exists():
            print("❌ get_links did not complete after maximum allowed attempts.")
        else:
            print("✅ Links have been retrieved from all session pages. Ready to retrieve abstracts.")
        
        # get abstracts
        while not paths["get_abstracts_finished"].exists() and calls < max_calls:
            print(f"🚧 Running get_abstracts (attempt {calls + 1})...")
            get_abstracts(service, options, paths, max_pages=max_pages)
            calls += 1
            print(f"Sleeping for {wait} seconds")
            time.sleep(wait)

        if not paths["get_abstracts_finished"].exists():
            print("❌ get_abstracts did not complete after maximum allowed attempts.")
        else:
            print("✅ All abstracts have been retrieved for all sessions. Ready to retrieve embargoed abstracts.")
    

    # cleanup
    end_time = datetime.datetime.now()
    elapsed = end_time - start_time
    print(f"✅ Finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')} (Elapsed time: {elapsed})")

    # Close the logger before renaming the file
    if isinstance(sys.stdout, TeeLogger):
        sys.stdout.log.close()
        sys.stdout = sys.stdout.terminal

    # Rename log.txt to include a timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_backup_path = paths["log"].with_name(f"log_{timestamp}.txt")
    paths["log"].rename(log_backup_path)



if __name__ == "__main__":
    main()

import argparse
from pathlib import Path
import pandas as pd

# ← Import everything from your existing script
# Assume the following are defined in the same file or imported:
# - fetch_sitc_title_auths_link
# - fetch_sitc_abstracts
# - get_chrome_options
# - setup_driver
# - safe_get
# - Service, ChromeDriverManager
import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium_stealth import stealth
import random
from selenium.common.exceptions import TimeoutException, WebDriverException
from pathlib import Path


# Setup Selenium WebDriver Options once
def get_chrome_options_x():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Ensure it's running in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-features=NetworkService")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return options

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


# Dynamically manage ChromeDriver
service = Service(ChromeDriverManager().install())
options = get_chrome_options()

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

# Function to fetch and parse SITC abstracts using Selenium
def fetch_sitc_title_auths_link(service, options, links_path: str):
    import os

    url = "https://www.sitcancer.org/2024/abstracts/titles-and-publications"
    driver = setup_driver(service, options)
    driver.get(url)
    time.sleep(5)  # Allow JS to load
    page_source = driver.page_source
    driver.quit()

    sections = page_source.split("Abstract Number")
    titles, authors_list, doi_links = [], [], []

    for section in sections[1:]:
        try:
            title_match = re.search(r'<p style="font-size: 1.5em; font-weight: 700;"><a href=.*?>(.*?)</a></p>', section, re.DOTALL)
            title = title_match.group(1).strip() if title_match else "Unknown Title"
            title = re.sub(r'<.*?>', '', title)
        except:
            title = "Unknown Title"

        try:
            authors_match = re.search(r'Authors</span>.*?<span class="ais-Highlight"><span class="ais-Highlight-nonHighlighted">(.*?)</span></span>', section, re.DOTALL)
            authors = authors_match.group(1).strip() if authors_match else "Unknown Authors"
        except:
            authors = "Unknown Authors"

        try:
            doi_match = re.search(r'(https?://dx\.doi\.org/10\.1136/jitc-2024-SITC2024\.\d+)', section)
            doi_link = doi_match.group(1) if doi_match else "No DOI Found"
        except:
            doi_link = "No DOI Found"

        titles.append(title)
        authors_list.append(authors)
        doi_links.append(doi_link)

    new_df = pd.DataFrame({
        "Title": titles,
        "Authors": authors_list,
        "DOI Link": doi_links,
        "retrieved": False
    })

    path = Path(links_path)

    if path.exists():
        existing_df = pd.read_csv(path, sep="\t")
        merged_df = pd.concat([existing_df, new_df], ignore_index=True)
        merged_df.drop_duplicates(subset=["DOI Link"], inplace=True)
        path.rename(path.with_suffix(".bak"))  # Backup
    else:
        merged_df = new_df

    merged_df.to_csv(path, sep="\t", index=False)
    print(f"🔗 Links written to {links_path} ({len(merged_df)} total entries)")

    return merged_df


def safe_get(driver, url, retries=3, wait=10):
    """Try to get a URL with retries and backoff"""
    for attempt in range(retries):
        try:
            driver.set_page_load_timeout(60)
            driver.get(url)
            return True
        except TimeoutException:
            print(f"⏱️ Timeout on attempt {attempt + 1} for {url}")
            time.sleep(wait)
    return False


def fetch_sitc_abstracts(links_path: str, abstracts_path: str, service, options, limit=None):
    links_df = pd.read_csv(links_path, sep="\t")

    pending_df = links_df[links_df["retrieved"] == False]
    if limit:
        pending_df = pending_df.head(limit)

    if pending_df.empty:
        print("✅ No abstracts to fetch — all entries marked as retrieved.")
        return pd.DataFrame()

    abstract_sections = []
    updated_links = links_df.copy()

    for index, row in pending_df.iterrows():
        doi_link = row["DOI Link"]
        print(f"\n[{index+1}/{len(links_df)}] Trying DOI: {doi_link}")

        try:
            driver = setup_driver(service, options)

            success = safe_get(driver, doi_link)
            if not success:
                print(f"⚠️ Timeout: {doi_link}")
                driver.quit()
                continue

            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            abstract_div = soup.find("div", class_="section abstract")

            if abstract_div:
                subsections = abstract_div.find_all("div", class_="subsection")
                if subsections:
                    for subsection in subsections:
                        heading = subsection.find("strong")
                        section_name = heading.get_text(strip=True) if heading else "Unknown Section"
                        text = subsection.get_text(strip=True).replace(section_name, "", 1).strip()
                        abstract_sections.append({
                            "DOI Link": doi_link,
                            "Section": section_name,
                            "Text": text
                        })
                else:
                    text = abstract_div.get_text(strip=True)
                    abstract_sections.append({
                        "DOI Link": doi_link,
                        "Section": "Abstract",
                        "Text": text
                    })

                # Mark as retrieved in original DataFrame
                updated_links.loc[updated_links["DOI Link"] == doi_link, "retrieved"] = True

            else:
                print(f"⚠️ No abstract found at {doi_link}")

        except Exception as e:
            print(f"❌ Error processing {doi_link}: {e}")

        finally:
            driver.quit()
            time.sleep(random.uniform(8, 12))

    # Write updated links with backup
    link_path = Path(links_path)
    link_path.rename(link_path.with_suffix(".bak"))
    updated_links.to_csv(links_path, sep="\t", index=False)
    print(f"✅ Updated links saved to {links_path}")

    # Save abstract content
    abstract_df = pd.DataFrame(abstract_sections)

    if Path(abstracts_path).exists():
        existing = pd.read_csv(abstracts_path, sep="\t")
        combined = pd.concat([existing, abstract_df], ignore_index=True)
        combined.drop_duplicates(subset=["DOI Link", "Section"], inplace=True)
        Path(abstracts_path).rename(Path(abstracts_path).with_suffix(".bak"))
    else:
        combined = abstract_df

    combined.to_csv(abstracts_path, sep="\t", index=False)
    print(f"📄 Abstracts saved to {abstracts_path} ({len(combined)} total entries)")

    return combined


################################



def main():
    parser = argparse.ArgumentParser(description="SITC Abstract Scraper")
    parser.add_argument("--refresh", action="store_true", help="Update links_path with new abstracts from SITC site")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of abstracts to retrieve")
    parser.add_argument("--links-path", type=str, default="sitc_links.tsv", help="Path to links data file")
    parser.add_argument("--abstracts-path", type=str, default="sitc_abstracts.tsv", help="Path to abstracts output file")
    args = parser.parse_args()

    service = Service(ChromeDriverManager().install())
    options = get_chrome_options()

    if args.refresh:
        print("🔄 Refreshing links from SITC site...")
        links_df = fetch_sitc_title_auths_link(service, options, args.links_path)
    else:
        path = Path(args.links_path)
        if not path.exists():
            print(f"❌ File {args.links_path} does not exist. Run with --refresh to create it.")
            return
        links_df = pd.read_csv(path, sep="\t")

    print("📥 Fetching abstracts not yet retrieved...")
    df_abstracts = fetch_sitc_abstracts(
        links_path=args.links_path,
        abstracts_path=args.abstracts_path,
        service=service,
        options=options,
        limit=args.limit,
    )

    print("✅ Done.")

if __name__ == "__main__":
    main()

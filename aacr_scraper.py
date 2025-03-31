import argparse
import time
import random
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup
import sys

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
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

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

def test_landing_page(driver, url, output_file="aacr_test_landing_page.html"):
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

def main():
    parser = argparse.ArgumentParser(description="AACR Abstract Scraper")
    parser.add_argument("--test-landing-page", action="store_true", help="Load and save the first landing page's DOM")
    parser.add_argument("--output", type=str, default="aacr_test_landing_page.html", help="Path to save rendered HTML for test")
    parser.add_argument("--parse-html", action="store_true", help="Extract links and titles from saved HTML file")
    parser.add_argument("--html-path", type=str, default="aacr_test_landing_page.html", help="Path to saved HTML file to parse")
    args = parser.parse_args()

    session_urls = [
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Clinical%20Trials%20Minisymposium/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Clinical%20Trials%20Plenary%20Session/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@AACRPrimaryCategoryAll=ClinicalPosters/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Late-Breaking%20Minisymposium/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Late-Breaking%20Poster%20Session/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Minisymposium/1",
        "https://www.abstractsonline.com/pp8/#!/20273/presentations/@sessiontype=Poster%20Session/1",
    ]

    service = Service(ChromeDriverManager().install())
    options = get_chrome_options()
    driver = setup_driver(service, options)

    if args.test_landing_page:
        test_landing_page(driver, session_urls[0], args.output)
        driver.quit()
        return

    if args.parse_html:
        df = fetch_aacr_title_link_from_html(args.html_path)
        df.to_csv("aacr_links.tsv", sep="\t", index=False)
        print("✅ Extracted links and titles saved to aacr_links.tsv")
        return

    print("🚧 More functionality coming soon!")
    driver.quit()

if __name__ == "__main__":
    main()

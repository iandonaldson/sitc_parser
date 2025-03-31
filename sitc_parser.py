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
def fetch_sitc_title_auths_link(service, options):
    url = "https://www.sitcancer.org/2024/abstracts/titles-and-publications"
    driver = setup_driver(service, options)
    driver.get(url)
    time.sleep(5)  # Wait for JavaScript to load content
    
    # Extract all page content
    page_source = driver.page_source
    driver.quit()  # Close browser early

    # Split into sections using "Abstract Number"
    sections = page_source.split("Abstract Number")
    
    titles, authors_list, doi_links = [], [], []
    
    for section in sections[1:16]:  # Skip first empty split and limit to 15 abstracts
        
        # Extract abstract number
        abstract_number = section.split('</span></span>')[0].strip()
        
        # Extract title and remove HTML tags
        try:
            title_match = re.search(r'<p style="font-size: 1.5em; font-weight: 700;"><a href=.*?>(.*?)</a></p>', section, re.DOTALL)
            title = title_match.group(1).strip() if title_match else "Unknown Title"
            title = re.sub(r'<.*?>', '', title)  # Remove all remaining HTML tags explicitly
        except:
            title = "Unknown Title"
        
        # Extract authors
        try:
            authors_match = re.search(r'Authors</span>.*?<span class="ais-Highlight"><span class="ais-Highlight-nonHighlighted">(.*?)</span></span>', section, re.DOTALL)
            authors = authors_match.group(1).strip() if authors_match else "Unknown Authors"
        except:
            authors = "Unknown Authors"
        
        # Extract DOI link
        try:
            doi_match = re.search(r'(https://dx\.doi\.org/10\.1136/jitc-2024-SITC2024\.\d+)', section)
            doi_link = doi_match.group(1) if doi_match else "No DOI Found"
        except:
            doi_link = "No DOI Found"
        
        print(f"Extracted DOI: {doi_link}")  # Debugging output
        
        # Append extracted data
        titles.append(title)
        authors_list.append(authors)
        doi_links.append(doi_link)
    
    # Store in DataFrame
    df = pd.DataFrame({"Abstract Number": list(range(1, len(titles) + 1)), "Title": titles, "Authors": authors_list, "DOI Link": doi_links})
    
    return df


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


def fetch_sitc_abstracts(df, service, options):
    abstract_sections = []

    for index, row in df.iterrows():
        doi_link = row["DOI Link"]
        print(f"\n[{index+1}/{len(df)}] Trying DOI: {doi_link}")

        if doi_link == "No DOI Found":
            abstract_sections.append({
                "DOI Link": doi_link,
                "Section": "None",
                "Text": "No Abstract Found"
            })
            continue

        # Create a fresh driver every time
        try:
            driver = setup_driver(service, options)

            success = safe_get(driver, doi_link)
            if not success:
                abstract_sections.append({
                    "DOI Link": doi_link,
                    "Section": "Timeout",
                    "Text": "Page load timed out after retries"
                })
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
            else:
                abstract_sections.append({
                    "DOI Link": doi_link,
                    "Section": "None",
                    "Text": "No Abstract Found"
                })

        except Exception as e:
            print(f"❌ Error processing {doi_link}: {e}")
            abstract_sections.append({
                "DOI Link": doi_link,
                "Section": "Error",
                "Text": f"Failed due to exception: {e}"
            })

        finally:
            driver.quit()

        # Throttle between requests
        sleep_time = random.uniform(8, 12)
        print(f"⏳ Sleeping for {sleep_time:.1f} seconds...")
        time.sleep(sleep_time)

    df_abstracts = pd.DataFrame(abstract_sections)
    return df_abstracts

# Example usage
df = fetch_sitc_title_auths_link(service, options)
df.to_csv("sitc_title_auth_link.tsv", index=False, sep="\t")
print("Data saved to sitc_title_auth_link.tsv")

df_abstracts = fetch_sitc_abstracts(df, service, options)
df_abstracts.to_csv("sitc_link_abstract.tsv", index=False, sep="\t")
print("Data saved to sitc_link_abstract.tsv")

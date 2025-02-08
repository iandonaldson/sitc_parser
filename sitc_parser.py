import time
import re
import tempfile
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Function to fetch and parse SITC abstracts using Selenium
def fetch_sitc_title_auths_link():
    url = "https://www.sitcancer.org/2024/abstracts/titles-and-publications"
    
    # Create a unique temporary directory for user data
    temp_user_data_dir = tempfile.mkdtemp()
    
    # Setup Selenium WebDriver with isolated profile
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={temp_user_data_dir}")  # Prevent session conflict
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  # Improve stability
    options.add_argument("--start-maximized")  # Ensure full content visibility
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(5)  # Wait for JavaScript to load content
    
    # Extract all page content
    page_source = driver.page_source
    
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
    
    # Close browser
    driver.quit()
    
    # Store in DataFrame
    df = pd.DataFrame({"Abstract Number": list(range(1, len(titles) + 1)), "Title": titles, "Authors": authors_list, "DOI Link": doi_links})
    
    return df

# Function to fetch abstracts from DOI links
def fetch_sitc_abstracts(df):
    abstracts = []
    
    # Create a unique temporary directory for user data
    temp_user_data_dir = tempfile.mkdtemp()
    
    # Setup Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={temp_user_data_dir}")  # Prevent session conflict
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  
    options.add_argument("--start-maximized")  
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    for index, row in df.iterrows():
        doi_link = row["DOI Link"]
        if doi_link == "No DOI Found":
            abstracts.append("No Abstract Found")
            continue
        
        driver.get(doi_link)
        time.sleep(5)  # Increased wait time to allow JavaScript to load content
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Save HTML for debugging
        with open(f"debug_doi_page_{index}.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        print(f"Saved HTML snapshot for {doi_link}")
        
        # Extract abstract content
        abstract_sections = soup.find_all("div", class_="abstract-section")
        if abstract_sections:
            abstract_text = " ".join([section.get_text(strip=True) for section in abstract_sections])
        else:
            abstract_text = "No Abstract Found"
        
        abstracts.append(abstract_text)
    
    driver.quit()
    
    # Store in DataFrame
    df_abstracts = pd.DataFrame({"DOI Link": df["DOI Link"], "Abstract": abstracts})
    
    return df_abstracts

# Example usage
df = fetch_sitc_title_auths_link()
df.to_csv("sitc_title_auth_link.tsv", index=False, sep="\t")
print("Data saved to sitc_title_auth_link.tsv")

df_abstracts = fetch_sitc_abstracts(df)
df_abstracts.to_csv("link_abstract.tsv", index=False, sep="\t")
print("Data saved to link_abstract.tsv")

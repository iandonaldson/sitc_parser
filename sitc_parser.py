import requests
from bs4 import BeautifulSoup
import pandas as pd

# Function to fetch and parse SITC abstracts from the live webpage
def fetch_sitc_abstracts():
    url = "https://www.sitcancer.org/2024/abstracts/titles-and-publications"
    headers = {'User-Agent': 'Mozilla/5.0'}  # Mimic a real browser
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve webpage, status code: {response.status_code}")
        return None
    
    # Parse HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Identify structure - find all abstract sections
    abstracts = soup.find_all('div', class_='abstract-entry')  # Adjust class based on actual structure
    
    titles, authors_list, doi_links = [], [], []
    
    for abstract in abstracts[:15]:  # Limit to first 15 entries
        
        # Extract title
        title_tag = abstract.find('h3')  # Adjust tag based on structure
        title = title_tag.text.strip() if title_tag else "Unknown Title"
        
        # Extract authors
        authors_tag = abstract.find('p', class_='authors')  # Adjust class based on structure
        authors = authors_tag.text.strip() if authors_tag else "Unknown Authors"
        
        # Extract DOI link
        doi_tag = abstract.find('a', href=True)
        doi_link = doi_tag['href'] if doi_tag and "doi.org" in doi_tag['href'] else "No DOI Found"
        
        # Append extracted data
        titles.append(title)
        authors_list.append(authors)
        doi_links.append(doi_link)
    
    # Store in DataFrame
    df = pd.DataFrame({"Title": titles, "Authors": authors_list, "DOI Link": doi_links})
    return df

# Example usage
df = fetch_sitc_abstracts()
if df is not None:
    print(df)

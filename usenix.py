import requests
from bs4 import BeautifulSoup
import csv
import logging
import time

# Setup & Config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "https://www.usenix.org"
PAPERS_URL = "https://www.usenix.org/publications/proceedings/usenix%2520security"

TEST_MODE = True
TEST_ROWS = 3     # Number of rows to scrape in test mode

MAX_PAGES = 1 if TEST_MODE else 59 # one of these doesn't do anything

### Scraping
# Extract abstract
def extract_abstract(paper_url, title):
    logging.info(f"Retrieving abstract from: {paper_url}")
    response = requests.get(paper_url)
    
    if response.status_code != 200:
        logging.error(f"Failed to retrieve page at {paper_url} (status code: {response.status_code})")
        return "No Abstract Found"
    
    paper_soup = BeautifulSoup(response.content, 'html.parser')

    # Get abstract from <div class="field-item odd">
    abstract_container = paper_soup.find('div', class_='field-name-field-paper-description')
    if abstract_container:
        abstract_element = abstract_container.find('div', class_='field-item odd')
        abstract = abstract_element.get_text(strip=True) if abstract_element else "No Abstract Found"
    else:
        abstract = "No Abstract Found"

    if abstract == "No Abstract Found":
        logging.warning(f"Abstract not found for paper: {title} at {paper_url}")
    
    return abstract

# Extract paper details
def scrape_paper_details(page_url, search_id):
    logging.info(f"Scraping papers from page: {page_url}")
    response = requests.get(page_url)
    
    if response.status_code != 200:
        logging.error(f"Failed to retrieve page at {page_url} (status code: {response.status_code})")
        return []

    page_soup = BeautifulSoup(response.content, 'html.parser')

    # Get proceedings table
    table = page_soup.find('table', class_='proceedings')
    if not table:
        logging.warning(f"No table found on page: {page_url}")
        return []
    
    rows = table.find_all('tr')[1:]
    if TEST_MODE:
        rows = rows[:TEST_ROWS]  # Limit to x first rows if in test mode

    papers_data = []
    paper_id = 1

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 2:
            logging.warning(f"Skipping malformed row on page: {page_url}")
            continue
        
        # Extract the conference name from the first <td>
        conference_element = cols[0].find_all('a')
        if conference_element:
            conference_name = conference_element[0].get_text(strip=True)
        else:
            conference_name = "Unknown Conference"

        # Extract paper title, URL, and authors
        title_element = cols[1].find('a')
        paper_title = title_element.get_text(strip=True) if title_element else "No Title Found"
        
        if title_element and 'href' in title_element.attrs:
            paper_url = f"{BASE_URL}{title_element['href']}"
        else:
            logging.warning(f"No valid paper URL found in row, skipping.")
            continue

        authors = cols[2].get_text(strip=True) if len(cols) > 2 else "No Authors Listed"

        # Extract the abstract
        abstract = extract_abstract(paper_url, paper_title)
        if abstract == "No Abstract Found":
            logging.warning(f"Skipping paper '{paper_title}' due to missing abstract.")
            continue

        logging.info(f"Retrieved paper: {paper_title} from {conference_name}")

        papers_data.append({
            'search_id': f"search_{search_id:03d}",
            'paper_id': f"paper_{paper_id:05d}",
            'conference': conference_name,
            'paper_url': paper_url,
            'title': paper_title,
            'authors': authors,
            'abstract': abstract
        })
        
        paper_id += 1

    logging.info(f"Completed scraping page: {page_url} with {len(papers_data)} papers found.")
    return papers_data


# Main scraping
def scrape_all_pages():
    all_results = []
    search_id = 1
    
    for page_num in range(MAX_PAGES):
        page_url = f"{PAPERS_URL}?page={page_num}"
        page_results = scrape_paper_details(page_url, search_id)
        
        if page_num == 0 and not page_results:
            logging.warning(f"No papers found on the first page {page_url}. Exiting.")
            break
        
        all_results.extend(page_results)
        search_id += 1
    
    return all_results

### Saving to CSV
def save_to_csv(data, filename):
    logging.info(f"Saving data to CSV file: {filename}")
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['search_id', 'paper_id', 'conference', 'paper_url', 'title', 'authors', 'abstract'], delimiter='|')
        writer.writeheader()
        for row in data:
            # Replace newline characters in the abstract with a space
            row['abstract'] = row['abstract'].replace('\n', ' ').replace('\r', ' ')
            writer.writerow(row)
    logging.info(f"Data successfully saved to {filename}")


# Execute
if __name__ == "__main__":
    all_results = scrape_all_pages()

    if all_results:
        save_to_csv(all_results, "usenix_security_papers_test.csv")
        logging.info("Scraping complete! Data saved.")
    else:
        logging.warning("No papers found to save.")

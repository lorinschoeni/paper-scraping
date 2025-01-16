import re
import requests
from bs4 import BeautifulSoup
import csv
import logging

# Setup & Config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "https://petsymposium.org/popets/"
OUTPUT_CSV = "popets_papers.csv"

TEST_MODE = False 

# Scrape paper info (now regex)
def scrape_paper_details(paper_url):
    logging.info(f"Scraping paper details from: {paper_url}")
    response = requests.get(paper_url)
    if response.status_code != 200:
        logging.error(f"Failed to retrieve paper page: {paper_url} (status code: {response.status_code})")
        return None

    paper_soup = BeautifulSoup(response.content, 'html.parser')
    content_div = paper_soup.find('div', class_='content')
    if not content_div:
        logging.warning(f"No content found on paper page: {paper_url}")
        return None

    # store entire element
    content_text = content_div.get_text(separator="\n", strip=True)

    # Just use regex lol
    title = re.search(r"^(.*?)\n", content_text)
    title = title.group(1) if title else "No Title Found"

    authors = re.search(r"Authors?:\s*(.*?)(?:\n|<br>)", content_text)
    authors = authors.group(1) if authors else "No Authors Found"

    volume = re.search(r"Volume:\s*(\d+)", content_text)
    volume = volume.group(1) if volume else "No Volume Found"

    issue = re.search(r"Issue:\s*(\d+)", content_text)
    issue = issue.group(1) if issue else "No Issue Found"

    doi = re.search(r"DOI:\s*https://doi.org/(\S+)", content_text)
    doi = f"https://doi.org/{doi.group(1)}" if doi else ""

    abstract = re.search(r"Abstract:\s*(.*?)(?:\n|<br>|<p>)", content_text, re.DOTALL)
    abstract = abstract.group(1).strip() if abstract else "No Abstract Found"

    paper_id = doi.split("-")[-1] if doi else ""

    return {
        "volume": volume,
        "issue": issue,
        "paper_id": paper_id,
        "doi": doi,
        "title": title,
        "authors": authors,
        "abstract": abstract
    }

# Scrape volume info to get paper info
def scrape_volume(volume_url, volume_name):
    logging.info(f"Scraping volume: {volume_name} ({volume_url})")
    response = requests.get(volume_url)
    if response.status_code != 200:
        logging.error(f"Failed to retrieve volume page: {volume_url} (status code: {response.status_code})")
        return []

    volume_soup = BeautifulSoup(response.content, 'html.parser')
    accepted_list_div = volume_soup.find('div', class_='content accepted-list')
    if not accepted_list_div:
        logging.warning(f"No accepted papers list found on volume page: {volume_url}")
        return []

    papers = []
    for li in accepted_list_div.find_all('li'):
        title_element = li.find('a', href=True)
        title_text = title_element.get_text(strip=True) if title_element else ""

        # Skipping introductions - MIGHT NOT WORK IF NAMED DIFFERENTLY. MIGHT OMIT CERTAIN TITLES // to be improved
        if "Editor" in title_text:
            continue

        paper_page = title_element['href'] if title_element else None
        if not paper_page or not paper_page.endswith('.php'):
            continue

        paper_url = requests.compat.urljoin(volume_url, paper_page)
        paper_details = scrape_paper_details(paper_url)
        if paper_details:
            paper_details["volume"] = volume_name
            papers.append(paper_details)

    return papers

# Scrape main page to get volume info
def scrape_all_volumes():
    logging.info(f"Starting to scrape POPETS volumes from {BASE_URL}")
    response = requests.get(BASE_URL)
    if response.status_code != 200:
        logging.error(f"Failed to retrieve main page: {BASE_URL} (status code: {response.status_code})")
        return []

    main_soup = BeautifulSoup(response.content, 'html.parser')
    volumes = main_soup.find_all('a', href=True, string=lambda x: x and "Volume" in x)

    all_papers = []
    for volume in volumes:
        volume_name = volume.get_text(strip=True)
        volume_url = requests.compat.urljoin(BASE_URL, volume['href'])
        volume_papers = scrape_volume(volume_url, volume_name)
        all_papers.extend(volume_papers)

        # If running in TEST_MODE, stop after scraping the first volume
        if TEST_MODE:
            logging.info("Test mode enabled, stopping after the first volume.")
            break

    return all_papers

# Save papers to CSV
def save_to_csv(papers, filename):
    logging.info(f"Saving data to CSV file: {filename}")
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[
            "volume", "issue", "paper_id", "doi", "title", "authors", "abstract"
            ], 
            delimiter='|')
        writer.writeheader()
        for paper in papers:
            writer.writerow(paper)
    logging.info(f"Data successfully saved to {filename}")

# Execute
if __name__ == "__main__":
    papers = scrape_all_volumes()

    if papers:
        save_to_csv(papers, OUTPUT_CSV)
        logging.info("Scraping complete! Data saved.")
    else:
        logging.warning("No papers found to save.")
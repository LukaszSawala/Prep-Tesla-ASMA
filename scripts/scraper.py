from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from chromedriver_py import binary_path  # This is the key import
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
from tqdm import tqdm
from crawler import crawl_body_panels_section



def scrape_procedure(url, driver, title):
    driver.get(url)
    # Wait for main content to load (e.g., h1 or a key section)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
    except:
        print(f"Timeout loading {url}")

    # Get fully rendered HTML
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")
    
    # ID from URL
    proc_id = url.split('/')[-1].replace('.html', '')
    
    # Correction code & FRT - search text pattern (robust)
    full_text = soup.get_text()
    import re
    correction_match = re.search(r"Correction code\s+(\d+)", full_text)
    frt_match = re.search(r"FRT\s+([\d.]+)", full_text)
    correction_code = correction_match.group(1) if correction_match else None
    frt = frt_match.group(1) if frt_match else None
    
    # Full text for LLM - now varied and complete
    main_content = soup.find('main') or soup.find('article') or soup.body
    if main_content:
        full_text = " ".join(main_content.stripped_strings)
    else:
        full_text = " ".join(soup.stripped_strings)
    
    return {
        "id": proc_id,
        "title": title, # use passed title
        "section": "10 - Body Panels > 1010 - Body Panels", # figure out how to get this dynamically later
        "correction_code": correction_code,
        "frt": frt,
        "full_url": url,
        "full_text": full_text
    }

if __name__ == "__main__":

    # Setup headless Chrome once (reuse driver if scraping many)
    print("Setting up headless Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Updated headless flag for recent Chrome
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    print("Headless Chrome setup complete.")
    service = Service(executable_path=binary_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    body_1010_url = "https://service.tesla.com/docs/ModelY/ServiceManual/2025/en-us/GUID-24F633E2-C64D-4ECB-A6E2-669CF5012901.html"
    procedure_links = crawl_body_panels_section(body_1010_url)

    print(f"Found {len(procedure_links)} procedures to scrape.")

    procedures = []
    for link in tqdm(procedure_links, desc="Scraping procedures"):
        procedure = scrape_procedure(link["url"], driver, title=link["title"])
        procedures.append(procedure)

    driver.quit()
    # save those to a folder higher up
    with open("../data/body_panels_procedures.json", "w") as f:
        json.dump(procedures, f, indent=2, ensure_ascii=False) # save as utf-8
import re
import json
from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from chromedriver_py import binary_path 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def clean_text(text):
    """Cleans up UI boilerplate, icons, and extra whitespace."""
    if not text: return ""
    # Remove UI artifacts and Informational boilerplate text
    text = re.sub(r'(Expand All\|Collapse All|Informational Purposes|An informational icon|calling your attention|Warning Icon|A warning icon|possibly risky situation)', '', text, flags=re.I)
    # Remove the specific text 'TIp' or 'Note' if it's left as a prefix
    text = re.sub(r'^(Tip|Note|Caution|Warning|TIp)\s*', '', text, flags=re.I)
    return " ".join(text.split()).strip().strip(',')

def scrape_procedure(url, driver, title):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    except Exception as e:
        print(f"Error loading {url}: {e}")
        return None

    soup = BeautifulSoup(driver.page_source, "html.parser")
    proc_id = url.split('/')[-1].replace('.html', '')
    
    # --- 1. Restore Metadata Fields ---
    full_text_raw = soup.get_text()
    correction_match = re.search(r"Correction code\s+(\d+)", full_text_raw)
    frt_match = re.search(r"FRT\s+([\d.]+)", full_text_raw)
    
    # --- 2. Procedure Section Extraction ---
    all_sections = []
    main_content = soup.find('main') or soup.find('article')
    
    if main_content:
        # Tesla typically uses <ol> for sequential steps
        procedure_lists = main_content.find_all(['ol', 'ul'])
        
        for p_list in procedure_lists:
            # Skip lists that are actually inside tables (like Torque tables)
            if p_list.find_parent('table'): continue

            # Find the header (e.g., 'Remove', 'Install')
            header = p_list.find_previous(['h2', 'h3'])
            section_name = clean_text(header.get_text()) if header else "Procedure"
            if section_name.lower() in ['tip', 'torque specifications']: continue

            section_steps = []
            step_counter = 1
            
            for li in p_list.find_all('li', recursive=False):
                # Target the specific 'Note' and 'Tip' containers within the <li>
                # Tesla uses specific classes for these interactive elements
                supplemental_elements = li.find_all(['div', 'span'], class_=re.compile('note|tip|caution|warning', re.I))
                
                tips_notes = []
                for elem in supplemental_elements:
                    label = "Note"
                    class_str = str(elem.get('class', [])).lower()
                    if 'tip' in class_str: label = "Tip"
                    elif 'caution' in class_str: label = "Caution"
                    elif 'warning' in class_str: label = "Warning"
                    
                    content = clean_text(elem.get_text())
                    if content:
                        tips_notes.append({"type": label, "content": content})
                    
                    # CRITICAL: Decompose removes the element from the HTML tree 
                    # so it isn't included in the instruction text
                    elem.decompose()

                # Remaining text after removing Tips/Notes is the instruction
                main_instruction = clean_text(li.get_text())

                section_steps.append({
                    "step_number": step_counter,
                    "instruction": main_instruction,
                    "tips_notes": tips_notes
                })
                step_counter += 1
            
            if section_steps:
                all_sections.append({
                    "section_title": section_name,
                    "steps": section_steps
                })

    # --- 3. Torque & Tool Table Extraction ---
    specs = []
    for table in soup.find_all('table'):
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        if 'torque value' in headers:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    specs.append({
                        "description": clean_text(cols[0].get_text()),
                        "torque": clean_text(cols[1].get_text()),
                        "tools": clean_text(cols[2].get_text()) if len(cols) > 2 else "N/A"
                    })

    return {
        "id": proc_id,
        "title": clean_text(title),
        "section": "10 - Body Panels > 1010 - Body Panels",
        "correction_code": correction_match.group(1) if correction_match else None,
        "frt": frt_match.group(1) if frt_match else "0.0",
        "full_url": url,
        "procedure_sections": all_sections,
        "specifications": specs,
        "full_text": clean_text(full_text_raw) # Restored field
    }

if __name__ == "__main__":
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    service = Service(executable_path=binary_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Note: Ensure your crawler function is defined or imported
    from crawler import crawl_body_panels_section
    root_url = "https://service.tesla.com/docs/ModelY/ServiceManual/2025/en-us/GUID-24F633E2-C64D-4ECB-A6E2-669CF5012901.html"
    procedure_links = crawl_body_panels_section(root_url)

    all_data = []
    for link in tqdm(procedure_links):
        data = scrape_procedure(link["url"], driver, title=link["title"])
        if data: all_data.append(data)

    driver.quit()

    with open("tesla_body_panels_complete.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
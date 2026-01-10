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

ROOT_URL = (
    "https://service.tesla.com/docs/ModelY/ServiceManual/2025/en-us/"
    "GUID-24F633E2-C64D-4ECB-A6E2-669CF5012901.html"
)

SAVE_PATH = "../data/raw/body_panels_procedures.json"

TIP_NOTE_PATTERN = re.compile(
    r'(?:(Tip|TIp|Note|Caution|Warning))\s*(.*?)(?=(?:Tip|TIp|Note|Caution|Warning|$))',
    re.IGNORECASE | re.DOTALL
)


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(
        r'(Expand All\|Collapse All|Expand All|Collapse All|Informational Purposes|'
        r'An informational icon|calling your attention|Warning Icon|A warning icon|'
        r'possibly risky situation)',
        '',
        text,
        flags=re.I
    )
    return " ".join(text.split()).strip().strip(',')


def normalize_section_title(raw_title: str) -> str:
    if not raw_title:
        return "Procedure"
    cleaned = clean_text(raw_title)
    return cleaned.split()[0]


def extract_links_from_li(li_tag):
    links = []
    for a in li_tag.find_all("a", href=True):
        text = clean_text(a.get_text())
        href = a["href"]
        if text and href:
            links.append({"text": text, "url": "https://service.tesla.com/docs/ModelY/ServiceManual/2025/en-us/"+href})
    return links


def split_instruction_and_notes(raw_text: str):
    """
    Splits a step into:
    - main instruction
    - tips/notes/cautions/warnings (even when poorly formatted, e.g. 'NoteDO NOT')
    """
    tips_notes = []

    matches = list(TIP_NOTE_PATTERN.finditer(raw_text))
    if not matches:
        return clean_text(raw_text), tips_notes

    first_match_start = matches[0].start()
    main_instruction = clean_text(raw_text[:first_match_start])

    for m in matches:
        label = m.group(1).capitalize()
        content = clean_text(m.group(2))
        if content:
            tips_notes.append({
                "type": label,
                "content": content
            })

    return main_instruction, tips_notes


def scrape_procedure(url: str, driver, title: str):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
    except Exception:
        return None

    soup = BeautifulSoup(driver.page_source, "html.parser")
    proc_id = url.split('/')[-1].replace('.html', '')

    full_text_raw = soup.get_text()
    correction_match = re.search(r"Correction code\s+(\d+)", full_text_raw)
    frt_match = re.search(r"FRT\s+([\d.]+)", full_text_raw)

    all_sections = []
    main_content = soup.find('main') or soup.find('article')

    if main_content:
        procedure_lists = main_content.find_all(['ol', 'ul'])

        for p_list in procedure_lists:
            if p_list.find_parent('table'):
                continue

            header = p_list.find_previous(['h2', 'h3'])
            section_name = normalize_section_title(
                header.get_text() if header else "Procedure"
            )

            section_steps = []
            step_counter = 1

            for li in p_list.find_all('li', recursive=False):
                hyperlinks = extract_links_from_li(li)

                raw_text = clean_text(li.get_text())
                instruction, tips_notes = split_instruction_and_notes(raw_text)

                if instruction:
                    section_steps.append({
                        "step_number": step_counter,
                        "instruction": instruction,
                        "hyperlinks": hyperlinks,
                        "tips_notes": tips_notes
                    })
                    step_counter += 1

            if len(section_steps) > 1:
                if not any(
                    s["section_title"] == section_name and
                    s["steps"] == section_steps
                    for s in all_sections
                ):
                    all_sections.append({
                        "section_title": section_name,
                        "steps": section_steps
                    })

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
                        "tools": clean_text(cols[2].get_text()) if len(cols) > 2 else "N/A",
                        "reuse/replace": clean_text(cols[3].get_text()) if len(cols) > 3 else "N/A",
                        "notes": clean_text(cols[4].get_text()) if len(cols) > 4 else "N/A"
                    })

    return {
        "id": proc_id,
        "title": clean_text(title),
        "section_category": "10 - Body Panels > 1010 - Body Panels",
        "correction_code": correction_match.group(1) if correction_match else None,
        "frt": frt_match.group(1) if frt_match else "0.0",
        "full_url": url,
        "procedure_sections": all_sections,
        "torque_specifications": specs,
        "full_text": clean_text(full_text_raw)
    }


def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(executable_path=binary_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    from crawler import crawl_body_panels_section

    procedure_links = crawl_body_panels_section(ROOT_URL)

    all_data = []
    for link in tqdm(procedure_links):
        data = scrape_procedure(link["url"], driver, title=link["title"])
        if data:
            all_data.append(data)

    driver.quit()

    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
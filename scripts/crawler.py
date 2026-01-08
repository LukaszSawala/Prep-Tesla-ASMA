import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://service.tesla.com/docs/ModelY/ServiceManual/2025/en-us/"

def crawl_body_panels_section(section_url):
    print("Starting crawl")
    res = requests.get(section_url)
    soup = BeautifulSoup(res.text, "html.parser")

    links = []
    for a in soup.select("main a"):
        href = a.get("href")
        text = a.get_text(strip=True)
        if href and "GUID" in href :
            # clean up title
            title_clean = text.split("Correction code")[0].strip()
            full = urljoin(BASE, href)
            if full not in [l["url"] for l in links] and title_clean != "10 - Body" and "Remove" in title_clean:
                links.append({
                    "title": title_clean,
                    "url": full
                })
    return links

# Example usage
if __name__ == "__main__":
    body_1010_url = "https://service.tesla.com/docs/ModelY/ServiceManual/2025/en-us/GUID-24F633E2-C64D-4ECB-A6E2-669CF5012901.html"
    procedure_links = crawl_body_panels_section(body_1010_url)

    for link in procedure_links:
        print(link)


import json
from tqdm import tqdm
import time
from google import genai
import os
from dotenv import load_dotenv
load_dotenv()

INPUT_PATH = "../data/raw/body_panels_procedures.json"
OUTPUT_PATH = "../data/processed/body_panels_procedures_augmented.json"

# ---------------- Gemini API Setup ----------------
API_KEY = os.getenv("API_KEY")
client = genai.Client(api_key=API_KEY)

def build_prompt(full_text: str) -> str:
    return f"""
    Objective: Analyze the following Tesla Model Y service procedure and extract key metadata.

    Return ONLY a valid JSON object with the following fields:
    - summary: 2-4 sentences
    - safety_flags: list of strings
    - prerequisites: list of strings
    - keywords: list of 5-10 technical keywords

    Procedure text:
    \"\"\"
    {full_text}
    \"\"\"
    """.strip()

def query_gemini(prompt: str) -> dict:
    """
    Sends the prompt to Gemini and parses JSON response.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        print("⚠️ Failed to parse Gemini response:", response.text)
        return None

# ---------------- Main ----------------
def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        procedures = json.load(f)

    i = 0
    for proc in tqdm(procedures, desc="Augmenting procedures"):
        if i>2:
            break
        i+=1

        # Skip already augmented
        if "llm_metadata" in proc:
            continue

        full_text = proc.get("full_text", "")
        if not full_text or len(full_text) < 200:
            continue

        prompt = build_prompt(full_text)
        result = query_gemini(prompt)

        if result:
            proc["llm_metadata"] = result

        # Be polite to API
        time.sleep(3)

    # Always overwrite JSON
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(procedures, f, indent=2, ensure_ascii=False)

    print("✅ Augmented JSON saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
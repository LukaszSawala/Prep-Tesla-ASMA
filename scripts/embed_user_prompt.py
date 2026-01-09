"""
Prototype: Procedure Matching System (Model → Part → Operation)

Flow:
1. Select model (prototype: Model Y only)
2. Load valid parts + operations
3. Extract TOP-3 target parts from free-form user input using Gemini
4. User selects correct part
5. Show available operations
6. Retrieve and display full procedure
"""

import json
import os
import re
from typing import Dict, List
from google import genai
from dotenv import load_dotenv

load_dotenv()

# =========================
# Configuration
# =========================

MODEL_NAME = "gemini-2.5-flash"

MODEL_PARTS_PATH = "../data/model_parts.json"
PROCEDURES_PATH = "../data/body_panels_procedures.json"

API_KEY = os.getenv("API_KEY")
client = genai.Client(api_key=API_KEY)

TOP_K = 3

# =========================
# Utilities
# =========================

def strip_json_fences(text: str) -> str:
    """
    Removes ```json ... ``` or ``` ... ``` fences if present.
    """
    fence_pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(fence_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()

# =========================
# Load Data
# =========================

def load_model_parts(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_procedures(path: str) -> Dict[str, dict]:
    with open(path, "r", encoding="utf-8") as f:
        procedures = json.load(f)
    return {proc["id"]: proc for proc in procedures}

# =========================
# Gemini Grounding
# =========================

def build_part_prompt(user_input: str, valid_parts: List[str]) -> str:
    return f"""
You are matching a technician request to known vehicle parts.

Rules:
- Select UP TO {TOP_K} candidates from the provided list.
- Rank candidates by likelihood (most likely first).
- Use ONLY parts from the provided list.
- If nothing applies, return an empty list.
- Do NOT invent parts.
- Ignore filler words and politeness.
- Handle synonyms and informal language.

Valid target parts:
{json.dumps(valid_parts, indent=2)}

Technician request:
"{user_input}"

Return ONLY valid JSON in this format:
{{
  "candidates": [
    {{ "part": "<valid part name>", "confidence": "high | medium | low" }}
  ]
}}
""".strip()

def query_gemini(prompt: str) -> Dict:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    raw_text = strip_json_fences(response.text)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print("⚠️ Failed to parse Gemini response:")
        print(raw_text)
        return {"candidates": []}

# =========================
# Part Extraction & Selection
# =========================

def extract_part_candidates(user_input: str, valid_parts: List[str]) -> List[Dict]:
    prompt = build_part_prompt(user_input, valid_parts)
    result = query_gemini(prompt)
    return result.get("candidates", [])

def choose_part(candidates: List[Dict]) -> str:
    if not candidates:
        print("❌ No matching parts found.")
        return None

    print("\nPossible target parts:")
    for i, c in enumerate(candidates, 1):
        print(f"{i}. {c['part']} (confidence: {c.get('confidence', 'unknown')})")

    while True:
        try:
            idx = int(input("Select the correct part (number): ")) - 1
            return candidates[idx]["part"]
        except (ValueError, IndexError):
            print("Invalid choice.")

# =========================
# Operation Selection
# =========================

def choose_operation(part_data: List[List[str]]) -> str:
    print("\nAvailable operations:")
    for i, (op, _) in enumerate(part_data, 1):
        print(f"{i}. {op}")

    while True:
        try:
            idx = int(input("Select operation: ")) - 1
            return part_data[idx][0]
        except (ValueError, IndexError):
            print("Invalid choice.")

def get_procedure_id(part_data: List[List[str]], operation: str) -> str:
    for op, guid in part_data:
        if op == operation:
            return guid
    return None

# =========================
# Main
# =========================

def run():
    print("\n=== Technician Assistant Prototype ===\n")

    # Model selection (prototype)
    model = "Model Y"
    print(f"Selected model: {model}")

    model_parts = load_model_parts(MODEL_PARTS_PATH)
    procedures = load_procedures(PROCEDURES_PATH)

    valid_parts = list(model_parts[model].keys())

    user_input = input("\nDescribe what you want to do: ")

    candidates = extract_part_candidates(user_input, valid_parts)
    selected_part = choose_part(candidates)

    if not selected_part:
        print("Aborted.")
        return

    part_data = model_parts[model][selected_part]
    operation = choose_operation(part_data)
    proc_id = get_procedure_id(part_data, operation)

    procedure = procedures.get(proc_id)
    if not procedure:
        print("❌ Procedure not found.")
        return

    print("\n✅ Final result")
    print("Model:", model)
    print("Target part:", selected_part)
    print("Operation:", operation)
    print("Procedure ID:", proc_id)
    print("URL:", procedure.get("full_url"))

    print("\nProcedure summary:")
    for k, v in procedure.get("llm_metadata", {}).items():
        print(f"{k}: {v}")

# =========================
# Entry
# =========================

if __name__ == "__main__":
    run()
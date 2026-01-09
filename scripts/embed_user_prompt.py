"""
Prototype: Procedure Matching System (Model → Part → Operation)

Flow:
1. Select model (prototype: Model Y only)
2. Load valid parts + operations
3. Extract target part from free-form user input using Gemini
4. Ask user for confirmation
5. Show available operations
6. Return selected document ID (stub for now)
"""

import json
from typing import Dict, List, Optional
from google import genai
from dotenv import load_dotenv
import os
import re
load_dotenv()

# =========================
# Configuration
# =========================


MODEL_NAME = "gemini-2.5-flash"

MODEL_PARTS_PATH = "../data/model_parts.json"
PROCEDURES_PATH = "../data/body_panels_procedures.json"

API_KEY = os.getenv("API_KEY")
client = genai.Client(api_key=API_KEY)

# =========================
# Load Data
# =========================

def load_model_parts(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def load_procedures(path: str) -> Dict[str, dict]:
    """
    Load procedures JSON and create a dictionary keyed by procedure ID.
    """
    with open(path, "r", encoding="utf-8") as f:
        procedures_list = json.load(f)

    return {proc["id"]: proc for proc in procedures_list}

# =========================
# Gemini Grounding
# =========================

def build_part_prompt(user_input: str, valid_parts: List[str]) -> str:
    """
    Prompt for grounding free-form user text to a known target part.
    """
    return f"""
            You are matching a technician request to a known vehicle part.

            Rules:
            - Choose EXACTLY one item from the provided list.
            - If none apply, return "unknown".
            - Do NOT invent parts. This is critical.
            - Ignore filler words, politeness, uncertainty, or verbosity.
            - Handle synonyms and informal language.
            - Assess confidence as high, medium, or low.

            Valid target parts:
            {json.dumps(valid_parts, indent=2)}

            Technician request:
            "{user_input}"

            Return ONLY valid JSON of a format:
            {{
            "matched_part": "<one valid target part or 'unknown'>",
            "confidence": "high | medium | low"
            }}
            """.strip()

def query_gemini(prompt: str) -> Dict:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    fence_pattern = r"^```(?:json)?\s*(.*?)\s*```$"
    match = re.match(fence_pattern, response, flags=re.DOTALL | re.IGNORECASE)
    if match:
        response = match.group(1).strip()
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        print("⚠️ Failed to parse Gemini response:", response.text)
        return {"matched_part": "unknown", "confidence": "low"}

# =========================
# Matching & Confirmation
# =========================

def extract_part(user_input: str, valid_parts: List[str]) -> Dict:
    prompt = build_part_prompt(user_input, valid_parts)
    return query_gemini(prompt)

def confirm_part(match: Dict) -> Optional[str]:
    part = match["matched_part"]
    confidence = match.get("confidence", "low")

    if part == "unknown":
        print("❌ Unable to identify target part.")
        return None

    confirm = input(
        f"I identified the part as '{part}' (confidence: {confidence}). Confirm? (y/n): "
    ).strip().lower()

    return part if confirm == "y" else None

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

    model_options = ["Model Y"]
    print("Available models:")
    for i, model in enumerate(model_options, 1):
        print(f"{i}. {model}")

    while True:
        try:
            idx = int(input("Select model: ")) - 1
            model = model_options[idx]
            break
        except (ValueError, IndexError):
            print("Invalid choice.")
    print(f"Selected model: {model}")

    model_parts = load_model_parts(MODEL_PARTS_PATH)
    valid_parts = list(model_parts[model].keys())

    user_input = input("\nDescribe what you want to do: ")

    match = extract_part(user_input, valid_parts)
    confirmed_part = confirm_part(match)

    if not confirmed_part:
        print("Aborted.")
        return

    part_data = model_parts[model][confirmed_part]
    operation = choose_operation(part_data)
    proc_id = get_procedure_id(part_data, operation)

    procedures_dict = load_procedures(PROCEDURES_PATH)
    procedure = procedures_dict.get(proc_id, {})
    print(f"\n✅ Retrieved procedure: {procedure.get('full_url')}\n")
    print("Procedure details:")
    for key in ["id", "target_part", "operation_type"]:
        print(f"{key}: {procedure.get(key)}")
    for key in procedure.get("llm_metadata", {}):
        print(f"{key}: {procedure['llm_metadata'].get(key)}")


# =========================
# Entry
# =========================

if __name__ == "__main__":
    run()
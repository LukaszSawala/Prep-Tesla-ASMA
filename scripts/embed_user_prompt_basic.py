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
# Data Loading
# =========================

def load_model_parts(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_procedures(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# =========================
# Gemini Prompting
# =========================

def build_part_matching_prompt(user_input: str, valid_parts: List[str]) -> str:
    """
    Prompt for grounding free-form user text to a known target part.
    """
    return f"""
            You are matching a technician request to a known vehicle part.

            Rules:
            - Choose EXACTLY one item from the provided list.
            - If none apply, return "unknown".
            - Do NOT invent parts.
            - Ignore filler words, politeness, uncertainty, or verbosity.
            - Handle synonyms and informal language.

            Valid target parts:
            {json.dumps(valid_parts, indent=2)}

            Technician request:
            "{user_input}"

            Return ONLY valid JSON:
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
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {"matched_part": "unknown", "confidence": "low"}

# =========================
# Matching & Confirmation
# =========================

def extract_target_part(
    user_input: str,
    valid_parts: List[str]
) -> Dict:
    prompt = build_part_matching_prompt(user_input, valid_parts)
    return query_gemini(prompt)

def confirm_part(match: Dict) -> Optional[str]:
    part = match.get("matched_part")
    confidence = match.get("confidence", "low")

    if part == "unknown":
        print("❌ Could not confidently identify the target part.")
        return None

    answer = input(
        f"I identified the part as '{part}' (confidence: {confidence}). Confirm? (y/n): "
    ).strip().lower()

    return part if answer == "y" else None

# =========================
# Operation Selection
# =========================

def choose_operation(model: str, part: str, model_parts: Dict) -> str:
    operations = model_parts[model][part]

    print("\nAvailable operations:")
    for i, op in enumerate(operations, 1):
        print(f"{i}. {op}")

    while True:
        try:
            idx = int(input("Select operation: ")) - 1
            return operations[idx]
        except (ValueError, IndexError):
            print("Invalid selection. Try again.")

# =========================
# Procedure Lookup (Prototype)
# =========================

def find_procedure_id(
    procedures: List[Dict],
    target_part: str,
    operation: str
) -> Optional[str]:
    for proc in procedures:
        if (
            proc.get("target_part") == target_part
            and operation.lower() in proc.get("operation_type", [])
        ):
            return proc.get("id")
    return None

# =========================
# Main Loop
# =========================

def run():
    print("\n=== Technician Assistant Prototype ===\n")

    # Load data
    model_parts = load_model_parts(MODEL_PARTS_PATH)
    procedures = load_procedures(PROCEDURES_PATH)

    # Model selection (prototype)
    print("Available models:")
    for model in model_parts.keys():
        print("-", model)

    model = "Model Y"
    input(f"\nSelected model: {model} (press Enter to continue)")

    valid_parts = list(model_parts[model].keys())

    # User input
    user_input = input("\nDescribe what you want to do: ")

    # Extract part
    match = extract_target_part(user_input, valid_parts)

    # Confirm part
    confirmed_part = confirm_part(match)
    if not confirmed_part:
        print("Aborted.")
        return

    # Choose operation
    operation = choose_operation(model, confirmed_part, model_parts)

    # Retrieve procedure ID
    proc_id = find_procedure_id(procedures, confirmed_part, operation.lower())

    print("\n✅ Final Selection:")
    print("Model:", model)
    print("Part:", confirmed_part)
    print("Operation:", operation)

    if proc_id:
        print("Procedure ID:", proc_id)
    else:
        print("⚠️ No procedure ID found (prototype limitation).")

# =========================
# Entry Point
# =========================

if __name__ == "__main__":
    run()
import json
import re
import time
from tqdm import tqdm
from utils import Utils

# ---------------- Paths ----------------
INPUT_PATH = "../data/raw/body_panels_procedures.json"      # Raw scraped procedures
OUTPUT_PATH = "../data/processed/body_panels_procedures_augmented.json"  # Final merged output

utils_handler = Utils()

# ---------------- Constants ----------------
OPERATION_KEYWORDS = ["remove", "install", "replace", "inspect", "tighten", "adjust", "disconnect", "reconnect"]

# ---------------- Helpers ----------------
def parse_frt(frt_value):
    """Convert FRT string to float"""
    if not frt_value:
        return None
    try:
        return float(frt_value)
    except ValueError:
        match = re.search(r"[\d\.]+", frt_value)
        return float(match.group()) if match else None

def split_target_and_operations(title: str):
    """
    Split title into target and operation types.
    Example: "Fem Bracket - LH (Remove and Replace)"
    -> target: "Fem Bracket - LH"
       operation_type: ["remove", "replace"]
    """
    match = re.match(r"^(.*?)\s*\((.*?)\)\s*$", title)
    if match:
        target = match.group(1).strip()
        ops_text = match.group(2).lower()
        operation_type = [op for op in OPERATION_KEYWORDS if op in ops_text]
        return target, operation_type
    else:
        # fallback
        return title, []

def build_prompt(full_text: str) -> str:
    return f"""
    Objective: Analyze the following Tesla Model Y service procedure and extract key metadata.

    Return ONLY a valid JSON object with the following fields:
    - summary: 2-4 sentences describing the procedure, including what is being removed/installed/repaired,
               key preparatory steps, critical precautions, and main tools used.
    - safety_flags: list of strings. Include electrical, mechanical, ergonomic, or PPE hazards.
    - prerequisites: list of strings. Include tools, fixtures, consumables required for the procedure.
    - keywords: list of 5-10 concise, semantic terms useful for matching user requests.
                Focus on components, actions, and location descriptors.

    Procedure text:
    \"\"\"
    {full_text}
    \"\"\"
    """.strip()

# ---------------- Main ----------------
def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        procedures = json.load(f)

    merged_procs = []

    for proc in tqdm(procedures, desc="Processing procedures"):

        # Skip if no meaningful text
        full_text = proc.get("full_text", "")
        if not full_text or len(full_text) < 200:
            continue

        # ---------------- LLM augmentation ----------------
        prompt = build_prompt(full_text)
        llm_result = utils_handler.query_gemini(prompt)
        if not llm_result:
            llm_result = {}

        # ---------------- Process title ----------------
        target_part, operation_type = split_target_and_operations(proc.get("title", ""))

        # ---------------- Build merged procedure ----------------
        merged_proc = proc.copy()
        merged_proc["frt"] = parse_frt(merged_proc.get("frt"))
        merged_proc["target_part"] = target_part
        merged_proc["operation_type"] = operation_type

        # Remove old title & full_text
        merged_proc.pop("title", None)
        merged_proc.pop("full_text", None)

        # Attach LLM metadata
        merged_proc["llm_metadata"] = llm_result

        merged_procs.append(merged_proc)

        # Be polite to API
        time.sleep(1)

    # ---------------- Save output ----------------
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged_procs, f, indent=2, ensure_ascii=False)

    print(f"✅ Augmented and merged JSON saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
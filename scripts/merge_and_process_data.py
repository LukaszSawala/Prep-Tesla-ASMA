import json
import re

# Paths
ORIGINAL_PATH = "../data/raw/body_panels_procedures.json"          # Original scraped procedures
AUGMENTED_PATH = "../data/raw/augmentations.json"  # Only first 3 with LLM metadata
OUTPUT_PATH = "../data/processed/body_panels_procedures_augmented.json"    # New file

# Known operation keywords
OPERATION_KEYWORDS = ["remove", "install", "replace", "inspect", "tighten", "adjust", "disconnect", "reconnect"]

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
        # Extract operations based on known keywords
        operation_type = [op for op in OPERATION_KEYWORDS if op in ops_text]
        return target, operation_type
    else:
        # fallback
        return title, []

def main():
    # Load original procedures
    with open(ORIGINAL_PATH, "r", encoding="utf-8") as f:
        original_procs = json.load(f)

    # Load LLM-generated summaries
    with open(AUGMENTED_PATH, "r", encoding="utf-8") as f:
        llm_data = json.load(f)

    merged_procs = []
    for i in range(min(3, len(original_procs), len(llm_data))):
        proc = original_procs[i].copy()
        # Convert FRT to float
        proc["frt"] = parse_frt(proc.get("frt"))
        # Split title into target + operation_type
        target, operation_type = split_target_and_operations(proc.get("title", ""))
        proc["target_part"] = target
        proc["operation_type"] = operation_type
        # Remove old title
        proc.pop("title", None)
        # Add LLM-generated fields at top level
        proc["llm_metadata"] = proc.get("llm_metadata", {})
        proc["llm_metadata"].update(llm_data[i])
        # Remove full_text
        proc.pop("full_text", None)
        merged_procs.append(proc)

    # Save only the first 3 augmented procedures
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged_procs, f, indent=2, ensure_ascii=False)

    print(f"✅ Merged JSON saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
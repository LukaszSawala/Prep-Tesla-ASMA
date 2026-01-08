import json
import re

INPUT_PATH = "../data/raw/body_panels_procedures.json"
OUTPUT_PATH = "../data/model_parts_actions.json"

# Expandable list of supported models
MODELS = ["Model Y"]


def extract_part_and_action(title: str):
    """
    From: 'Brace - Shock Tower (Remove and Replace)'
    Returns:
        part = 'Brace - Shock Tower'
        action = 'Remove and Replace'
    """
    if not title:
        return None, None

    action_match = re.search(r"\((.*?)\)", title)
    action = action_match.group(1).strip() if action_match else None

    part = re.sub(r"\(.*?\)", "", title).strip()

    return part, action


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        procedures = json.load(f)

    # Initialize output structure
    output = {model: {} for model in MODELS}

    for proc in procedures:
        title = proc.get("title", "")
        if not title:
            continue

        # For now, everything belongs to Model Y
        model = "Model Y"

        part, action = extract_part_and_action(title)
        if not part or not action:
            continue

        model_parts = output[model]

        if part not in model_parts:
            model_parts[part] = []

        if action not in model_parts[part]:
            model_parts[part].append(action)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved model → parts → actions to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
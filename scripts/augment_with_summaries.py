import json
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from tqdm import tqdm

INPUT_PATH = "../data/body_panels_procedures.json"
OUTPUT_PATH = "../data/body_panels_procedures_augmented.json"

# Load model
model_name = "google/flan-t5-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def build_prompt(full_text: str) -> str:
    return f"""
            Extract the following from the Tesla procedure text. If a field is not present, leave it empty or null.

            Return as valid JSON:
            - summary: 2-4 sentences
            - safety_flags: list of strings
            - prerequisites: list of strings
            - keywords: list of 5-10 technical keywords

            Procedure text:
            \"\"\"
            {full_text}
            \"\"\"
            """

def query_model(prompt: str) -> dict:
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    outputs = model.generate(**inputs, max_new_tokens=512)
    text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("Failed to parse JSON:", text)
        return None

def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        procedures = json.load(f)

    for proc in tqdm(procedures, desc="Augmenting procedures"):
        if "llm_metadata" in proc:
            continue
        full_text = proc.get("full_text", "")
        if not full_text or len(full_text) < 200:
            continue
        prompt = build_prompt(full_text)
        result = query_model(prompt)
        if result:
            proc["llm_metadata"] = result

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(procedures, f, indent=2, ensure_ascii=False)

    print("✅ Augmented JSON saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
import os
import re
import json
import uuid
from datetime import datetime, UTC
from typing import Dict
from google import genai
from dotenv import load_dotenv
load_dotenv()

# =========================
INPUT_PATH = "../data/raw/body_panels_procedures.json"
OUTPUT_PATH = "../data/processed/body_panels_procedures_augmented.json"
LOG_DIR = "../logs"
API_KEY = os.getenv("API_KEY")
# =========================
    

class Utils:
    """
    General utility functions like querying the Gemini or saving logs.
    """
    def __init__(self):
        self._client = genai.Client(api_key=API_KEY)

    def query_gemini(self, prompt: str) -> dict:
        """
        Sends the prompt to Gemini and parses JSON response.
        """
        def strip_json_fences(text: str) -> str:
            fence_pattern = r"```(?:json)?\s*(.*?)\s*```"
            match = re.search(fence_pattern, text, flags=re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else text.strip()

        
        response = self._client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        cleaned_text = strip_json_fences(response.text)
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            print("⚠️ Failed to parse Gemini response:", cleaned_text)
            return None

    def save_log(self, log_data: Dict, error: bool = False, run_stage: str = None) -> None:
        """
        Saves log data to a timestamped JSON file.
        """
        path = os.path.join(LOG_DIR, run_stage) # subdir for stage of the logging
        if error:
            path = os.path.join(path, "errors") # change the path to error subdir
        else:
            path = os.path.join(path, "normal")

        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        log_id = str(uuid.uuid4())
        filename = f"{timestamp}_{log_id}.json"
        path = os.path.join(path, filename)

        log_data["log_id"] = log_id
        log_data["timestamp"] = timestamp    
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

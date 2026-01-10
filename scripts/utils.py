import os
import re
import json
import uuid
from datetime import datetime, UTC
from typing import Dict
from google import genai
from text_to_speech import record_and_transcribe, parse_choice
from dotenv import load_dotenv
load_dotenv()

# =========================
INPUT_PATH = "../data/raw/body_panels_procedures.json"
OUTPUT_PATH = "../data/processed/body_panels_procedures_augmented.json"
LOG_DIR = "../logs"
API_KEY = os.getenv("API_KEY")
# =========================


class UserInputHandler:
    """
    Handles both text and voice input, including number parsing and
    voice/text switching.
    """

    def __init__(self, mode="text"):
        """
        mode: "text" or "voice"
        """
        self.mode = mode

    def set_mode(self, mode: str):
        if mode in ["text", "voice"]:
            self.mode = mode

    def get_input(self, prompt: str, expect_choice=False, max_choice=None) -> str:
        """
        Get user input based on the current mode.
        """
        print(prompt)

        # -------------------------
        # TEXT MODE
        # -------------------------
        if self.mode == "text":
            user_input = input("> ").strip()

            if user_input == "404":
                print("🔄 Switching to VOICE mode")
                self.mode = "voice"
                return self.get_input(prompt, expect_choice, max_choice)

            return user_input

        # -------------------------
        # VOICE MODE
        # -------------------------
        transcript = record_and_transcribe()

        if not transcript:
            print("⚠️ No speech detected → switching to TEXT")
            self.mode = "text"
            return self.get_input(prompt, expect_choice, max_choice)

        print(f"🗣️ Heard: {transcript}")

        if expect_choice:
            choice = parse_choice(transcript)
            if choice is None:
                print("❌ Could not understand selection.")
                return self.get_input(prompt, expect_choice, max_choice)

            if max_choice is not None and not (1 <= choice <= max_choice):
                print("❌ Choice out of range.")
                return self.get_input(prompt, expect_choice, max_choice)

            return str(choice)

        return transcript
    


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

    def save_log(self, log_data: Dict, error: bool = False):
        """
        Saves log data to a timestamped JSON file.
        """
        if error:
            path = os.path.join(LOG_DIR, "errors") # change the path to error subdir
        else:
            path = os.path.join(LOG_DIR, "normal")

        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        log_id = str(uuid.uuid4())
        filename = f"{timestamp}_{log_id}.json"
        path = os.path.join(path, filename)

        log_data["log_id"] = log_id
        log_data["timestamp"] = timestamp    
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

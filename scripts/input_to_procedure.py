"""
Phase 1 Prototype — Procedure Matching System (Model → Part → Operation)

Responsibilities:
- Model & part selection
- Candidate retrieval & disambiguation
- Operation selection
- Procedure retrieval
- Feedback logging

Phase 2 will extend this with step-level guidance.
"""

import json
import os
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from user_input_handler import UserInputHandler
from utils import Utils

load_dotenv()

# =========================
# Configuration
# =========================

MODEL_NAME = "gemini-2.5-flash"

MODEL_PARTS_PATH = "../data/model_parts.json"
PROCEDURES_PATH = "../data/processed/body_panels_procedures_augmented.json"

API_KEY = os.getenv("API_KEY")
TOP_K = 3


# =========================
# Procedure Assistant Class
# =========================

class ProcedureRetriever:
    def __init__(self, input_mode: str = "text"):
        self.input_handler = UserInputHandler(mode=input_mode)
        self.utils = Utils()
        self.model_parts = self._load_json(MODEL_PARTS_PATH)
        self.procedures = self._load_json(PROCEDURES_PATH, by_id=True)

    # -------------------------
    # JSON Loaders
    # -------------------------

    def _load_json(self, path: str, by_id: bool = False) -> Dict:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if by_id:
            return {proc["id"]: proc for proc in data}
        return data

    # -------------------------
    # Part Candidate Prompt
    # -------------------------

    def _build_part_prompt(self, user_input: str, valid_parts: List[str]) -> str:
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

        Return ONLY valid JSON:
        {{
        "candidates": [
            {{ "part": "<valid part name>", "confidence": "high | medium | low" }}
        ]
        }}
        """.strip()

    def _extract_part_candidates(self, user_input: str, valid_parts: List[str]) -> List[Dict]:
        prompt = self._build_part_prompt(user_input, valid_parts)
        result = self.utils.query_gemini(prompt)
        return result.get("candidates", [])

    # -------------------------
    # Part Selection (Loop + Retry)
    # -------------------------

    def _choose_part(self, initial_input: str, valid_parts: List[str]) -> Tuple[str, List[Dict]]:
        user_input = initial_input
        while True:
            candidates = self._extract_part_candidates(user_input, valid_parts)

            if not candidates:
                print("❌ No matching parts found. You can retry with a new prompt.")
            else:
                print("\nPossible target parts:")
                for i, c in enumerate(candidates, 1):
                    print(f"{i}. {c['part']} (confidence: {c.get('confidence', 'unknown')})")

            try:
                idx = int(
                    self.input_handler.get_input(
                        "Select the correct part (number) or 202 to retry:",
                        expect_choice=True,
                        max_choice=max(len(candidates), 202)
                    )
                )
            except ValueError:
                print("Invalid input. Try again.")
                continue

            if idx == 202:
                user_input = self.input_handler.get_input("Enter a new description of the part:")
                continue
            elif 1 <= idx <= len(candidates):
                return candidates[idx - 1]["part"], candidates
            else:
                print("Invalid choice. Try again.")

    # -------------------------
    # Operation Selection
    # -------------------------

    def _choose_operation(self, part_data: List[List[str]]) -> str:
        print("\nAvailable operations:")
        for i, (op, _) in enumerate(part_data, 1):
            print(f"{i}. {op}")

        idx = int(
            self.input_handler.get_input(
                "Select operation (number):",
                expect_choice=True,
                max_choice=len(part_data)
            )
        ) - 1
        return part_data[idx][0]

    def _get_procedure_id(self, part_data: List[List[str]], operation: str) -> str:
        for op, guid in part_data:
            if op == operation:
                return guid
        return None

    # -------------------------
    # Feedback Logging
    # -------------------------

    def _collect_feedback(self) -> Dict:
        error = self.input_handler.get_input("\nDid anything go wrong? (y/n):").strip().lower() == "y"
        comment = ""
        if error:
            comment = self.input_handler.get_input("Please describe the issue:").strip()
        return {"error": error, "comment": comment}

    # -------------------------
    # Main Procedure Retrieval Flow
    # -------------------------

    def retrieve_procedure(self, assistant_mode: bool = False) -> dict:
        # return self.procedures.get("GUID-3854CC14-6DD1-4CFE-A639-A8464023F1C7") # temporary bypass for testing
        print("\n=== Technician Assistant Prototype ===\n")

        # Input method selection
        print("Choose input method:")
        print("1. Text")
        print("2. Voice")
        while True:
            choice = input("> ").strip()
            if choice == "1":
                self.input_handler.mode = "text"
                break
            elif choice == "2":
                self.input_handler.mode = "voice"
                break
            else:
                print("Invalid choice.")

        # Model selection
        models = ["Model Y"]
        for i, m in enumerate(models, 1):
            print(f"{i}. {m}")

        model_idx = int(
            self.input_handler.get_input(
                "Select model (number):",
                expect_choice=True,
                max_choice=len(models)
            )
        ) - 1
        model = models[model_idx]
        print(f"Selected model: {model}")

        # Retrieve parts
        valid_parts = list(self.model_parts[model].keys())
        user_input = self.input_handler.get_input("\nDescribe what you want to do:")
        selected_part, candidates = self._choose_part(user_input, valid_parts)

        if not selected_part:
            print("Aborted.")
            return {}

        # Retrieve operation and procedure
        part_data = self.model_parts[model][selected_part]
        operation = self._choose_operation(part_data)
        proc_id = self._get_procedure_id(part_data, operation)
        procedure = self.procedures.get(proc_id)

        if not assistant_mode:
            print("\n✅ Procedure Retrieved:")
            print("Target part:", selected_part)
            print("Operation:", operation)
            print("Procedure ID:", proc_id)
            print("URL:", procedure.get("full_url"))
            print("Summary:", procedure.get("llm_metadata", {}).get("summary", "N/A"))

        # Collect feedback
        feedback = self._collect_feedback()

        # Log interaction
        self.utils.save_log(
            run_stage="procedure_retrieval",
            error=feedback.get("error", False),
            log_data={
                "model": model,
                "user_prompt": user_input,
                "llm_part_candidates": candidates,
                "selected_part": selected_part,
                "selected_operation": operation,
                "procedure_id": proc_id,
                "feedback": feedback
            }
        )
        print("\n📝 Interaction logged.")

        return procedure


# =========================
# Entry
# =========================

def main():
    assistant = ProcedureRetriever(input_mode="text")
    procedure = assistant.retrieve_procedure()
    return procedure


if __name__ == "__main__":
    main()
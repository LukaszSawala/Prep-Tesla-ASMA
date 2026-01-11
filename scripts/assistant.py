"""
Phase 2 Technician Assistant Prototype with Resume / Checkpointing
Logic:
Step 0: Prerequisites
→ Subprocedure A: Step 1 → confirm → Step 2 → confirm → …
→ Confirm move to next subprocedure
→ Subprocedure B → …
→ End

Checkpointing:
- Saves progress after each step in ../logs/step_assistant/saves/<procedure_id>.json
- Only one save per procedure
- Resume restores next unconfirmed step
"""

import json
import os
from pathlib import Path
from typing import Optional

from input_to_procedure import ProcedureRetriever
from user_input_handler import UserInputHandler


SAVE_DIR = "../logs/step_assistant/saves/"
os.makedirs(SAVE_DIR, exist_ok=True)


# =========================
# Step Manager
# =========================

class StepManager:
    """
    Deterministic step executor for a single procedure with checkpointing.
    """

    def __init__(
        self,
        procedure: dict,
        input_mode: str = "text",
        start_subprocedure_idx: int = 0,
        start_step_idx: int = 0,
    ):
        self.procedure = procedure
        self.procedure_id = procedure.get("id")
        self.procedure_title = procedure.get("title", "Unknown Procedure")
        self.llm_metadata = procedure.get("llm_metadata", {})
        self.sections = procedure.get("procedure_sections", [])
        self.input_handler = UserInputHandler(mode=input_mode)

        # Resume indices
        self.current_subprocedure_idx = start_subprocedure_idx
        self.current_step_idx = start_step_idx

        # Save path
        self.save_path = Path(SAVE_DIR) / f"{self.procedure_id}.json"

    # -------------------------
    # Public entry point
    # -------------------------

    def run(self) -> None:
        self._print_header()
        self._run_prerequisites()
        self._run_subprocedures()
        self._print_footer()
        # Clear save after completion
        if self.save_path.exists():
            self.save_path.unlink()
            print("\n🗑️  Save cleared as procedure is complete.")

    # -------------------------
    # Internal helpers
    # -------------------------

    def _save_state(self) -> None:
        state = {
            "procedure_id": self.procedure_id,
            "procedure_title": self.procedure_title,
            "subprocedure_idx": self.current_subprocedure_idx,
            "step_idx": self.current_step_idx,
        }
        with open(self.save_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def _require_yes(self, prompt: str) -> None:
        """
        Blocks execution until the user explicitly confirms.
        Uses the shared UserInputHandler (text / voice).
        Saves progress after each confirmation.
        """
        while True:
            answer = self.input_handler.get_input(f"{prompt}:").strip().lower()
            if "yes" in answer or answer == "y":
                self._save_state()
                return
            print("❌ Please explicitly confirm by typing or saying 'yes'.")

    def _print_header(self) -> None:
        print("\n" + "=" * 80)
        print("📘 PROCEDURE START")
        print("=" * 80)
        print("\nTitle:", self.procedure.get("title"))
        print("URL:", self.procedure.get("full_url"))

    def _print_footer(self) -> None:
        print("\n" + "=" * 80)
        print("✅ PROCEDURE COMPLETE")
        print("=" * 80)

    # -------------------------
    # Step 0 — Prerequisites
    # -------------------------

    def _run_prerequisites(self) -> None:
        prerequisites = self.llm_metadata.get("prerequisites", [])
        if not prerequisites:
            return

        print("\n--- STEP 0: PREREQUISITES ---")
        for i, item in enumerate(prerequisites, 1):
            print(f"{i}. {item}")

        self._require_yes("Have all prerequisites been reviewed and satisfied")

    # -------------------------
    # Subprocedures
    # -------------------------

    def _run_subprocedures(self) -> None:
        for s_idx in range(self.current_subprocedure_idx, len(self.sections)):
            section = self.sections[s_idx]
            self.current_subprocedure_idx = s_idx
            self._run_single_subprocedure(section, s_idx)

    def _run_single_subprocedure(self, section: dict, section_idx: int) -> None:
        section_title = section.get("section_title", f"Section {section_idx}")
        steps = section.get("steps", [])

        print("\n" + "=" * 50)
        print(f"🔧 SUBPROCEDURE: {section_title}")
        print("=" * 50)

        # Resume from saved step index
        start_step = self.current_step_idx if section_idx == self.current_subprocedure_idx else 0

        # **Increment start_step by 1 if resuming so we skip already confirmed step**
        if start_step > 0:
            start_step += 1

        for step_idx in range(start_step, len(steps)):
            self.current_step_idx = step_idx
            step = steps[step_idx]
            self._run_single_step(step_idx + 1, step)

        self.current_step_idx = 0  # Reset for next subprocedure
        self._require_yes(
            f"Subprocedure '{section_title}' completed. "
            "Confirm before moving to the next subprocedure"
        )

    # -------------------------
    # Individual step
    # -------------------------

    def _run_single_step(self, step_number: int, step: dict) -> None:
        instruction = step.get("instruction", "").strip()
        tips_notes = step.get("tips_notes", [])
        hyperlinks = step.get("hyperlinks", [])

        print("\n" + "=" * 30)
        print(f"Step {step_number}")
        print(instruction)

        if tips_notes:
            print("\nNotes / Tips:")
            for note in tips_notes:
                content = note.get("content")
                if content:
                    print("-", content)

        if hyperlinks:
            print("\nRelated Links:")
            for link in hyperlinks:
                print(f"- {link['text']}: {link['url']}")

        self._require_yes(f"Finished step {step_number}")


# =========================
# Startup / Save selection
# ==========================

def select_startup_option(input_handler: UserInputHandler) -> Optional[StepManager]:
    saves = list(Path(SAVE_DIR).glob("*.json"))
    if saves:
        print("\nSaved procedures found:")
        for i, s in enumerate(saves, 1):
            # Load the save to show step number
            try:
                with open(s, "r", encoding="utf-8") as f:
                    state = json.load(f)
                step_num = state.get("step_idx", 0) + 1  # Display next step
                title = state.get("procedure_title", s.stem)
            except Exception:
                step_num = 0
                title = s.stem
            print(f"{i}. {title} - step {step_num}")

        print(f"{len(saves)+1}. Start a new procedure")
        choice = input_handler.get_input("Select option (number):").strip()

        try:
            choice_idx = int(choice) - 1
        except ValueError:
            print("Invalid input. Starting new procedure.")
            choice_idx = len(saves)  # new procedure

        if 0 <= choice_idx < len(saves):
            # Load save
            with open(saves[choice_idx], "r", encoding="utf-8") as f:
                state = json.load(f)

            retriever = ProcedureRetriever(input_mode=input_handler.mode)
            procedures = retriever.procedures
            procedure = procedures.get(state["procedure_id"])

            if not procedure:
                print("❌ Saved procedure not found. Starting new procedure.")
                return None

            return StepManager(
                procedure,
                input_mode=input_handler.mode,
                start_subprocedure_idx=state.get("subprocedure_idx", 0),
                start_step_idx=state.get("step_idx", 0)
            )
        else:
            return None  # Start new
    else:
        print("No saved procedures found.")
        return None  # No saves found


# =========================
# Main
# ==========================

def main():
    input_handler = UserInputHandler(mode="text")

    manager = select_startup_option(input_handler)
    if not manager:
        # Start new procedure
        retriever = ProcedureRetriever(input_mode=input_handler.mode)
        procedure = retriever.retrieve_procedure()
        if not procedure:
            print("❌ No procedure retrieved. Exiting.")
            return
        manager = StepManager(procedure, input_mode=input_handler.mode)

    manager.run()


if __name__ == "__main__":
    main()
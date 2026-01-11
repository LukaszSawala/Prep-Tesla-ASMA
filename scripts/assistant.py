"""
Phase 2 of the Technician Assistant Prototype.

Logic:
Prerequisites (step 0)
→ Subprocedure A
   → Step 1 → confirm → Step 2 → confirm → …
→ Confirm move to next subprocedure
→ Subprocedure B
→ …
→ End
"""

from input_to_procedure import ProcedureRetriever
from user_input_handler import UserInputHandler


# =========================
# Step Manager
# =========================

class StepManager:
    """
    Deterministic step executor for a single procedure.
    Responsible ONLY for step order and explicit confirmation.
    """

    def __init__(self, procedure: dict, input_mode: str = "text"):
        self.procedure = procedure
        self.llm_metadata = procedure.get("llm_metadata", {})
        self.sections = procedure.get("procedure_sections", [])
        self.input_handler = UserInputHandler(mode=input_mode)

    # -------------------------
    # Public entry point
    # -------------------------

    def run(self) -> None:
        self._print_header()
        self._run_prerequisites()
        self._run_subprocedures()
        self._print_footer()

    # -------------------------
    # Internal helpers
    # -------------------------

    def _require_yes(self, prompt: str) -> None:
        """
        Blocks execution until the user explicitly confirms.
        Uses the shared UserInputHandler (text / voice).
        """
        while True:
            answer = self.input_handler.get_input(
                f"{prompt}:"
            ).strip().lower()

            if "yes" in answer.lower() or answer == "y":
                return

            print("❌ Please explicitly confirm by saying or typing 'yes'.")

    def _print_header(self) -> None:
        print()
        print("=" * 80)
        print("📘 PROCEDURE START")
        print("=" * 80)
        print("\nTitle:", self.procedure.get("title"))
        print("URL:", self.procedure.get("full_url"))

    def _print_footer(self) -> None:
        print()
        print("=" * 80)
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
        for section_idx, section in enumerate(self.sections, 1):
            self._run_single_subprocedure(section, section_idx)

    def _run_single_subprocedure(self, section: dict, section_idx: int) -> None:
        section_title = section.get("section_title", f"Section {section_idx}")
        steps = section.get("steps", [])

        print()
        print("=" * 50)
        print(f"🔧 SUBPROCEDURE: {section_title}")
        print("=" * 50)

        for step_idx, step in enumerate(steps, 1):
            self._run_single_step(step_idx, step)

        self._require_yes(
            f"Subprocedure '{section_title}' completed. "
            "Confirm before moving to the next subprocedure"
        )

    # -------------------------
    # Individual step
    # -------------------------

    def _run_single_step(self, step_id: int, step: dict) -> None:
        instruction = step.get("instruction", "").strip()
        tips_notes = step.get("tips_notes", [])
        hyperlinks = step.get("hyperlinks", [])

        print("\n==============================")
        print(f"Step {step_id}")
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

        self._require_yes(f"Finished step {step_id}")


# =========================
# Main entry
# =========================

def main():
    assistant = ProcedureRetriever(input_mode="text")
    procedure = assistant.retrieve_procedure()

    if not procedure:
        print("❌ No procedure retrieved. Exiting.")
        return

    # Input mode already chosen earlier in the pipeline
    manager = StepManager(procedure, input_mode="text")
    manager.run()


if __name__ == "__main__":
    main()
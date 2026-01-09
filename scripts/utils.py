from text_to_speech import record_and_transcribe, parse_choice

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
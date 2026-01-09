import sounddevice as sd
import numpy as np
import re
from faster_whisper import WhisperModel

# =========================
# Configuration
# =========================

SAMPLE_RATE = 16000
MODEL_SIZE = "small"

# =========================
# Recorder
# =========================

class Recorder:
    def __init__(self, samplerate=SAMPLE_RATE):
        self.samplerate = samplerate
        self.frames = []
        self.recording = False
        self.stream = None

    def callback(self, indata, frames, time, status):
        if self.recording:
            self.frames.append(indata.copy())

    def start(self):
        self.frames = []
        self.recording = True
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            callback=self.callback
        )
        self.stream.start()
        print("🎤 Recording... Press ENTER to stop.")

    def stop(self):
        self.recording = False
        self.stream.stop()
        self.stream.close()

        if not self.frames:
            return None

        return np.concatenate(self.frames, axis=0).flatten()

# =========================
# Whisper
# =========================

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel(MODEL_SIZE)
    return _whisper_model

def transcribe_audio(audio: np.ndarray) -> str:
    model = get_whisper_model()
    segments, _ = model.transcribe(audio, beam_size=5)
    return " ".join(seg.text.strip() for seg in segments).strip()

def record_and_transcribe() -> str:
    recorder = Recorder()

    input("🎤 Voice input selected. Press ENTER to start...")
    recorder.start()
    input()
    audio = recorder.stop()

    if audio is None:
        return ""

    return transcribe_audio(audio)

# =========================
# Choice Parsing
# =========================

def get_number_words():
    return {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20
    }

def parse_choice(text: str):
    if not text:
        return None

    text = text.lower()

    # numeric digit
    digit_match = re.search(r"\b(\d+)\b", text)
    if digit_match:
        return int(digit_match.group(1))

    # number words
    for word, value in get_number_words().items():
        if word in text:
            return value

    return None
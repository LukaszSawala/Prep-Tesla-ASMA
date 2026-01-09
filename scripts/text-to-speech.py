import sounddevice as sd
import numpy as np
import json
from faster_whisper import WhisperModel

# --------- CONFIG ----------
SAMPLE_RATE = 16000       # Whisper requires 16 kHz
OUTPUT_JSON = "../data/speech_transcripts.json"
MODEL_SIZE = "small"      # can also use "base", "medium", "large"
# ---------------------------

class Recorder:
    def __init__(self, samplerate=SAMPLE_RATE):
        self.samplerate = samplerate
        self.frames = []
        self.recording = False

    def callback(self, indata, frames, time, status):
        if self.recording:
            self.frames.append(indata.copy())

    def start(self):
        self.frames = []
        self.recording = True
        self.stream = sd.InputStream(samplerate=self.samplerate, channels=1, callback=self.callback)
        self.stream.start()
        print("Recording... Press ENTER to stop.")

    def stop(self):
        self.recording = False
        self.stream.stop()
        self.stream.close()
        audio = np.concatenate(self.frames, axis=0).flatten()
        print("Recording stopped.")
        return audio

def transcribe_audio(audio, model_size=MODEL_SIZE):
    print("Loading Whisper model...")
    model = WhisperModel(model_size)
    print("Transcribing...")
    segments, _ = model.transcribe(audio, beam_size=5)
    transcript = " ".join([seg.text for seg in segments])
    print("Transcription complete.")
    return transcript

def save_transcript_json(transcript, output_file=OUTPUT_JSON):
    data = {"transcript": transcript}
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Transcript saved to {output_file}")

def main():
    recorder = Recorder()

    input("Press ENTER to start recording...")
    recorder.start()

    # Wait until user presses ENTER again
    input()
    audio = recorder.stop()

    transcript = transcribe_audio(audio)
    print("The following was heard:", transcript)
    save_transcript_json(transcript)

if __name__ == "__main__":
    main()
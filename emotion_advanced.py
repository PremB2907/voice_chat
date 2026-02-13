from TTS.api import TTS
import random

print("🔊 Loading XTTS model...")
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")

emotion = input("Choose emotion (happy/sad/angry/calm): ").lower()
intensity = input("Intensity (low/medium/high): ").lower()

base_text = "Prem, I am speaking to you right now."

emotion_modifiers = {
    "happy": {
        "low": "Hey Prem. I'm really glad about this.",
        "medium": "Hey Prem! This is really exciting!",
        "high": "PREM!! This is absolutely incredible!! I'm so proud of you!!!"
    },
    "sad": {
        "low": "Prem... it's okay.",
        "medium": "Prem... I'm here with you. It's going to be alright.",
        "high": "Prem... I know this hurts deeply. But I’m right here."
    },
    "angry": {
        "low": "Prem. Focus.",
        "medium": "Prem! You need to concentrate.",
        "high": "PREM! This cannot continue. You must discipline yourself!"
    },
    "calm": {
        "low": "Prem. Relax.",
        "medium": "Prem. Take a slow breath. Everything is steady.",
        "high": "Prem. Close your eyes. Breathe deeply. Let everything settle."
    }
}

text = emotion_modifiers.get(emotion, emotion_modifiers["calm"]).get(intensity, base_text)

print("🎤 Generating emotional voice...")

tts.tts_to_file(
    text=text,
    speaker_wav=[
        "voice_samples/sample1.wav",
        "voice_samples/sample2.wav",
        "voice_samples/sample3.wav",
        "voice_samples/sample4.wav"
    ],
    language="en",
    file_path=f"{emotion}_{intensity}_output.wav"
)

print(f"✅ DONE! Output saved as {emotion}_{intensity}_output.wav")

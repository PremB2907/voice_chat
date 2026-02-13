from TTS.api import TTS

print("🔊 Loading XTTS model...")
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")

emotion = input("Choose emotion (happy/sad/angry/calm): ").lower()

texts = {
    "happy": "Hey Prem!! I'm so proud of you! This is absolutely amazing!",
    "sad": "Hello Prem... I'm here with you. It's going to be okay.",
    "angry": "Prem! Listen carefully. You must focus and stay disciplined.",
    "calm": "Hello Prem. Take a deep breath. Everything is under control."
}

text = texts.get(emotion, texts["calm"])

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
    file_path=f"{emotion}_output.wav"
)

print(f"✅ DONE! Output saved as {emotion}_output.wav")

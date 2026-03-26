from TTS.api import TTS

print("🔊 Loading XTTS model...")

tts = TTS(
    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
    gpu=False
)

print("🎤 Generating cloned voice...")

tts.tts_to_file(
    text="Hello Prem. Your cloned voice system is now alive.",
    speaker_wav=[
        "voice_samples/sample1.wav",
        "voice_samples/sample2.wav",
        "voice_samples/sample3.wav",
        "voice_samples/sample4.wav"
    ],
    language="en",
    file_path="cloned_output.wav"
)

print("✅ DONE! Output saved as cloned_output.wav")

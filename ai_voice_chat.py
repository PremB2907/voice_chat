import os
from openai import OpenAI
from TTS.api import TTS

print("🔊 Loading XTTS model...")
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")

client = OpenAI()

print("🤖 AI Voice Chat Started")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        break

    # Generate AI response
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are intelligent and emotionally aware."},
            {"role": "user", "content": user_input}
        ]
    )

    ai_text = response.choices[0].message.content
    print("AI:", ai_text)

    print("🎤 Generating voice...")

    tts.tts_to_file(
        text=ai_text,
        speaker_wav=[
            "voice_samples/sample1.wav",
            "voice_samples/sample2.wav",
            "voice_samples/sample3.wav",
            "voice_samples/sample4.wav"
        ],
        language="en",
        file_path="ai_response.wav"
    )

    # Auto-play audio
    os.system("ffplay -autoexit -nodisp ai_response.wav")

    print("🔊 Response played.\n")


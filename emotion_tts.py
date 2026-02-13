import pyttsx3
import os

def detect_emotion(text):
    text = text.lower()

    happy_words = ["happy", "great", "awesome", "love", "excited"]
    sad_words = ["sad", "upset", "lonely", "depressed", "cry"]

    if any(word in text for word in happy_words):
        return "happy"
    elif any(word in text for word in sad_words):
        return "sad"
    else:
        return "neutral"

def emotion_based_tts(text, filename="output/emotion_voice.wav"):
    engine = pyttsx3.init()
    emotion = detect_emotion(text)

    # Emotion tuning
    if emotion == "happy":
        engine.setProperty('rate', 190)
        engine.setProperty('volume', 1.0)
    elif emotion == "sad":
        engine.setProperty('rate', 130)
        engine.setProperty('volume', 0.7)
    else:
        engine.setProperty('rate', 160)
        engine.setProperty('volume', 0.9)

    os.makedirs("output", exist_ok=True)

    engine.save_to_file(text, filename)
    engine.runAndWait()

    print(f"Detected emotion: {emotion}")
    return filename

import pyttsx3
import os

def text_to_speech(text, filename="output/message.wav"):
    engine = pyttsx3.init()

    # Voice settings
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)  # change index for different voices
    engine.setProperty('rate', 170)             # speech speed
    engine.setProperty('volume', 1.0)           # volume

    # Ensure output folder exists
    os.makedirs("output", exist_ok=True)

    engine.save_to_file(text, filename)
    engine.runAndWait()

    return filename

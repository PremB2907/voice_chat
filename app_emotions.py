from emotion_tts import emotion_based_tts
import os

text = input("Enter your message: ")
audio = emotion_based_tts(text)

os.system(f"start {audio}")

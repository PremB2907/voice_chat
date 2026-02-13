from tts_engine import text_to_speech
import os
import platform

def play_audio(file_path):
    system = platform.system()

    if system == "Windows":
        os.system(f'start {file_path}')
    elif system == "Darwin":  # macOS
        os.system(f'afplay {file_path}')
    else:  # Linux
        os.system(f'aplay {file_path}')

def main():
    print("🎙️ Voice Chat – Text to Speech")
    print("--------------------------------")

    text = input("Enter your message: ")

    if not text.strip():
        print("❌ Empty message!")
        return

    audio_file = text_to_speech(text)
    print("✅ Voice message generated!")

    play_audio(audio_file)

if __name__ == "__main__":
    main()

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from TTS.api import TTS
import subprocess
import os
import uuid

app = Flask(__name__)
CORS(app)

print("🔊 Loading Prem's Voice Model...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

USER_NAME = "Maitree"

VOICE_SAMPLES = [
    "voice_samples/sample1.wav",
    "voice_samples/sample2.wav",
    "voice_samples/sample3.wav",
    "voice_samples/sample4.wav"
]

@app.route("/")
def home():
    return "UN-MISS AI Backend Running"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    user_input = data["message"].strip()

    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    system_prompt = """
You are Prem.
You are speaking to Maitree, someone deeply close to you.
Always respond in English only.
Never use Spanish or any other language.
Speak in first person.
Keep the response to ONE short emotional sentence.
Do not explain anything.
Do not switch roles.
Do not include Maitree’s dialogue.
Only reply as Prem.
"""


    full_prompt = system_prompt + "\nMaitree says: " + user_input + "\nPrem:"


    result = subprocess.run(
        ["ollama", "run", "phi", full_prompt],
        capture_output=True,
        text=True
    )

    prem_reply = result.stdout.strip()

    if not prem_reply:
        prem_reply = "Maitree… I'm here."

    filename = f"response_{uuid.uuid4().hex}.wav"

    tts.tts_to_file(
        text=prem_reply,
        speaker_wav=VOICE_SAMPLES,
        language="en",
        file_path=filename
    )

    return jsonify({
        "reply": prem_reply,
        "audio": filename
    })


@app.route("/audio/<filename>")
def audio(filename):
    if os.path.exists(filename):
        return send_file(filename, mimetype="audio/wav")
    return "Audio not found", 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


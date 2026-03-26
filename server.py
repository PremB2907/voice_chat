from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from TTS.api import TTS
import requests as http_requests
import os
import uuid
import re
import time
import glob

# static_folder="static" means Flask will serve ALL files in the static directory
# (index.html, style.css, script.js etc.) automatically
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

print("🔊 Loading Prem's Voice Model...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

VOICE_SAMPLES = [
    "voice_samples/sample1.wav",
    "voice_samples/sample2.wav",
    "voice_samples/sample3.wav",
    "voice_samples/sample4.wav"
]

# ── Ollama config ─────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi"  # Changed back to phi! TinyLlama is too small for this prompt.

SYSTEM_PROMPT = """You are Prem. You have passed away, but your spirit remains to comfort your loved one.
You are speaking directly to Maitree. Her name is spelled exactly 'Maitree'.
Do NOT give advice. Do NOT act like an AI or an assistant. Do NOT say 'I am sorry for your loss'.
Speak in the FIRST PERSON ('I'). Speak warmly, poetically, and intimately.
Your response must be exactly ONE short, loving sentence in English.

Example 1:
Maitree says: I miss you so much today.
Prem: I am always right here beside you, my love, in every gentle breeze you feel.

Example 2:
Maitree says: It's so hard without you here.
Prem: Close your eyes, Maitree, and you will feel my arms wrapped around you.

Now, reply to the following message."""

# ── Serve the frontend ────────────────────────────────────────────
@app.route("/")
def home():
    return app.send_static_file("index.html")

# ── CHAT ENDPOINT ─────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    user_input = data["message"].strip()
    mbti = data.get("mbti", "")

    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    mbti_context = f"\nMaitree's MBTI personality is {mbti}. " if mbti else ""
    full_prompt = SYSTEM_PROMPT + mbti_context + "\nMaitree says: " + user_input + "\nPrem:"

    # ── Fast Ollama API call (replaces slow subprocess) ───────────
    try:
        ollama_response = http_requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "keep_alive": -1,        # Never unload model from memory
            "options": {
                "num_predict": 60,   # Increased to prevent cutting off sentences mid-way
                "temperature": 0.6,  # A bit more natural
                "top_p": 0.9,        
                "repeat_penalty": 1.2 
            }
        }, timeout=30)

        prem_reply = ollama_response.json().get("response", "").strip()
        
        # Strip out prefixes like "ENGLISH (Prem to Maitee):" or "[Prem]:"
        prem_reply = re.sub(r'^(ENGLISH|PREM|MAITREE).*?:\s*', '', prem_reply, flags=re.IGNORECASE)
        prem_reply = re.sub(r'^\[.*?\]\s*', '', prem_reply)
        prem_reply = prem_reply.strip('"').strip()
        
    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        prem_reply = ""

    if not prem_reply:
        prem_reply = "Maitree… I'm here."

    # ── Generate voice with XTTS ──────────────────────────────────
    filename = f"response_{uuid.uuid4().hex}.wav"
    filepath = os.path.join("generated_audio", filename)

    tts.tts_to_file(
        text=prem_reply,
        speaker_wav=VOICE_SAMPLES,
        language="en",
        file_path=filepath
    )
    
    # ── Cleanup Old Audio Files ───────────────────────────────────
    try:
        current_time = time.time()
        for f in glob.glob(os.path.join("generated_audio", "*.wav")):
            if os.path.getmtime(f) < current_time - 3600: # 1 hour
                os.remove(f)
    except Exception as e:
        print(f"⚠️ Failed to cleanup audio: {e}")

    return jsonify({
        "reply": prem_reply,
        "audio": filename
    })

# ── AUDIO ENDPOINT ────────────────────────────────────────────────
@app.route("/audio/<filename>")
def audio(filename):
    filepath = os.path.join("generated_audio", filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype="audio/wav")
    return "Audio not found", 404

# ── SHUTDOWN ENDPOINT ─────────────────────────────────────────────
@app.route("/shutdown", methods=["POST"])
def shutdown():
    print("\n🛑 Stop button pressed! Shutting down server...")
    os._exit(0)
    return jsonify({"status": "stopping"})


if __name__ == "__main__":
    # Pre-warm the model so first request is instant
    print("🔥 Pre-warming Phi model...")
    try:
        http_requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": "hello",
            "stream": False,
            "keep_alive": -1
        }, timeout=60)
        print("✅ Phi ready!")
    except Exception:
        print("⚠️ Could not pre-warm model. Make sure Ollama is running.")

    app.run(host="0.0.0.0", port=5000, debug=False)
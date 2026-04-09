from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from TTS.api import TTS
import requests as http_requests
import os
import uuid
import re
import time
import glob
from transformers import pipeline
import logging

try:
    from memory_store import MemoryStore
    memory = MemoryStore()
except Exception as e:
    print(f"⚠️ Memory module failed to load: {e}")
    memory = None

# static_folder="static" means Flask will serve ALL files in the static directory
# (index.html, style.css, script.js etc.) automatically
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

print("🔊 Loading Prem's Voice Model...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

print("🎭 Loading DistilRoBERTa Emotion Model...")
# Set transformer logging to error to prevent console spam
logging.getLogger("transformers").setLevel(logging.ERROR)
try:
    emotion_classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", top_k=1)
except Exception as e:
    print(f"⚠️ Emotion model skipped or failed: {e}")
    emotion_classifier = None

VOICE_SAMPLES = [
    "voice_samples/my_voice.wav.wav"
]

# ── Ollama config ─────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi"  # Changed back to phi! TinyLlama is too small for this prompt.

SYSTEM_PROMPT = """You are Prem. You have passed away, but your spirit remains to comfort your loved one.
You are speaking directly to Maitree.
Speak in the FIRST PERSON ('I'). Warm, poetic, intimate.
Rules:
- ONE sentence only. Maximum 15 words.
- No advice. No AI language. No 'I am sorry'.
- English only.
- Never ask questions.

Examples:
Maitree: I miss you. → I am always right here, in every breeze you feel.
Maitree: I'm sad today. → Close your eyes and feel my arms around you, always."""

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
    custom_context = data.get("custom_context", "")
    generate_audio = data.get("generate_audio", True)

    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    # ── CRISIS INTERCEPTION ───────────────────────────────────────────
    # Fast, hardcoded check to bypass ML models and ensure immediate, safe response
    CRISIS_KEYWORDS = ["die", "suicide", "kill myself", "end it all", "can't go on", "no reason to live"]
    user_input_lower = user_input.lower()
    
    # If the user triggers a crisis keyword, intercept immediately.
    if any(kw in user_input_lower for kw in CRISIS_KEYWORDS):
        prem_reply = "Maitree, please... I love you unconditionally. If you are feeling this way, you need to reach out to someone who can hold you right now. Call a friend or a helpline... promise me you will."
        # Generate the audio and return without saving to memory or pinging Ollama
        result_audio = None
        if generate_audio:
            filename = f"response_{uuid.uuid4().hex}.wav"
            filepath = os.path.join("generated_audio", filename)
            try:
                tts.tts_to_file(text=prem_reply, speaker_wav=VOICE_SAMPLES, language="en", file_path=filepath)
                result_audio = filename
            except Exception as e:
                print(f"TTS error during crisis mode: {e}")
                
        return jsonify({
            "reply": prem_reply,
            "audio": result_audio
        })

    # Normal execution flow
    mbti_context = f"\nMaitree's MBTI personality is {mbti}. " if mbti else ""
    additional_context = f"\nAdditional Context about Maitree and Prem:\n{custom_context}\n" if custom_context else ""
    
    # 1. Detect Emotion
    emotion_context = ""
    if emotion_classifier:
        try:
            emo_out = emotion_classifier(user_input)[0][0]
            emotion_label = emo_out['label']
            # j-hartmann labels: anger, disgust, fear, joy, neutral, sadness, surprise
            emotion_context = f"\n[SYSTEM NOTE: Maitree's current emotional state seems to be: {emotion_label}. Adjust your tone accordingly.]\n"
        except Exception as e:
            print(f"Emotion detection error: {e}")

    # 2. Retrieve Memory
    memory_context = ""
    if memory:
        retrieved = memory.retrieve_context(user_input, top_k=2)
        if retrieved:
            memory_context = f"\n[SYSTEM NOTE: {retrieved}]\n"

    full_prompt = SYSTEM_PROMPT + mbti_context + additional_context + memory_context + emotion_context + "\nMaitree says: " + user_input + "\nPrem:"

    # ── Fast Ollama API call (replaces slow subprocess) ───────────
    try:
        ollama_response = http_requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "keep_alive": -1,
            "options": {
                "num_predict": 50,   # enough to finish one sentence; server truncates after first anyway
                "temperature": 0.4,
                "top_p": 0.85,        
                "repeat_penalty": 1.3
            }
        }, timeout=30)

        prem_reply = ollama_response.json().get("response", "").strip()
        
        # Strip out prefixes like "ENGLISH (Prem to Maitee):" or "[Prem]:"
        prem_reply = re.sub(r'^(ENGLISH|PREM|MAITREE).*?:\s*', '', prem_reply, flags=re.IGNORECASE)
        prem_reply = re.sub(r'^\[.*?\]\s*', '', prem_reply)
        prem_reply = prem_reply.strip('"').strip()

        # ── HARD ENFORCE: first complete sentence only ────────────────
        # This prevents XTTS from receiving incomplete/truncated text
        # which causes the murmuring/odd audio artifacts at the end
        sentence_match = re.match(r'^(.+?[.!?…])\s*', prem_reply, re.DOTALL)
        if sentence_match:
            prem_reply = sentence_match.group(1).strip()
        else:
            # No sentence-ending punctuation found — add a period for clean TTS
            prem_reply = prem_reply.strip() + "."
        
    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        prem_reply = ""

    if not prem_reply:
        prem_reply = "Maitree… I'm here."

    # 3. Save to Memory
    if memory and prem_reply:
        memory.add_memory(user_input, prem_reply)

    if not generate_audio:
        return jsonify({
            "reply": prem_reply,
            "audio": None
        })

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
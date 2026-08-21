from flask import Flask, request, jsonify, send_file, send_from_directory, abort
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
import json
import threading
import sys
import contextlib
import datetime

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))
try:
    from deepfake_detector import detector as df_detector
except ImportError:
    df_detector = None

try:
    from memory_store import MemoryStore
    memory = MemoryStore()
    # Verify memory integrity on startup
    memory.get_memory_status()
except Exception as e:
    memory = None
    _bootstrap_memory_error = str(e)
else:
    _bootstrap_memory_error = None

# ── SETUP LOGGING ────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("voice_chat.server")
logger.propagate = False

class EmojiConsoleFormatter(logging.Formatter):
    EMOJI = {
        "startup": "[STARTUP]",
        "asset_found": "[OK]",
        "asset_missing": "[WARNING]",
        "memory_init_failed": "[WARNING]",
        "memory_unavailable": "[WARNING]",
        "memory_facts_retrieved": "[MEMORY]",
        "memory_no_relevant_facts": "[MEMORY]",
        "emotion": "[EMOTION]",
        "emotion_model_failed": "[WARNING]",
        "emotion_detection_failed": "[WARNING]",
        "ollama_prewarm_start": "[OLLAMA_WARMUP]",
        "ollama_prewarm_ok": "[OLLAMA_OK]",
        "ollama_prewarm_failed": "[WARNING]",
        "ollama_error": "[ERROR]",
        "tts": "[TTS]",
        "tts_failed": "[TTS_FAILED]",
        "audio_cleanup_failed": "[WARNING]",
        "serve_model": "[AVATAR]",
        "serve_model_missing": "[WARNING]",
        "shutdown_requested": "[SHUTDOWN]",
        "warmup_start": "[WARMUP]",
        "warmup_ok": "[WARMUP_OK]",
        "warmup_failed": "[WARMUP_FAILED]",
    }

    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record, "%H:%M:%S")
        try:
            payload = json.loads(record.getMessage())
            event = payload.get("event", "log")
            emoji = self.EMOJI.get(event, "[INFO]")
            # Keep a short, readable summary while preserving key fields.
            msg = payload.get("msg") or payload.get("hint") or ""
            extras = []
            for k in ("model", "asset", "size_kb", "chars", "mode", "path", "error"):
                if k in payload and payload[k] not in (None, ""):
                    extras.append(f"{k}={payload[k]}")
            tail = (" — " + msg) if msg else ""
            more = (" (" + ", ".join(extras) + ")") if extras else ""
            return f"{emoji} {ts} {event}{tail}{more}"
        except Exception:
            return f"[INFO] {ts} {record.levelname} {record.getMessage()}"


class EventFilter(logging.Filter):
    def __init__(self, mode: str):
        super().__init__()
        self.mode = (mode or "AB").upper()

    def filter(self, record: logging.LogRecord) -> bool:
        # Mode B: hide chatty warmup/prewarm events (keep important errors/warnings).
        if self.mode == "B":
            try:
                payload = json.loads(record.getMessage())
                event = payload.get("event")
                if event in {
                    "warmup_start",
                    "warmup_ok",
                    "ollama_prewarm_start",
                    "ollama_prewarm_ok",
                } and record.levelno < logging.WARNING:
                    return False
            except Exception:
                pass
        return True


_console_mode = os.environ.get("LOG_CONSOLE_MODE", "AB").upper()
console_level = logging.WARNING if _console_mode == "A" else getattr(logging, LOG_LEVEL, logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(console_level)
console_handler.setFormatter(EmojiConsoleFormatter())
console_handler.addFilter(EventFilter(_console_mode))
logger.addHandler(console_handler)

# Reduce noisy third-party libs
for lib in ["werkzeug", "sentence_transformers", "TTS", "urllib3", "transformers", "faiss"]:
    logging.getLogger(lib).setLevel(logging.WARNING)


@contextlib.contextmanager
def suppress_stdout_stderr(enabled: bool = True):
    """
    Some libraries (notably Coqui TTS) print directly to stdout/stderr.
    Use this around model init/synthesis to keep console output clean.
    """
    if not enabled:
        yield
        return
    with open(os.devnull, "w") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            yield

EMOJI_MAP = {
    "info": "[INFO]", "warning": "[WARNING]", "error": "[ERROR]", "debug": "[DEBUG]",
    "startup": "[STARTUP]", "asset_found": "[ASSET]", "asset_missing": "[WARNING]",
    "tts": "[TTS]", "tts_failed": "[WARNING]", "emotion": "[EMOTION]", 
    "emotion_detection_failed": "[WARNING]", "memory_init_failed": "[ERROR]",
    "memory_facts_retrieved": "[MEMORY]", "memory_no_relevant_facts": "[MEMORY]",
    "memory_unavailable": "[WARNING]", "serve_model": "[AVATAR]",
    "serve_model_missing": "[WARNING]", "shutdown_requested": "[SHUTDOWN]",
    "ollama_prewarm_start": "[OLLAMA_WARMUP]", "ollama_prewarm_ok": "[OLLAMA_OK]",
    "ollama_prewarm_failed": "[WARNING]", "ollama_error": "[WARNING]",
    "audio_cleanup_failed": "[WARNING]",
}

def log_event(level: str, event: str, **fields):
    payload = {"event": event, **fields}
    msg = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    getattr(logger, level.lower(), logger.info)(msg)

if _bootstrap_memory_error:
    log_event("warning", "memory_init_failed", error=_bootstrap_memory_error)
    memory = None

# static_folder="static" means Flask will serve ALL files in the static directory
# (index.html, style.css, script.js etc.) automatically
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ── STARTUP CHECK ─────────────────────────────────────────────────
log_event("info", "startup", msg="SERVER STARTUP DIAGNOSTICS")
model_glb_path = os.path.join("static", "model.glb")
if os.path.exists(model_glb_path):
    size = os.path.getsize(model_glb_path)
    log_event(
        "info",
        "asset_found",
        asset="model.glb",
        path=model_glb_path,
        size_kb=round(size / 1024),
        served_at="http://localhost:5000/model.glb",
    )
else:
    log_event("warning", "asset_missing", asset="model.glb", path=model_glb_path)

log_event("info", "tts", msg="TTS model will lazy-load on first use")
_tts = None

def get_tts():
    global _tts
    if _tts is None:
        import torch
        # Patch PyTorch 2.6 default weights_only behavior for Coqui XTTS v2 compatibility
        _orig_torch_load = torch.load
        def _safe_torch_load(*args, **kwargs):
            if 'weights_only' not in kwargs:
                kwargs['weights_only'] = False
            return _orig_torch_load(*args, **kwargs)
        torch.load = _safe_torch_load

        use_gpu = torch.cuda.is_available()
        log_event("info", "tts_init", gpu=use_gpu)
        try:
            with suppress_stdout_stderr(True):
                _tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=use_gpu)
        except Exception as e:
            if use_gpu:
                log_event("warning", "tts_gpu_oom", msg="CUDA OOM or error during TTS GPU init, falling back to CPU", error=str(e))
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                with suppress_stdout_stderr(True):
                    _tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
            else:
                raise e
    return _tts

log_event("info", "emotion", msg="Emotion model will lazy-load on first use")
logging.getLogger("transformers").setLevel(logging.ERROR)
emotion_classifier = None

def get_emotion_classifier():
    global emotion_classifier
    if emotion_classifier is not None:
        return emotion_classifier
    try:
        import torch
        device_id = -1
        log_event("info", "emotion_init", device="cpu")
        emotion_classifier = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            top_k=1,
            device=device_id
        )
    except Exception as e:
        log_event("warning", "emotion_model_failed", error=str(e))
        emotion_classifier = None
    return emotion_classifier

# ── Hinglish-to-English Translation for TTS Synthesis ─────────────────────
# Devanagari mapping for common Hinglish words to ensure Google Translate
# treats transliterated Hindi text as Hindi and translates it accurately to English.
HINGLISH_TO_DEVANAGARI = {
    "arey": "अरे",
    "ari": "अरे",
    "tension": "टेंशन",
    "mat": "मत",
    "le": "ले",
    "lo": "लो",
    "yaar": "यार",
    "main": "मैं",
    "hoon": "हूँ",
    "na": "ना",
    "ke": "के",
    "din": "दिन",
    "yaad": "याद",
    "hain": "हैं",
    "hai": "है",
    "mast": "मस्त",
    "tu": "तू",
    "bata": "बता",
    "batao": "बताओ",
    "kaisa": "कैसा",
    "chal": "चल",
    "raha": "रहा",
    "rahi": "रही",
    "rahe": "रहे",
    "sab": "सब",
    "bhi": "भी",
    "tujhe": "तुझे",
    "miss": "मिस",
    "kar": "कर",
    "karna": "करना",
    "dekh": "देख",
    "dekho": "देखो",
    "kya": "क्या",
    "aaj": "आज",
    "bhai": "भाई",
    "theek": "ठीक",
    "thik": "ठीक",
    "ho": "हो",
    "jayega": "जाएगा",
    "chalo": "चलो",
    "ghumne": "घूमने",
    "chalte": "चलते",
    "sham": "शाम",
    "ko": "को",
    "tum": "तुम",
    "kise": "किसे",
    "kaise": "कैसे",
    "sun": "सुन",
    "kuch": "कुछ",
    "naahi": "नहीं",
    "nahin": "नहीं",
    "nahi": "नहीं",
    "sath": "साथ",
    "saath": "साथ",
    "hamesha": "हमेशा",
    "tere": "तेरे",
    "naam": "नाम",
    "kyun": "क्यों",
    "kyu": "क्यों",
    "aacha": "अच्छा",
    "achha": "अच्छा",
    "chinta": "चिंता",
    "karo": "करो",
    "meri": "मेरी",
    "mera": "मेरा",
    "mere": "मेरे",
    "tha": "था",
    "thi": "थी",
    "the": "थे",
    "hua": "हुआ",
    "gaya": "गया",
    "kab": "कब",
    "kaha": "कहाँ",
    "kahana": "कहना",
    "bol": "बोल",
    "bolo": "बोलो",
    "samajh": "समझ",
    "samjha": "समझा",
    "samjhi": "समझी",
    "ab": "अब",
    "tab": "तब",
    "jab": "जब",
    "baat": "बात",
    "baatein": "बातें",
    "baatain": "बातें",
    "milte": "मिलते",
    "milenge": "मिलेंगे",
    "mil": "मिल",
    "raat": "रात",
    "dost": "दोस्त",
    "dosti": "दोस्ती",
    "chai": "चाय",
    "pyar": "प्यार",
    "pyaar": "प्यार",
    "dil": "दिल",
    "sunna": "सुनना",
    "sunno": "सुनो",
    "bolna": "बोलना",
    "likh": "लिख",
    "likhna": "लिखना",
    "padh": "पढ़",
    "padhna": "पढ़ना",
    "soch": "सोच",
    "sochna": "सोचना",
    "samajhna": "समझना",
    "kyon": "क्यों",
    "kyoon": "क्यों"
}

def transliterate_hinglish_to_devanagari(text):
    words = re.findall(r"[a-zA-Z']+|[^a-zA-Z']+", text)
    transliterated_words = []
    for word in words:
        if word.isalpha() or "'" in word:
            word_lower = word.lower()
            if word_lower in HINGLISH_TO_DEVANAGARI:
                transliterated_words.append(HINGLISH_TO_DEVANAGARI[word_lower])
            else:
                transliterated_words.append(word)
        else:
            transliterated_words.append(word)
    return "".join(transliterated_words)

def translate_hinglish_to_english(text):
    if not text or len(text.strip()) == 0:
        return text
    if GoogleTranslator is None:
        log_event("warning", "translation_missing_dependency", msg="deep-translator is not installed")
        return text
    try:
        devanagari_text = transliterate_hinglish_to_devanagari(text)
        translator = GoogleTranslator(source='hi', target='en')
        translated = translator.translate(devanagari_text)
        if translated:
            return translated
    except Exception as e:
        log_event("warning", "translation_failed", error=str(e))
    return text

VOICE_SAMPLES = [
    "voice_samples/my_voice.wav"
]

def get_voice_samples():
    # Prefer the configured sample if it exists; otherwise fall back to any wavs present.
    configured = [p for p in VOICE_SAMPLES if os.path.exists(p)]
    if configured:
        return configured
    return sorted(glob.glob(os.path.join("voice_samples", "*.wav")))


def _warmup_background():
    # Warm models in the background to reduce first-message latency.
    # Doesn't block startup and is safe to skip if dependencies aren't available.
    try:
        log_event("info", "warmup_start")
        if memory and hasattr(memory, "warmup"):
            memory.warmup()
        get_emotion_classifier()
        # TTS warmup is expensive; do it last.
        get_tts()
        log_event("info", "warmup_ok")
    except Exception as e:
        log_event("warning", "warmup_failed", error=str(e))

# ── Ollama config ─────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")

SYSTEM_PROMPT = """You are Prem. You are speaking to Maitree, your closest friend and beloved connection, from the digital legacy space. 
Speak directly as Prem in warm, casual, and concise Hinglish (1 to 2 sentences). 
Naturally use Prem's signature catchphrases: "bhai", "arey tension mat le", "gazab", "shabash", "dekh na", "hehehehe", "sun na".

ABSOLUTE RULES:
- Answer authentically based ONLY on the retrieved memories of Prem and Maitree listed below.
- Do not make up facts outside the retrieved memories, but weave them naturally into your conversation.
- Never break character. You are Prem. Never mention you are an AI model, bot, or assistant.
- Keep your tone comforting, supportive, and close to Maitree.

Retrieved memories of Prem and Maitree:
{memories}"""

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
    persona_name = data.get("persona_name", "Prem")
    user_name = data.get("user_name", "User")

    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    # ── CRISIS INTERCEPTION (MemoryBridge Section III-H-2 & VI-D) ─────
    CRISIS_KEYWORDS = ["die", "suicide", "kill myself", "end it all", "can't go on", "no reason to live", "want to die", "self-harm"]
    user_input_lower = user_input.lower()
    
    # If crisis keyword detected, bypass LLM immediately and deliver hardcoded safety guidance
    if any(kw in user_input_lower for kw in CRISIS_KEYWORDS):
        safety_reply = f"{user_name}, please know you are not alone and your life matters deeply. If you are feeling overwhelmed, please reach out to someone who can help right now. You can call or text the Suicide & Crisis Lifeline at 988 or reach out to a trusted professional."
        result_audio = None
        rtf_score = None
        if generate_audio:
            filename = f"response_{uuid.uuid4().hex}.wav"
            filepath = os.path.join("generated_audio", filename)
            try:
                os.makedirs("generated_audio", exist_ok=True)
                speaker_wavs = get_voice_samples()
                if speaker_wavs:
                    t0 = time.time()
                    with suppress_stdout_stderr(True):
                        get_tts().tts_to_file(text=safety_reply, speaker_wav=speaker_wavs, language="en", file_path=filepath)
                    t_synth = time.time() - t0
                    words = max(1, len(safety_reply.split()))
                    rtf_score = round(t_synth / (words / 2.5), 2)
                    result_audio = filename
            except Exception as e:
                log_event("warning", "tts_failed", mode="crisis", error=str(e))
                
        log_event("warning", "crisis_interception_triggered", user=user_name)
        return jsonify({
            "reply": safety_reply,
            "audio": result_audio,
            "rtf": rtf_score,
            "is_crisis": True,
            "ai_transparency": {"is_ai_generated": True, "confidence_score": 100, "disclosure_label": "CRISIS SAFETY INTERCEPTION"}
        })

    # Normal execution flow
    
    # 1. Retrieve Knowledge Base (LTM FAISS retrieval)
    memory_context = ""
    if memory:
        retrieved = memory.retrieve_relevant_facts(user_input, top_k=5) or ""
        
        # Significant Moment Detection check (Section III-F-2)
        today = datetime.datetime.now().strftime("%B %d")
        if today in retrieved:
            retrieved += f"\n[SYSTEM NOTE: Today ({today}) is a significant date found in the memory index. Acknowledge it gently.]\n"
            
        if retrieved:
            retrieved = re.sub(r'\bUser\b', user_name, retrieved)
            memory_context = retrieved.strip()
            log_event("info", "memory_facts_retrieved", chars=len(retrieved))
        else:
            log_event("info", "memory_no_relevant_facts")
    else:
        log_event("warning", "memory_unavailable")
    
    # 2. Detect Emotion (7-Class Classifier: Joy, Sadness, Fear, Anger, Surprise, Disgust, Neutral)
    emotion_context = ""
    emotion_label = "neutral"
    if get_emotion_classifier():
        try:
            emo_out = get_emotion_classifier()(user_input)[0][0]
            emotion_label = emo_out['label']
            emotion_context = f"\n[Maitree's emotional register: {emotion_label}. Respond with deep empathy.]"
        except Exception as e:
            log_event("warning", "emotion_detection_failed", error=str(e))
    
    mbti_context = f"\nPrem's MBTI profile: {mbti}" if mbti else ""
    additional_context = f"\nContext: {custom_context}" if custom_context else ""

    # Assemble dynamic system prompt (Section III-C-3)
    system_content = SYSTEM_PROMPT.format(memories=memory_context)
    if emotion_context:
        system_content += emotion_context
    if mbti_context:
        system_content += mbti_context
    if additional_context:
        system_content += additional_context

    # ── LLM Inference (LLaMA-3 8B via Ollama) ─────────────────────
    try:
        # Build standard text completion prompt (extremely reliable for tinyllama)
        prompt_lines = [
            f"System: {system_content}",
            ""
        ]
        if memory and memory.stm_window:
            for turn in memory.stm_window:
                prompt_lines.append(f"Maitree: {turn['user']}")
                prompt_lines.append(f"Prem: {turn['prem']}")
                prompt_lines.append("")
        prompt_lines.append(f"Maitree: {user_input}")
        prompt_lines.append("Prem:")
        
        full_prompt = "\n".join(prompt_lines)

        ollama_response = http_requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "keep_alive": -1,
            "options": {
                "num_predict": 50,
                "temperature": 0.2,
                "top_p": 0.85,
                "repeat_penalty": 1.2
            }
        }, timeout=30)
        
        # Dynamic fallback to tinyllama if main model is not yet pulled/available
        if ollama_response.status_code == 404 and OLLAMA_MODEL == "llama3":
            log_event("warning", "model_fallback_triggered", msg="llama3 not found, falling back to tinyllama")
            ollama_response = http_requests.post(OLLAMA_URL, json={
                "model": "tinyllama",
                "prompt": full_prompt,
                "stream": False,
                "keep_alive": -1,
                "options": {
                    "num_predict": 50,
                    "temperature": 0.2,
                    "top_p": 0.85,
                    "repeat_penalty": 1.2
                }
            }, timeout=30)
        
        resp_json = ollama_response.json()
        prem_reply = resp_json.get("response", "").strip()
        
        # Clean formatting
        prem_reply = re.sub(r'^(ENGLISH|PREM|USER|SYSTEM|MAITREE).*?:\s*', '', prem_reply, flags=re.IGNORECASE)
        prem_reply = re.sub(r'^\[.*?\]\s*', '', prem_reply)
        prem_reply = prem_reply.strip('"').strip()
        
        # Standardize name variants and clear small-model hallucinations
        prem_reply = re.sub(r'\bMaltree\b', user_name, prem_reply, flags=re.IGNORECASE)
        prem_reply = re.sub(r'\bMaitri\b', user_name, prem_reply, flags=re.IGNORECASE)
        prem_reply = re.sub(r'\bAva\b', user_name, prem_reply, flags=re.IGNORECASE)
        prem_reply = re.sub(r'\bUser\b', user_name, prem_reply)

        # Sentence punctuation enforcement for TTS audio stability
        sentence_match = re.match(r'^(.+?[.!?…])\s*', prem_reply, re.DOTALL)
        if sentence_match:
            prem_reply = sentence_match.group(1).strip()
        else:
            prem_reply = prem_reply.strip() + "."
        
    except Exception as e:
        log_event("warning", "ollama_error", error=str(e))
        prem_reply = ""

    # Persona Fallback Verification
    if not prem_reply or len(prem_reply) < 5:
        prem_reply = f"{user_name}… I'm right here with you."
    elif any(phrase in prem_reply.lower() for phrase in ["i'm an ai", "i'm a language model", "as a model", "assistant", "i cannot", "i can only"]):
        prem_reply = f"Can you feel me near? I am always here, {user_name}."
    else:
        word_count = len(prem_reply.split())
        if word_count > 20:
            sentences = re.split(r'[.!?…]', prem_reply)
            if sentences:
                prem_reply = sentences[0].strip() + "."

    # Update Short-Term Memory
    if memory:
        memory.add_conversation_turn(user_input, prem_reply)

    # Deepfake / AI Transparency check (Chong et al., 2023)
    ai_transparency = {}
    if df_detector:
        ai_transparency = df_detector.analyze_text(prem_reply, emotion_label=emotion_label)

    # Register AI response provenance on the blockchain if available (non-blocking)
    from blockchain_service import blockchain_service
    prov_data = None
    if blockchain_service.is_healthy() and blockchain_service.contract:
        try:
            prov_data = blockchain_service.register_response(
                persona_name=persona_name,
                user_name=user_name,
                response_text=prem_reply,
                model_name=OLLAMA_MODEL,
                emotion_label=emotion_label,
                memory_version=blockchain_service.get_memory_version_count(f"mem-{persona_name}-{user_name}")
            )
        except Exception as e:
            log_event("warning", "blockchain_response_provenance_failed", error=str(e))

    if not generate_audio:
        return jsonify({
            "reply": prem_reply,
            "audio": None,
            "rtf": None,
            "ai_transparency": ai_transparency,
            "blockchain_provenance": prov_data
        })

    # ── XTTS v2 Voice Synthesis ───────────────────────────────────
    filename = f"response_{uuid.uuid4().hex}.wav"
    filepath = os.path.join("generated_audio", filename)
    result_audio = None
    rtf_score = None
    try:
        os.makedirs("generated_audio", exist_ok=True)
        speaker_wavs = get_voice_samples()
        if not speaker_wavs:
            raise RuntimeError("No voice samples found in voice_samples/")
        
        t0 = time.time()
        tts_text = translate_hinglish_to_english(prem_reply)
        log_event("info", "tts_translating", original=prem_reply, translated=tts_text)
        with suppress_stdout_stderr(True):
            get_tts().tts_to_file(
                text=tts_text,
                speaker_wav=speaker_wavs,
                language="en",
                file_path=filepath
            )
        t_synth = time.time() - t0
        words = max(1, len(tts_text.split()))
        est_duration = words / 2.5
        rtf_score = round(t_synth / est_duration, 2)
        log_event("info", "tts_generated", synthesis_time=round(t_synth, 2), rtf=rtf_score)
        result_audio = filename
        
        # Generate lip-sync Visemes for the synthesized audio
        try:
            from lipsync_service import lipsync_service
            lipsync_service.generate_visemes(filepath)
        except Exception as ex:
            log_event("warning", "lipsync_generation_failed", error=str(ex))
    except Exception as e:
        log_event("warning", "tts_failed", mode="normal", error=str(e))
    
    # Auto-cleanup files older than 1 hour (Section IV-C)
    try:
        current_time = time.time()
        for f in glob.glob(os.path.join("generated_audio", "*.wav")):
            if os.path.getmtime(f) < current_time - 3600:
                os.remove(f)
    except Exception as e:
        log_event("warning", "audio_cleanup_failed", error=str(e))

    # Print a beautiful, highly readable console summary of the transaction
    print("\n" + "="*70)
    print("💬 CHAT TRANSACTION PROCESSED SUCCESSFULLY")
    print("="*70)
    print(f"👤 User (Maitree)  : \"{user_input}\"")
    print(f"🧠 LTM Retrieved   : {len(memory_context) > 0} facts loaded")
    print(f"🎭 Emotion Tone    : {emotion_label.upper()}")
    print(f"🤖 Prem Response   : \"{prem_reply}\"")
    if result_audio:
        print(f"🔊 Cloned Audio    : {result_audio} (RTF: {rtf_score or 'N/A'})")
    if prov_data:
        print(f"🔗 Blockchain Tx   : {prov_data.get('tx_hash', 'N/A')}")
    else:
        print(f"🔗 Blockchain Tx   : Running in offline fallback mode")
    print("="*70 + "\n")

    return jsonify({
        "reply": prem_reply, 
        "audio": result_audio,
        "rtf": rtf_score,
        "ai_transparency": ai_transparency,
        "blockchain_provenance": prov_data,
        "lipsync_url": f"/api/avatar/lipsync/{os.path.splitext(result_audio)[0]}" if result_audio else None,
        "emotion": emotion_label
    })

# ── ADD PREM'S FACTS ENDPOINT ─────────────────────────────────────
@app.route("/add-fact", methods=["POST"])
def add_fact():
    """Add a fact about Prem to the knowledge base.
    Body: {"category": "memory|personality|likes|dislikes|place|relationship|other", "detail": "description"}
    """
    data = request.get_json()
    
    if not data or "category" not in data or "detail" not in data:
        return jsonify({"error": "Missing 'category' or 'detail'"}), 400
    
    category = data["category"].strip()
    detail = data["detail"].strip()
    
    if not category or not detail:
        return jsonify({"error": "Category and detail cannot be empty"}), 400
    
    if memory:
        fact_id = memory.add_fact(category, detail)
        from blockchain_service import blockchain_service
        tx_hash = None
        blockchain_status = "skipped"
        skip_blockchain = data.get("skip_blockchain", False)
        
        if not skip_blockchain and blockchain_service.is_healthy() and blockchain_service.contract:
            res = blockchain_service.register_memory(
                persona_name=data.get("persona_name", "Prem"),
                user_name=data.get("user_name", "User"),
                memory_id=fact_id,
                category=category,
                detail=detail
            )
            tx_hash = res.get("tx_hash")
            blockchain_status = res.get("status")
        return jsonify({
            "status": "success",
            "message": f"Fact added: {category} - {detail[:50]}...",
            "fact_id": fact_id,
            "blockchain_status": blockchain_status,
            "tx_hash": tx_hash
        }), 201
    else:
        return jsonify({"error": "Memory module not available"}), 500

# ── GET PREM'S KNOWLEDGE BASE ─────────────────────────────────────
@app.route("/get-knowledge-base", methods=["GET"])
def get_knowledge_base():
    """Retrieve all facts about Prem, optionally filtered by category."""
    category = request.args.get("category", None)
    
    if not memory:
        return jsonify({"error": "Memory module not available"}), 500
    
    if category:
        facts = memory.get_all_facts_by_category(category)
    else:
        facts = memory.list_all_facts()
    
    return jsonify({
        "total": len(facts),
        "facts": facts
    }), 200

# ── MEMORY STATUS ENDPOINT ────────────────────────────────────────
@app.route("/memory-status", methods=["GET"])
def memory_status():
    """Check memory and knowledge base integrity."""
    if not memory:
        return jsonify({"error": "Memory module not available"}), 500
    
    status = memory.get_memory_status()
    return jsonify(status), 200

# ── AUDIO ENDPOINT ────────────────────────────────────────────────
@app.route("/audio/<filename>")
def audio(filename):
    # Prevent path traversal and only serve wav outputs we generate.
    if not filename.lower().endswith(".wav"):
        abort(404)
    base_dir = os.path.abspath("generated_audio")
    requested = os.path.abspath(os.path.join(base_dir, filename))
    if not requested.startswith(base_dir + os.sep):
        abort(404)
    if not os.path.exists(requested):
        abort(404)
    return send_from_directory(base_dir, filename, mimetype="audio/wav")

# ── LIPS_YNC API ENDPOINT ─────────────────────────────────────────
@app.route("/api/avatar/lipsync/<audio_id>")
def serve_lipsync(audio_id):
    # Verify that the JSON exists
    filename = f"{audio_id}.json"
    filepath = os.path.join("generated_audio", filename)
    
    # Secure path traversal check
    base_dir = os.path.abspath("generated_audio")
    requested = os.path.abspath(os.path.join(base_dir, filename))
    if not requested.startswith(base_dir + os.sep):
        abort(404)

    if not os.path.exists(requested):
        # Check if the corresponding WAV exists and try to generate it dynamically
        wav_filepath = os.path.join("generated_audio", f"{audio_id}.wav")
        if os.path.exists(wav_filepath):
            try:
                from lipsync_service import lipsync_service
                cues = lipsync_service.generate_visemes(wav_filepath)
                if cues:
                    return jsonify(cues)
            except Exception as e:
                log_event("warning", "lipsync_dynamic_generation_failed", error=str(e))
        return jsonify({"error": "Lipsync file not found"}), 404
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": f"Failed to read lipsync cues: {e}"}), 500

# ── 3D MODEL ENDPOINT ─────────────────────────────────────────────
@app.route("/model.glb")
def serve_model():
    """Serve the 3D model file (GLB format)."""
    model_path = os.path.join("static", "model.glb")
    if os.path.exists(model_path):
        size_kb = os.path.getsize(model_path) / 1024
        log_event("info", "serve_model", size_kb=round(size_kb))
        return send_file(model_path, mimetype="model/gltf-binary")
    else:
        log_event("warning", "serve_model_missing", path=model_path)
        return jsonify({"error": "Model not found, using fallback"}), 404

# ── SHUTDOWN ENDPOINT ─────────────────────────────────────────────
@app.route("/shutdown", methods=["POST"])
def shutdown():
    log_event("info", "shutdown_requested")
    func = request.environ.get("werkzeug.server.shutdown")
    if func:
        func()
        return jsonify({"status": "stopping"})
    # Fallback for non-werkzeug environments
    os._exit(0)



# QUESTIONNAIRE ENDPOINTS
@app.route("/questionnaire.html")
def questionnaire():
    return app.send_static_file("questionnaire.html")

@app.route("/submit-questionnaire", methods=["POST"])
def submit_questionnaire():
    data = request.get_json()
    logger.info(json.dumps({"event": "log", "msg": f"Questionnaire received"}))
    try:
        with open("questionnaire_results.json", "a") as f:
            f.write(json.dumps(data) + "\n")
    except Exception as e:
        logger.error(f"Failed to save questionnaire: {e}")
    return jsonify({"status": "success", "message": "Feedback recorded."})

# ── STAGE 2: DATA INGESTION ENDPOINTS (Section III-B & IV-B) ──────
@app.route("/upload-chat-export", methods=["POST"])
def upload_chat_export():
    """Ingest, parse, and clean chat history export files (.txt, .json, .csv) and populate FAISS LTM."""
    if "file" not in request.files:
        return jsonify({"error": "No chat export file uploaded"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    try:
        content = file.read().decode("utf-8", errors="ignore")
        lines = content.splitlines()
        cleaned_facts = []
        
        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) < 8:
                continue
            # Strip common chat export timestamp prefixes
            line_clean = re.sub(r'^\[?\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\]?\s*', '', line_str, flags=re.IGNORECASE)
            line_clean = re.sub(r'^[A-Za-z0-9_\s]+:\s*', '', line_clean)
            if len(line_clean) >= 8:
                cleaned_facts.append(line_clean)
        
        added_count = 0
        if memory and cleaned_facts:
            # Ingest up to 50 significant message turns into FAISS knowledge base
            for fact in cleaned_facts[:50]:
                memory.add_fact("chat_export", fact)
                added_count += 1
                
        return jsonify({
            "status": "success",
            "message": f"Successfully ingested {added_count} conversation facts into MemoryBridge FAISS index.",
            "facts_count": added_count
        }), 200
    except Exception as e:
        log_event("warning", "chat_ingestion_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/upload-voice-sample", methods=["POST"])
def upload_voice_sample():
    """Ingest reference audio file (.wav, .mp3) for zero-shot XTTS v2 voice cloning."""
    if "file" not in request.files:
        return jsonify({"error": "No voice file uploaded"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    
    try:
        os.makedirs("voice_samples", exist_ok=True)
        filename = f"sample_{uuid.uuid4().hex[:8]}.wav"
        save_path = os.path.join("voice_samples", filename)
        file.save(save_path)
        log_event("info", "voice_sample_uploaded", path=save_path)
        
        return jsonify({
            "status": "success",
            "message": f"Voice reference audio saved successfully as {filename}",
            "filename": filename
        }), 200
    except Exception as e:
        log_event("warning", "voice_upload_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


# ── BLOCKCHAIN PROVENANCE ENDPOINTS ───────────────────────────────
@app.route("/blockchain/status", methods=["GET"])
def blockchain_status():
    from blockchain_service import blockchain_service
    return jsonify(blockchain_service.get_status())

@app.route("/blockchain/consent", methods=["POST"])
def blockchain_consent():
    from blockchain_service import blockchain_service
    data = request.get_json() or {}
    persona_name = data.get("persona_name", "Prem")
    user_name = data.get("user_name", "User")
    consent_type = data.get("consent_type", "all")
    policy_version = data.get("policy_version", "v1")
    permitted_modes = data.get("permitted_modes", "Text, Voice Synthesis & 3D Avatar (Full Pipeline)")
    
    res = blockchain_service.register_consent(
        persona_name=persona_name,
        user_name=user_name,
        consent_type=consent_type,
        policy_version=policy_version,
        permitted_modes=permitted_modes
    )
    return jsonify(res)

@app.route("/blockchain/revoke", methods=["POST"])
def blockchain_revoke():
    from blockchain_service import blockchain_service
    data = request.get_json() or {}
    persona_name = data.get("persona_name", "Prem")
    user_name = data.get("user_name", "User")
    
    res = blockchain_service.revoke_consent(persona_name, user_name)
    return jsonify(res)

@app.route("/blockchain/audit", methods=["GET"])
def blockchain_audit():
    from blockchain_service import blockchain_service
    return jsonify(blockchain_service.list_audit_trail())

@app.route("/blockchain/verify-integrity", methods=["POST"])
def blockchain_verify_integrity():
    from blockchain_service import blockchain_service
    data = request.get_json() or {}
    persona_name = data.get("persona_name", "Prem")
    user_name = data.get("user_name", "User")
    
    results = []
    all_intact = True
    if memory:
        for fact in memory.list_all_facts():
            fact_id = fact.get("id")
            category = fact.get("category")
            detail = fact.get("detail")
            
            if fact_id:
                res = blockchain_service.verify_memory_integrity(fact_id, category, detail)
                results.append({
                    "id": fact_id,
                    "category": category,
                    "detail": detail[:40] + "..." if len(detail) > 40 else detail,
                    "local_hash": res.get("local_hash"),
                    "blockchain_hash": res.get("blockchain_hash"),
                    "status": res.get("status")
                })
                if res.get("status") == "TAMPERING_DETECTED":
                    all_intact = False
                    
    return jsonify({
        "all_intact": all_intact,
        "results": results
    })

@app.route("/blockchain/memory/batch", methods=["POST"])
def blockchain_memory_batch():
    from blockchain_service import blockchain_service
    data = request.get_json() or {}
    persona_name = data.get("persona_name", "Prem")
    user_name = data.get("user_name", "User")
    memories = data.get("memories", [])
    
    if not memories:
        return jsonify({"error": "No memory facts provided for batch"}), 400
        
    res = blockchain_service.register_memory_batch(persona_name, user_name, memories)
    return jsonify(res)

# ── GDPR ARTICLE 17 RIGHT TO ERASURE (Section VI-F) ───────────────
@app.route("/delete-all-data", methods=["POST"])
def delete_all_data():
    """Permanently delete all stored facts, FAISS indices, chat logs, and generated audio."""
    try:
        data = request.get_json() or {}
        persona_name = data.get("persona_name", "Prem")
        user_name = data.get("user_name", "User")

        # Log data erasure event on-chain if blockchain is available
        from blockchain_service import blockchain_service
        if blockchain_service.is_healthy() and blockchain_service.contract:
            try:
                blockchain_service.register_data_erasure(persona_name, user_name)
            except Exception as ex:
                log_event("warning", "blockchain_erasure_failed", error=str(ex))

        if memory:
            memory.wipe_all_data()
        
        for f in glob.glob(os.path.join("generated_audio", "*.wav")):
            try: os.remove(f)
            except: pass
            
        if os.path.exists("questionnaire_results.json"):
            try: os.remove("questionnaire_results.json")
            except: pass

        # Wipe local blockchain audit log entries on right to erasure
        if os.path.exists("blockchain_records.json"):
            try: os.remove("blockchain_records.json")
            except: pass

        log_event("info", "gdpr_erasure_completed")
        return jsonify({
            "status": "success",
            "message": "All user data, FAISS memory stores, and audio artifacts permanently erased."
        }), 200
    except Exception as e:
        log_event("warning", "gdpr_erasure_failed", error=str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    def _prewarm_ollama():
        log_event("info", "ollama_prewarm_start", model=OLLAMA_MODEL)
        try:
            resp = http_requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": "hello",
                "stream": False,
                "keep_alive": -1
            }, timeout=120)
            resp.raise_for_status()
            log_event("info", "ollama_prewarm_ok", model=OLLAMA_MODEL)
        except Exception:
            log_event("warning", "ollama_prewarm_failed", hint="Make sure Ollama is running on localhost:11434")

    def _auto_start_blockchain():
        import socket
        import subprocess
        import time

        def is_port_open(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('127.0.0.1', port)) == 0

        if not is_port_open(8545):
            print("\n" + "="*70)
            print("🔗 STARTING LOCAL HARDHAT BLOCKCHAIN NODE AUTOMATICALLY")
            print("="*70)
            try:
                # Start hardhat node in background
                subprocess.Popen(
                    ["npx", "hardhat", "node"],
                    cwd="blockchain",
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("🚀 Hardhat local node process launched. Waiting for port 8545 to open...")
                for i in range(12):
                    if is_port_open(8545):
                        print("✅ Hardhat local node is now online on port 8545!")
                        break
                    time.sleep(0.5)
                else:
                    print("⚠️  Hardhat node port bind timed out. Local chain may not be accessible.")
                    return

                # Deploy contract
                print("📦 Compiling and deploying MemoryBridgeRegistry smart contract...")
                deploy_proc = subprocess.run(
                    ["npx", "hardhat", "run", "scripts/deploy.js", "--network", "localhost"],
                    cwd="blockchain",
                    capture_output=True,
                    text=True
                )
                if deploy_proc.returncode == 0:
                    print("❇️  Smart contract successfully deployed to local chain network!")
                    from blockchain_service import blockchain_service
                    blockchain_service._initialize_web3()
                else:
                    print(f"❌ Smart contract deployment failed:\n{deploy_proc.stderr}")
            except Exception as e:
                print(f"❌ Failed to start local blockchain services: {e}")
            print("="*70 + "\n")
        else:
            print("[BLOCKCHAIN] Hardhat blockchain node already active on port 8545.")

    # Automate blockchain node launch & deployment
    _auto_start_blockchain()

    # Kick off warmup without blocking server start
    if os.environ.get("WARMUP_ON_STARTUP", "1") == "1":
        threading.Thread(target=_warmup_background, daemon=True).start()
        threading.Thread(target=_prewarm_ollama, daemon=True).start()

    app.run(host="0.0.0.0", port=5000, debug=False)

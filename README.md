# 🎤 Voice Chat - AI-Powered Conversational Avatar

An advanced voice chat application that combines large language models (Ollama), text-to-speech synthesis, emotion detection, and 3D avatar visualization for immersive interactive conversations.

## 🌟 Features

- **Multi-turn Conversations**: Persistent memory system using FAISS for semantic search and conversation history
- **Emotion-Aware Responses**: Real-time emotion detection using DistilRoBERTa model
- **Advanced Text-to-Speech**: XTTS v2 multilingual model for natural voice synthesis
- **3D Avatar Visualization**: OpenGL-rendered 3D models that respond to conversation
- **Ollama Integration**: On-device LLM support for privacy-first conversations
- **Web Interface**: Flask-based REST API with interactive frontend
- **Knowledge Base**: Custom knowledge injection with semantic indexing
- **Sentiment Analysis**: Integrated emotion pipeline for nuanced responses

## 📚 Research Papers Referenced

This project builds on cutting-edge research in:
- Digital Immortality and Afterlife Technologies
- Emotional Support Chatbot Design
- Voice-based AI Interactions
- Virtual Reality Therapeutic Experiences
- Conversational AI with Synthetic Data Generation
- Memory Integration for Natural Language Systems

See `Research Papers/` directory for full references.

## 🛠️ Prerequisites

- Python 3.9+
- Ollama (for local LLM inference)
- CUDA (optional, for GPU acceleration)

## 📦 Installation

### 1. Clone Repository
```bash
git clone https://github.com/PremB2907/voice_chat.git
cd voice_chat
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download TTS & Emotion Models
The models are downloaded automatically on first run, but you can pre-download:
```bash
python -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')"
```

### 5. Setup Ollama (Optional)
```bash
# Download from https://ollama.ai
ollama pull llama3  # or any model you prefer
ollama serve  # Start Ollama server on localhost:11434
```

## 🚀 Quick Start

### 1. Initialize Knowledge Base (First Time Only)
```bash
python setup_prem_knowledge.py
```

This creates:
- `prem_knowledge_base.json` - Knowledge base
- `memory_index.faiss` - Semantic search index (if/when populated)

### 2. Start the Server
```bash
# Important: start Ollama first (unless you expect responses to fall back).
# ollama serve
python server.py
```

Server will start on `http://localhost:5000`

### 3. Open in Browser
Navigate to:
```
http://localhost:5000
```

## 📁 Project Structure

```
voice_chat/
├── server.py                 # Main Flask server & API endpoints
├── memory_store.py           # Conversation memory & knowledge management
├── scripts/
│   ├── app.py               # CLI text-to-speech tool
│   ├── app_emotions.py      # Emotion-aware chat CLI
│   ├── emotion_tts.py       # TTS with emotion integration
│   ├── emotion_advanced.py  # Advanced emotion analysis
│   ├── emotion_voice.py     # Voice-based emotion detection
│   ├── tts_engine.py        # Core TTS engine
│   ├── voice_clone.py       # Voice cloning utilities
│   └── test_api.py          # API testing
├── static/
│   ├── index.html           # Main web interface
│   ├── step1.html           # Onboarding UI
│   ├── step2.html           # Configuration UI
│   ├── frontend/
│   │   ├── app.js           # Frontend application logic
│   │   ├── style.css        # Styling
│   │   └── presentation.css # Presentation mode styles
│   └── model.glb            # 3D Avatar model (GLB format)
├── prem_knowledge_base.json # Custom knowledge base
├── memory_index.faiss       # Semantic search index
├── memory_log.json          # Conversation history
├── requirements.txt         # Python dependencies
└── Research Papers/         # Referenced academic papers
```

## 🔧 Configuration

### TTS Settings
Modify in `server.py`:
```python
TTS("tts_models/multilingual/multi-dataset/xtts_v2")
```

### Emotion Model
Currently uses: `j-hartmann/emotion-english-distilroberta-base`

### Ollama Model
Update in `server.py` - defaults to `llama3`

### Memory Settings
Configure in `memory_store.py`:
- Vector dimension: 384
- Max similar contexts: 3
- Memory persistence location

## 📋 API Endpoints

### POST `/chat`
Send a message and get a response with emotion detection
```json
{
  "message": "Hello!",
  "user_id": "user123"
}
```

### GET `/audio/<filename>`
Stream generated audio files

### POST `/emotion`
Analyze emotion of input text

## 🔗 Integration Points

### Ollama
- Default endpoint: `http://localhost:11434`
- Configurable in `server.py`
- Fallback to public API if Ollama unavailable

### TTS Engine
- Model: XTTS v2 (Multilingual)
- Supports 13+ languages
- Customizable speaker characteristics

### Memory System
- FAISS for semantic similarity
- Sentence Transformers for embeddings
- JSON persistence for conversation logs

## 🧪 Testing

Run individual components:
```bash
# Test Ollama connection
python test_ollama.py

# Test TTS
python scripts/test_tts.py

# Test API
python scripts/test_api.py

# Check model status
python check_model.py
```

## 📊 Logging

The server emits **structured JSON logs** (one JSON object per log line).

### Control verbosity

```bash
# Linux/macOS
LOG_LEVEL=DEBUG python server.py

# Windows (PowerShell)
$env:LOG_LEVEL="DEBUG"; python server.py
```

Common levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`.

### Cleaner console modes (A / B)

The server logs are structured JSON internally, but the console is rendered as **emoji one-liners**.

- **Mode A**: only show `WARNING`/`ERROR` (quiet)
- **Mode B**: show `INFO`, but hide warmup/prewarm noise
- **Mode AB**: show everything (default)

```bash
# Linux/macOS
LOG_CONSOLE_MODE=A  python server.py
LOG_CONSOLE_MODE=B  python server.py
LOG_CONSOLE_MODE=AB python server.py

# Windows (PowerShell)
$env:LOG_CONSOLE_MODE="A";  python server.py
$env:LOG_CONSOLE_MODE="B";  python server.py
$env:LOG_CONSOLE_MODE="AB"; python server.py
```

### Pretty-print logs

```bash
# From a file
python scripts/parse_logs.py path/to/server.log

# Or from a stream (Linux/macOS)
python server.py 2>&1 | python scripts/parse_logs.py
```

### Production aggregation (optional)

Because the payload is JSON, it’s easy to ship logs to tools like **ELK/OpenSearch**, **Datadog**, or **CloudWatch**
and filter by fields like `"event"`, `"error"`, `"model"`, etc.

## 🔄 Reset Memory

Clear conversation history and memory index:
```bash
python reset_memory.py
```

## 🔊 Voice Samples

Voice cloning uses WAV files in `voice_samples/`. The default configured sample is currently named
`my_voice.wav.wav` (double `.wav` extension); that’s expected by `server.py` unless you change it.

## 📊 Performance Tips

1. **GPU Acceleration**: Install CUDA version of torch for faster inference
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Memory Optimization**: Reduce `max_similar_contexts` in memory_store.py for lower memory usage

3. **Ollama Performance**: Use quantized models (e.g., `neural-chat:7b-q5`)

## 🐛 Troubleshooting

### Models not downloading
- Check internet connection
- Manually download with: `python -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')"`

### Ollama connection failed
- Ensure Ollama is running: `ollama serve`
- Check port 11434 is accessible
- Fallback to API mode is automatic

### Audio playback issues
- Ensure audio device is connected
- Install audio drivers for your OS
- Check file permissions in `generated_audio/` directory

### Out of memory errors
- Reduce batch size in `tts_engine.py`
- Use CPU mode if GPU memory insufficient
- Restart server to flush memory

## 📝 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pyttsx3 | Latest | Text-to-speech (fallback) |
| sounddevice | Latest | Audio I/O |
| scipy | Latest | Signal processing |
| faiss-cpu | Latest | Vector search |
| sentence-transformers | Latest | Embeddings & similarity |
| transformers | Latest | NLP models |
| torch | Latest | Deep learning framework |
| flask-cors | Latest | Cross-origin requests |
| TTS (Coqui) | Latest | Advanced TTS synthesis |

## 🚀 Future Enhancements

- [ ] Real-time voice input streaming
- [ ] Multi-user conversation support
- [ ] Custom emotion labels
- [ ] Advanced voice cloning
- [ ] Conversation analytics dashboard
- [ ] Multiple avatar options
- [ ] Conversation export (PDF/JSON)

## 📄 License

[Add your license here]

## 👤 Author

**Prem** - [GitHub Profile](https://github.com/PremB2907)

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## ❓ Support

For issues and questions, please open an issue on [GitHub Issues](https://github.com/PremB2907/voice_chat/issues)

---

**Note**: This project uses on-device models for privacy. All conversations can be stored locally. For production use, review the memory storage and data retention policies.

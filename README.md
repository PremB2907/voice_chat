# 🎙️ Voice Chat AI

Your browser talks.
Your AI answers.
Emotions included.

An end-to-end **AI Voice Chat System** that listens, understands emotion, generates intelligent responses, and speaks back with expressive voice output. Built with Python, emotion modeling, TTS pipelines, and a clean frontend interface.

---

## 🚀 What This Project Does

* 🎤 Accepts user voice input
* 🧠 Detects emotional tone
* 🤖 Generates contextual AI response
* 🔊 Converts response into expressive speech
* 🌐 Serves everything through a simple web interface

This is not just TTS.
It’s conversation with mood.

---

## 🧩 Project Architecture

```
voice_chat/
│
├── server.py             # Main Server logic
├── requirements.txt      # Python dependencies
├── .gitignore
│
├── static/               # Frontend elements
│   ├── index.html
│   ├── step1.html
│   ├── step2.html
│   └── frontend/
│       ├── style.css
│       └── app.js
│
├── scripts/              # AI and TTS test modules
│   ├── ai_voice_chat.py
│   ├── emotion_voice.py 
│   ├── emotion_tts.py   
│   ├── emotion_advanced.py
│   ├── tts_engine.py    
│   ├── voice_clone.py   
│   └── test_tts.py      
│
└── generated_audio/      # Output dynamically generated speech
```

---

## ⚙️ Tech Stack

* 🐍 Python
* 🌐 Flask
* 🎧 Text-to-Speech (TTS)
* 🎭 Emotion Detection Logic
* 🖥 HTML, CSS, JavaScript

---

## 🧠 Emotion Engine

The system supports multiple emotional states such as:

* 😊 Happy
* 😡 Angry
* 😢 Sad
* 😌 Calm

Each emotion influences:

* Voice tone
* Speech variation
* Response modulation

It creates a more natural and immersive AI conversation flow.

---

## 🔧 Installation Guide

### 1️⃣ Clone the repository

```bash
git clone https://github.com/PremB2907/voice_chat.git
cd voice_chat
```

### 2️⃣ Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run the application

```bash
python server.py
```

Open browser:

```
http://127.0.0.1:5000
```

---

## 🌐 Frontend Features

* Clean minimal interface
* Voice interaction ready
* Dynamic response playback
* Emotion-based response feel

---

## 🧪 Testing

Run TTS test:

```bash
python test_tts.py
```

---

## 🔮 Future Improvements

* Real-time speech-to-text integration
* Better emotion classification model
* Database logging of conversations
* Role-based multi-user support
* Deploy to cloud (AWS / Render / Railway)

---

## 🛡️ .gitignore Highlights

This project excludes:

* `venv/`
* `__pycache__/`
* Generated `.wav` files
* Temporary audio outputs

Keeping the repo clean and lightweight.

---

## 📌 Use Cases

* AI Companions
* Mental wellness bots
* Voice-based assistants
* Emotion-aware conversational systems
* Experimental AI research projects

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Commit changes
4. Open Pull Request

---

## 📄 License

This project is open-source and available under the MIT License.

---

## 👨‍💻 Author

**Prem Baraskar**
AI + Voice Systems Explorer
Building expressive machines.

---

If you liked this project ⭐
Drop a star on GitHub and let the algorithm smile a little.

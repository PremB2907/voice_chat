/* ═══════════════════════════════════════════════════
   MOBILE KEYBOARD FIX — Visual Viewport API
═══════════════════════════════════════════════════ */
const app       = document.getElementById("app");
const inputArea = document.getElementById("input-area");
const chatBox   = document.getElementById("chat-box");

function adjustForKeyboard() {
  if (!window.visualViewport) return;
  const vv = window.visualViewport;
  // Distance from bottom of visual viewport to bottom of layout viewport
  const offsetFromBottom = window.innerHeight - (vv.offsetTop + vv.height);
  // Shift the app up by keyboard height
  app.style.height = vv.height + 'px';
  app.style.marginTop = vv.offsetTop + 'px';
  // Scroll chat to bottom
  requestAnimationFrame(() => {
    chatBox.scrollTop = chatBox.scrollHeight;
  });
}

if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', adjustForKeyboard);
  window.visualViewport.addEventListener('scroll', adjustForKeyboard);
}

/* Scroll to bottom when input is focused (fallback) */
const userInput = document.getElementById("user-input");
userInput.addEventListener('focus', () => {
  setTimeout(() => chatBox.scrollTop = chatBox.scrollHeight, 350);
});

/* ═══════════════════════════════════════════════════
   CHAT LOGIC
═══════════════════════════════════════════════════ */
const sendBtn   = document.getElementById("send-btn");
const waveBar   = document.getElementById("wave-bar");
const waveTimer = document.getElementById("wave-timer");
const themeBtn  = document.getElementById("theme-toggle");
const clearBtn  = document.getElementById("clear-btn");
const audioPill = document.getElementById("audio-pill");
const toastEl   = document.getElementById("toast");

const SERVER = window.location.origin;
let timerInterval = null;
let isLoading = false;

const HISTORY_KEY = "un-miss-history";
let chatHistory = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");

const globalAudio = new Audio();
globalAudio.crossOrigin = "anonymous";
let audioCtx, analyser, source, dataArray;


function getTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function removeEmpty() {
  const e = document.getElementById("empty-state");
  if (e) e.remove();
}

function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, tag => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[tag]));
}

function addMessage(sender, text, isUser = false, saveItem = true) {
  removeEmpty();
  const div = document.createElement("div");
  div.className = `message ${isUser ? 'user' : 'prem'}`;
  
  const contentHtml = isUser ? escapeHTML(text) : DOMPurify.sanitize(marked.parse(text));
  
  if (saveItem) {
    chatHistory.push({ sender, text, isUser });
    localStorage.setItem(HISTORY_KEY, JSON.stringify(chatHistory));
  }
  
  div.innerHTML = `
    <div class="msg-meta">
      <span class="msg-name">${sender}</span>
      <span class="msg-time">${getTime()}</span>
    </div>
    <div class="bubble">${contentHtml}</div>
  `;
  chatBox.appendChild(div);
  requestAnimationFrame(() => { chatBox.scrollTop = chatBox.scrollHeight; });
  return div;
}

function addTyping() {
  removeEmpty();
  const div = document.createElement("div");
  div.className = "typing-wrap";
  div.id = "typing-indicator";
  div.innerHTML = `
    <div class="typing-label">Prem</div>
    <div class="typing-bubble">
      <div class="tdot"></div>
      <div class="tdot"></div>
      <div class="tdot"></div>
    </div>
  `;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function removeTyping() {
  const t = document.getElementById("typing-indicator");
  if (t) t.remove();
}

function showToast(msg, ms = 3500) {
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), ms);
}

function setLoading(on) {
  isLoading = on;
  waveBar.classList.toggle("active", on);
  sendBtn.disabled = on;
  userInput.disabled = on;

  if (on) {
    let s = 0;
    waveTimer.textContent = "0s";
    timerInterval = setInterval(() => { waveTimer.textContent = (++s) + "s"; }, 1000);
    addTyping();
  } else {
    clearInterval(timerInterval);
    removeTyping();
    userInput.disabled = false;
    setTimeout(() => {
      if (window.innerWidth > 768) userInput.focus();
    }, 100);
  }
}

function showAudioPill(show) {
  audioPill.classList.toggle("show", show);
}

function setupAudio(url) {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 32;
    source = audioCtx.createMediaElementSource(globalAudio);
    source.connect(analyser);
    analyser.connect(audioCtx.destination);
    dataArray = new Uint8Array(analyser.frequencyBinCount);
    document.querySelectorAll(".apb").forEach(b => b.style.animation = "none");
    visualize();
  }
  if (audioCtx.state === 'suspended') audioCtx.resume();
  globalAudio.src = url;
  
  const stopBtn = document.getElementById("stop-audio-btn");
  if (stopBtn) {
    stopBtn.onclick = () => {
      globalAudio.pause();
      showAudioPill(false);
      document.querySelectorAll(".bubble.playing").forEach(b => b.classList.remove("playing"));
    };
  }
  return globalAudio;
}

function visualize() {
  requestAnimationFrame(visualize);
  if (globalAudio.paused || globalAudio.ended) {
    document.querySelectorAll(".apb").forEach((bar, i) => bar.style.height = [4,10,14,10,4][i] + "px");
    return;
  }
  analyser.getByteFrequencyData(dataArray);
  const bars = document.querySelectorAll(".apb");
  for (let i = 0; i < bars.length; i++) {
    const val = dataArray[i * 2 + 1] || 0;
    const h = 4 + (val / 255) * 16;
    if (bars[i]) bars[i].style.height = h + "px";
  }
}

async function sendMessage() {
  const message = userInput.value.trim();
  if (!message || isLoading) return;

  addMessage("Maitree", message, true);
  userInput.value = "";
  setLoading(true);

  try {
    const mbti = localStorage.getItem("mbti") || "INFJ";
    const res = await fetch(`${SERVER}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, mbti })
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();

    setLoading(false);
    const msgEl  = addMessage("Prem", data.reply, false);
    const bubble = msgEl.querySelector(".bubble");

    const audio = setupAudio(`${SERVER}/audio/${data.audio}`);
    audio.onplay   = () => { bubble.classList.add("playing");   showAudioPill(true);  };
    audio.onended  = () => { bubble.classList.remove("playing"); showAudioPill(false); };
    audio.onerror  = () => { bubble.classList.remove("playing"); showAudioPill(false); };

    audio.play().catch(() => {
      showToast("▶  TAP PREM'S MESSAGE TO PLAY");
      bubble.style.cursor = "pointer";
      bubble.onclick = () => { audio.play(); bubble.onclick = null; bubble.style.cursor = ""; };
    });

  } catch (err) {
    setLoading(false);
    showToast("⚠  " + err.message);
    addMessage("Prem", "Maitree… I can't reach you right now.", false);
  }
}

/* ═══ EVENTS ═══ */
sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

/* ═══ THEME ═══ */
let isLight = false;
themeBtn.addEventListener("click", () => {
  isLight = !isLight;
  themeBtn.textContent = isLight ? "🌙" : "☀";
  document.documentElement.classList.toggle('light-mode', isLight);
});

/* ═══ CLEAR ═══ */
clearBtn.addEventListener("click", () => {
  chatBox.innerHTML = `
    <div class="empty-state" id="empty-state">
      <div class="empty-mandala">
        <div class="mandala-ring"></div>
        <div class="mandala-ring"></div>
        <div class="mandala-ring"></div>
        <div class="mandala-center">MB</div>
      </div>
      <div class="empty-title">Un-Miss</div>
      <div class="empty-msg">
        Say something to Prem <span class="blink-cursor"></span>
      </div>
    </div>`;
});

/* ═══ SHUTDOWN ═══ */
const shutdownBtn = document.getElementById("shutdown-btn");
if (shutdownBtn) {
  shutdownBtn.addEventListener("click", async () => {
    if(!confirm("Are you sure you want to stop the server and end the conversation?")) return;
    try {
      await fetch(`${SERVER}/shutdown`, { method: "POST" });
    } catch(e) { /* Ignoring error since server shutdown will close connection */ }
    
    showToast("Server stopped. You can close this window now.");
    document.body.style.opacity = "0.4";
    document.body.style.pointerEvents = "none";
  });
}

/* Desktop autofocus */
if (window.innerWidth > 768) userInput.focus();

/* ═══ SPEECH RECOGNITION ═══ */
const micBtn = document.getElementById("mic-btn");
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition && micBtn) {
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  recognition.onstart = () => {
    micBtn.classList.add("recording");
    userInput.placeholder = "Listening...";
  };
  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    userInput.value = transcript;
    sendMessage();
  };
  recognition.onerror = (e) => {
    showToast("⚠ Mic Error: " + e.error);
    micBtn.classList.remove("recording");
    userInput.placeholder = "Talk to Prem...";
  };
  recognition.onend = () => {
    micBtn.classList.remove("recording");
    userInput.placeholder = "Talk to Prem...";
  };

  micBtn.addEventListener("click", () => {
    if (micBtn.classList.contains("recording")) {
      recognition.stop();
    } else {
      recognition.start();
    }
  });
} else if (micBtn) {
  micBtn.style.display = "none";
}

/* ═══ RESTORE HISTORY ═══ */
chatHistory.forEach(msg => addMessage(msg.sender, msg.text, msg.isUser, false));
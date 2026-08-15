import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

/* ═══════════════════════════════════════════════════
   THREE.JS GLOBAL STATE
═══════════════════════════════════════════════════ */
let scene, camera, renderer, clock, mixer;
window.jawBone = null;
window.jawBoneBaseRotation = 0;
window.headBone = null;
window.headBoneBaseRotation = 0;

/* ═══════════════════════════════════════════════════
   AMBIENT PARTICLE SYSTEM
═══════════════════════════════════════════════════ */
function initAmbientCanvas() {
  const canvas = document.getElementById("ambient-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let w, h;
  const particles = [];
  const PARTICLE_COUNT = 50;

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x = Math.random() * w;
      this.y = Math.random() * h;
      this.size = Math.random() * 2 + 0.5;
      this.speedX = (Math.random() - 0.5) * 0.3;
      this.speedY = (Math.random() - 0.5) * 0.2 - 0.1;
      this.opacity = Math.random() * 0.3 + 0.05;
      this.fadeDir = Math.random() > 0.5 ? 1 : -1;
      this.hue = Math.random() > 0.6 ? 42 : 260; // gold or violet
      this.sat = this.hue === 42 ? '60%' : '45%';
      this.light = this.hue === 42 ? '65%' : '60%';
    }
    update() {
      this.x += this.speedX;
      this.y += this.speedY;
      this.opacity += this.fadeDir * 0.002;
      if (this.opacity <= 0.02 || this.opacity >= 0.35) this.fadeDir *= -1;
      if (this.x < -10 || this.x > w + 10 || this.y < -10 || this.y > h + 10) this.reset();
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(${this.hue}, ${this.sat}, ${this.light}, ${this.opacity})`;
      ctx.fill();
    }
  }

  for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(new Particle());

  function animate() {
    requestAnimationFrame(animate);
    ctx.clearRect(0, 0, w, h);
    for (const p of particles) { p.update(); p.draw(); }
  }
  animate();
}

initAmbientCanvas();

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
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

const SERVER = window.location.origin;
let timerInterval = null;
let isLoading = false;
let isVoiceOn = true;  // declared here so sendMessage can use it
let isServerOnline = true;

const HISTORY_KEY = "un-miss-history";
let chatHistory = [];
try {
  chatHistory = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  if (!Array.isArray(chatHistory)) chatHistory = [];
} catch {
  chatHistory = [];
}

const globalAudio = new Audio();
globalAudio.crossOrigin = "anonymous";
let audioCtx, analyser, source, dataArray;


/* ═══════════════════════════════════════════════════
   SESSION TIMER SAFEGUARD (Section VI-D)
═══════════════════════════════════════════════════ */
let sessionStart = Date.now();
const sessionClockEl = document.getElementById("session-clock");
setInterval(() => {
  if (!sessionClockEl) return;
  const elapsedSec = Math.floor((Date.now() - sessionStart) / 1000);
  const mins = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
  const secs = String(elapsedSec % 60).padStart(2, '0');
  sessionClockEl.textContent = `${mins}:${secs}`;

  // Section VI-D: 30-minute session duration warning
  if (elapsedSec === 1800) {
    showToast("⏱ Session duration limit (30 mins) reached. Remember to take a break and care for yourself.");
  }
}, 1000);

function getPersonaName() {
  return localStorage.getItem("persona_name") || "Prem";
}
function getUserName() {
  return localStorage.getItem("user_name") || "Maitree";
}

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

function addMessage(sender, text, isUser = false, saveItem = true, aiTransparency = null, blockchainProvenance = null) {
  removeEmpty();
  const div = document.createElement("div");
  div.className = `message ${isUser ? 'user' : 'prem'}`;
  
  const contentHtml = isUser ? escapeHTML(text) : DOMPurify.sanitize(marked.parse(text));
  
  if (saveItem) {
    chatHistory.push({ sender, text, isUser, aiTransparency, blockchainProvenance });
    localStorage.setItem(HISTORY_KEY, JSON.stringify(chatHistory));
  }
  
  let transparencyBadge = "";
  if (!isUser) {
    const confidence = (aiTransparency && aiTransparency.confidence_score) ? `${aiTransparency.confidence_score}%` : 'AI';
    transparencyBadge = `<span class="ai-badge" title="MemoryBridge AI Transparency Disclosure">[AI · ${confidence}]</span>`;
  }

  let provenanceBadge = "";
  if (!isUser && blockchainProvenance) {
    const status = blockchainProvenance.status || "PENDING";
    const evId = blockchainProvenance.event_id || "";
    const hash = blockchainProvenance.response_hash || "";
    
    let badgeClass = "status-unknown";
    let badgeText = "⏳ Verification Pending";
    if (status === "CONFIRMED") {
      badgeClass = "status-verified";
      badgeText = "✓ Blockchain Verified";
    } else if (status === "FAILED") {
      badgeClass = "status-failed";
      badgeText = "❌ Verification Failed";
    }
    
    provenanceBadge = `
      <div class="provenance-badge ${badgeClass}" id="prov-${evId}" data-hash="${hash}" title="On-Chain Response Hash: ${hash}">
        🛡️ <span class="badge-text">${badgeText}</span>
      </div>
    `;
  }
  
  div.innerHTML = `
    <div class="msg-meta">
      <span class="msg-name">${sender}</span>
      <span class="msg-time">${getTime()}</span>
      ${transparencyBadge}
    </div>
    <div class="bubble">
      ${contentHtml}
      ${provenanceBadge}
    </div>
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
    <div class="typing-label">${getPersonaName()}</div>
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

function setServerStatus(state, text) {
  isServerOnline = state === "online" || state === "warn";
  if (statusDot) {
    statusDot.classList.remove("online", "offline", "warn");
    statusDot.classList.add(state);
  }
  if (statusText) statusText.textContent = text;
}

async function pollServerStatus() {
  try {
    const res = await fetch(`${SERVER}/memory-status`, { cache: "no-store" });
    if (!res.ok) throw new Error("offline");
    const data = await res.json();
    if (data && data.mismatch) {
      setServerStatus("warn", "Memory mismatch");
    } else {
      setServerStatus("online", "Online");
    }
  } catch {
    setServerStatus("offline", "Offline");
  }
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
  const avatarView = document.getElementById("avatar-view");
  
  if (globalAudio.paused || globalAudio.ended) {
    document.querySelectorAll(".apb").forEach((bar, i) => bar.style.height = [4,10,14,10,4][i] + "px");
    if (window.faceMesh && window.faceMesh.morphTargetDictionary) {
      const dict = window.faceMesh.morphTargetDictionary;
      for (const key in dict) {
        window.faceMesh.morphTargetInfluences[dict[key]] *= 0.85;
      }
    }
    if (window.jawBone) {
      window.jawBone.rotation.x += (window.jawBoneBaseRotation - window.jawBone.rotation.x) * 0.2;
    }
    if (window.headBone) {
      window.headBone.rotation.x += (window.headBoneBaseRotation - window.headBone.rotation.x) * 0.15;
    }
    if (avatarView) {
      avatarView.style.transform = "scale(1)";
      avatarView.style.filter = "none";
    }
    return;
  }
  
  analyser.getByteFrequencyData(dataArray);
  const bars = document.querySelectorAll(".apb");
  
  let bass = 0, mid = 0, treble = 0;
  const binCount = dataArray.length;
  const third = Math.max(1, Math.floor(binCount / 3));
  for (let i = 0; i < binCount; i++) {
    if (i < third) bass += dataArray[i];
    else if (i < 2 * third) mid += dataArray[i];
    else treble += dataArray[i];
  }
  const bassNorm = Math.min(1, (bass / third) / 200);
  const midNorm = Math.min(1, (mid / third) / 200);
  const trebleNorm = Math.min(1, (treble / Math.max(1, binCount - 2 * third)) / 200);
  const overallIntensity = (bassNorm * 0.5 + midNorm * 1.0 + trebleNorm * 0.5) / 2.0;
  
  for (let i = 0; i < bars.length; i++) {
    const val = dataArray[i * 2 + 1] || 0;
    const h = 4 + (val / 255) * 16;
    if (bars[i]) bars[i].style.height = h + "px";
  }

  if (window.faceMesh && window.faceMesh.morphTargetDictionary) {
    const dict = window.faceMesh.morphTargetDictionary;
    const influences = window.faceMesh.morphTargetInfluences;
    for (const key in dict) influences[dict[key]] *= 0.65;
    
    const findIdx = (keywords) => {
      for (const kw of keywords) {
        for (const d in dict) {
          if (d.toLowerCase().includes(kw)) return dict[d];
        }
      }
      return -1;
    };
    
    const idxOh = findIdx(["oh", "ou", "o_", "viseme_o"]);
    const idxAa = findIdx(["aa", "open", "a_", "viseme_a", "jawopen"]);
    const idxEe = findIdx(["ee", "smile", "i_", "viseme_e"]);
    
    if (idxOh !== -1) influences[idxOh] = Math.min(1, influences[idxOh] + bassNorm * 0.9);
    if (idxAa !== -1) influences[idxAa] = Math.min(1, influences[idxAa] + midNorm * 0.9);
    if (idxEe !== -1) influences[idxEe] = Math.min(1, influences[idxEe] + trebleNorm * 0.7);
  }
  
  if (window.jawBone) {
    const targetRot = window.jawBoneBaseRotation + (overallIntensity * 0.4);
    window.jawBone.rotation.x += (targetRot - window.jawBone.rotation.x) * 0.5;
  }
  
  if (window.headBone) {
    const headTarget = window.headBoneBaseRotation + (overallIntensity * 0.08);
    window.headBone.rotation.x += (headTarget - window.headBone.rotation.x) * 0.3;
  }
  
  if (avatarView) {
    const scale = 1 + overallIntensity * 0.025;
    avatarView.style.transform = `scale(${scale})`;
    const glow = overallIntensity * 20;
    if (glow > 2) {
      avatarView.style.filter = `drop-shadow(0 0 ${glow}px rgba(155, 142, 196, ${0.15 + overallIntensity * 0.3}))`;
    } else {
      avatarView.style.filter = "none";
    }
  }
}

async function sendMessage() {
  const message = userInput.value.trim();
  if (!message || isLoading) return;
  if (!isServerOnline) {
    showToast("Server offline. Start server.py first.");
    return;
  }

  const personaName = getPersonaName();
  const userName = getUserName();

  addMessage(userName, message, true);
  userInput.value = "";
  setLoading(true);

  try {
    const customContext = localStorage.getItem("customContext") || "";
    const mbti = localStorage.getItem("mbti") || "";
    const res = await fetch(`${SERVER}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        message, 
        mbti, 
        custom_context: customContext, 
        persona_name: personaName,
        user_name: userName,
        generate_audio: isVoiceOn 
      })
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();

    setLoading(false);
    const msgEl = addMessage(personaName, data.reply, false, true, data.ai_transparency, data.blockchain_provenance);
    const bubble = msgEl.querySelector(".bubble");

    if (data.rtf) {
      console.log(`[MemoryBridge TTS] RTF: ${data.rtf}`);
    }

    if (data.audio) {
      const audio = setupAudio(`${SERVER}/audio/${data.audio}`);
      audio.onplay   = () => { bubble.classList.add("playing");   showAudioPill(true);  };
      audio.onended  = () => { bubble.classList.remove("playing"); showAudioPill(false); };
      audio.onerror  = () => { bubble.classList.remove("playing"); showAudioPill(false); };

      audio.play().catch(() => {
        showToast(`▶ TAP ${personaName.toUpperCase()}'S MESSAGE TO PLAY`);
        bubble.style.cursor = "pointer";
        bubble.onclick = () => { audio.play(); bubble.onclick = null; bubble.style.cursor = ""; };
      });
    }

  } catch (err) {
    setLoading(false);
    setServerStatus("offline", "Offline");
    showToast("⚠ " + err.message);
    addMessage(personaName, `${userName}… I can't reach you right now.`, false);
  }
}

/* ═══ EVENTS ═══ */
sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

/* ═══ THEME ═══ */
let isLight = false;
if (themeBtn) {
  themeBtn.addEventListener("click", () => {
    isLight = !isLight;
    themeBtn.textContent = isLight ? "🌙" : "☀";
    document.documentElement.classList.toggle('light-mode', isLight);
  });
}

/* ═══ VOICE TOGGLE ═══ */
const voiceToggle = document.getElementById("voice-toggle");
if (voiceToggle) {
  voiceToggle.addEventListener("click", () => {
    isVoiceOn = !isVoiceOn;
    voiceToggle.textContent = isVoiceOn ? "🔊" : "🔇";
    voiceToggle.title = isVoiceOn ? "Voice Output ON" : "Voice Output OFF";
    showToast(isVoiceOn ? "Voice Output Enabled" : "Voice Output Disabled");
  });
}

/* ═══ CLEAR CHAT HISTORY ═══ */
clearBtn.addEventListener("click", () => {
  try { globalAudio.pause(); } catch {}
  showAudioPill(false);
  chatHistory = [];
  localStorage.removeItem(HISTORY_KEY);
  document.querySelectorAll(".bubble.playing").forEach(b => b.classList.remove("playing"));

  chatBox.innerHTML = `
    <div class="empty-state" id="empty-state">
      <div class="empty-orb">
        <div class="orb-glow"></div>
        <div class="orb-ring"></div>
        <div class="orb-ring"></div>
        <div class="orb-ring"></div>
        <div class="orb-center">MB</div>
      </div>
      <div class="empty-title">MemoryBridge</div>
      <div class="empty-msg">
        Speak to ${getPersonaName()} <span class="blink-cursor"></span>
      </div>
    </div>`;
});

/* ═══ GDPR ARTICLE 17 ERASE ALL DATA ═══ */
const eraseBtn = document.getElementById("erase-btn");
if (eraseBtn) {
  eraseBtn.addEventListener("click", async () => {
    if (!confirm("GDPR Article 17 Erasure: Are you sure you want to PERMANENTLY delete all memory stores, FAISS indices, chat history, and uploaded voice samples? This cannot be undone.")) return;
    try {
      const res = await fetch(`${SERVER}/delete-all-data`, { method: "POST" });
      const data = await res.json();
      localStorage.clear();
      chatHistory = [];
      showToast(data.message || "All user data permanently deleted.");
      setTimeout(() => location.reload(), 1500);
    } catch (err) {
      showToast("❌ Erasure failed: " + err.message);
    }
  });
}

/* ═══ SHUTDOWN ═══ */
const shutdownBtn = document.getElementById("shutdown-btn");
if (shutdownBtn) {
  shutdownBtn.addEventListener("click", async () => {
    if(!confirm("Are you sure you want to stop the server and end the conversation?")) return;
    try {
      await fetch(`${SERVER}/shutdown`, { method: "POST" });
    } catch(e) {}
    
    showToast("Server stopped. You can close this window now.");
    document.body.style.opacity = "0.3";
    document.body.style.pointerEvents = "none";
  });
}

/* Desktop autofocus */
if (window.innerWidth > 768) userInput.focus();

// Initial status + polling
setServerStatus("warn", "Connecting…");
pollServerStatus();
setInterval(pollServerStatus, 8000);

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
chatHistory.forEach(msg => addMessage(msg.sender, msg.text, msg.isUser, false, msg.aiTransparency, msg.blockchainProvenance));

/* ═══════════════════════════════════════════════════
   THREE.JS SETUP & GLB LOADER (3D Avatar)
═══════════════════════════════════════════════════ */
function initThreeJS() {
  const container = document.getElementById("three-canvas-container");
  if (!container) {
    console.error("❌ three-canvas-container not found!");
    return;
  }

  console.log("📐 Container dimensions:", container.clientWidth, "x", container.clientHeight);
  
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x060911);
  scene.fog = new THREE.FogExp2(0x060911, 0.02);

  camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
  camera.position.set(0, 1.5, 3);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.shadowMap.enabled = true;
  container.appendChild(renderer.domElement);
  console.log("✅ Renderer initialized");

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableZoom = false;
  controls.enablePan = false;
  controls.target.set(0, 1.4, 0); // Focus around the face area
  controls.update();

  // Lighting — softer, more ambient
  const hemiLight = new THREE.HemisphereLight(0xc8b8e8, 0x333355, 0.8);
  hemiLight.position.set(0, 20, 0);
  scene.add(hemiLight);

  const dirLight = new THREE.DirectionalLight(0xe8deff, 0.6);
  dirLight.position.set(0, 5, 5);
  scene.add(dirLight);

  // Subtle rim light for atmosphere
  const rimLight = new THREE.DirectionalLight(0x9b8ec4, 0.3);
  rimLight.position.set(-3, 2, -3);
  scene.add(rimLight);

  clock = new THREE.Clock();

// Load GLB Model (GLTF binary format - best for web)
  const loader = new GLTFLoader();
  console.log("🤖 Attempting to load model from: /model.glb");
  
  loader.load(
    '/model.glb',
    (gltf) => {
      console.log("✅ GLB Model loaded successfully!");
      const model = gltf.scene;
      
      // Setup animations if they exist
      if (gltf.animations && gltf.animations.length > 0) {
        mixer = new THREE.AnimationMixer(model);
        const action = mixer.clipAction(gltf.animations[0]);
        action.play();
        console.log(`🎬 Playing animation: ${gltf.animations[0].name}`);
      }

      model.position.set(0, 0, 0);
      model.scale.setScalar(1); // GLB usually already has correct scale
      
      // Traverse bones & meshes: fix T-pose, set up SALSA lip-sync & idle animation targets
      const boneNames = [];
      const meshNames = [];
      window.leftArmBone = null;
      window.rightArmBone = null;
      window.spineBone = null;

      model.traverse((child) => {
        if (child.isBone) {
          boneNames.push(child.name);
          const name = child.name.toLowerCase();

          // SALSA Jaw & Head Bone Detection
          if ((name.includes("jaw") || name.includes("mouth")) && !window.jawBone) {
            window.jawBone = child;
            window.jawBoneBaseRotation = child.rotation.x;
            console.log("[SALSA] Found Jaw Bone:", child.name);
          }
          if (name.includes("head") && !window.headBone) {
            window.headBone = child;
            window.headBoneBaseRotation = child.rotation.x;
            window.headBoneBaseRotationY = child.rotation.y;
            console.log("[SALSA] Found Head Bone:", child.name);
          }
          if ((name.includes("spine") || name.includes("chest")) && !window.spineBone) {
            window.spineBone = child;
          }

          // T-Pose Correction: Rotate upper arms down into a relaxed standing posture
          // Exclude root nodes (Armature, Hips, Root, Spine) to prevent displacing the whole model
          if (!name.includes("armature") && !name.includes("root") && !name.includes("hips") && !name.includes("spine")) {
            if (name.includes("upperarm") || name.includes("leftarm") || name.includes("rightarm") || name.includes("arm_l") || name.includes("arm_r")) {
              if (name.includes("l") || name.includes("left")) {
                if (!window.leftArmBone) {
                  window.leftArmBone = child;
                  child.rotation.z = -1.15;
                  child.rotation.y = 0.2;
                }
              } else if (name.includes("r") || name.includes("right")) {
                if (!window.rightArmBone) {
                  window.rightArmBone = child;
                  child.rotation.z = 1.15;
                  child.rotation.y = -0.2;
                }
              }
            }
          }
        }

        if (child.isMesh || child.isSkinnedMesh) {
          meshNames.push(child.name);
          child.castShadow = true;
          child.receiveShadow = true;
          if (child.morphTargetDictionary && Object.keys(child.morphTargetDictionary).length > 0) {
            window.faceMesh = child;
            console.log("[SALSA] Found Morph Targets:", Object.keys(child.morphTargetDictionary));
          }
        }
      });

      // Auto-scale & auto-fit camera framing to model bounding box
      const box = new THREE.Box3().setFromObject(model);
      if (!box.isEmpty()) {
        const size = box.getSize(new THREE.Vector3());
        
        // Normalize model scale to standard human height (~1.7m)
        if (size.y > 0.01) {
          const scaleFactor = 1.7 / size.y;
          model.scale.setScalar(scaleFactor);
        }

        const updatedBox = new THREE.Box3().setFromObject(model);
        const updatedSize = updatedBox.getSize(new THREE.Vector3());

        // Ground feet at y = 0
        model.position.y = -updatedBox.min.y;

        // Position camera to frame head & upper body clearly
        camera.position.set(0, updatedSize.y * 0.75, Math.max(1.2, updatedSize.y * 0.55));
        controls.target.set(0, updatedSize.y * 0.70, 0);
        controls.update();
      }

      console.log("[SALSA] All Bones:", boneNames);
      console.log("[SALSA] All Meshes:", meshNames);
      console.log("[SALSA] jawBone:", !!window.jawBone, "| headBone:", !!window.headBone, "| faceMesh:", !!window.faceMesh);

      // Store model reference
      window.avatarModel = model;
      scene.add(model);
      console.log("🎭 Character model added to scene with T-pose correction & SALSA setup");
    },
    (progress) => {
      const percent = Math.round((progress.loaded / progress.total) * 100);
      console.log(`📦 Model loading: ${percent}%`);
    },
    (error) => {
      console.error("❌ GLB Loader Error:", error);
      console.warn("Creating fallback 3D object...");
      
      // Fallback: Create a glowing ethereal orb
      const geometry = new THREE.IcosahedronGeometry(0.8, 4);
      const material = new THREE.MeshPhongMaterial({
        color: 0x9b8ec4,
        emissive: 0x6c5eaa,
        emissiveIntensity: 0.3,
        wireframe: false,
        transparent: true,
        opacity: 0.85,
      });
      const fallbackMesh = new THREE.Mesh(geometry, material);
      fallbackMesh.position.set(0, 1.2, 0);
      scene.add(fallbackMesh);
      
      // Add subtle rotation to fallback
      function rotateFallback() {
        requestAnimationFrame(rotateFallback);
        fallbackMesh.rotation.y += 0.003;
        fallbackMesh.rotation.x += 0.001;
      }
      rotateFallback();
      
      console.log("✨ Fallback object created (ethereal orb)");
    }
  );

  // Handle Resize
  window.addEventListener('resize', () => {
    if (!container) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });

  // Render Loop — Procedural SALSA Lip Sync + Living Idle Breathing & Sway
  function animate() {
    requestAnimationFrame(animate);
    const delta = clock.getDelta();
    const elapsedTime = clock.getElapsedTime();

    if (mixer) mixer.update(delta);

    // Living Avatar Procedural Animations (when 3D GLB is active)
    if (window.avatarModel) {
      // 1. Natural Breathing (Subtle Y vertical float)
      window.avatarModel.position.y = Math.sin(elapsedTime * 1.5) * 0.012;

      // 2. Spine Breathing Sway
      if (window.spineBone) {
        window.spineBone.rotation.x = Math.sin(elapsedTime * 1.5) * 0.015;
      }

      // 3. Subtle Head Sway (when not actively speaking)
      if (window.headBone && (!audio || audio.paused)) {
        const base = window.headBoneBaseRotationY || 0;
        window.headBone.rotation.y = base + Math.sin(elapsedTime * 0.7) * 0.025;
      }

      // 4. Procedural Arm Micro Sway
      if (window.leftArmBone) {
        window.leftArmBone.rotation.x = Math.sin(elapsedTime * 1.2) * 0.015;
      }
      if (window.rightArmBone) {
        window.rightArmBone.rotation.x = -Math.sin(elapsedTime * 1.2) * 0.015;
      }
    }

    renderer.render(scene, camera);
  }
  animate();
}

/* ═══════════════════════════════════════════════════
   TRUST & PROVENANCE LAYER INTEGRATION
   ═══════════════════════════════════════════════════ */
const trustToggleBtn = document.getElementById("trust-toggle");
const trustDrawer = document.getElementById("trust-drawer");
const closeTrustBtn = document.getElementById("close-trust-btn");

const trustBlockchainStatus = document.getElementById("trust-blockchain-status");
const trustConsentStatus = document.getElementById("trust-consent-status");
const trustPersonaStatus = document.getElementById("trust-persona-status");
const trustMemoryStatus = document.getElementById("trust-memory-status");
const trustResponseStatus = document.getElementById("trust-response-status");

const trustContractAddress = document.getElementById("trust-contract-address");
const trustLatestTx = document.getElementById("trust-latest-tx");
const trustLastCheck = document.getElementById("trust-last-check");

const btnVerifyIntegrity = document.getElementById("btn-verify-integrity");
const btnVerifyConsent = document.getElementById("btn-verify-consent");
const btnViewAudit = document.getElementById("btn-view-audit");

const auditTrailBox = document.getElementById("audit-trail-box");
const auditEntries = document.getElementById("audit-entries");

// Open and Close Drawer
if (trustToggleBtn && trustDrawer) {
  trustToggleBtn.addEventListener("click", () => {
    trustDrawer.classList.toggle("show");
    if (trustDrawer.classList.contains("show")) {
      updateBlockchainStatus();
    }
  });
}
if (closeTrustBtn && trustDrawer) {
  closeTrustBtn.addEventListener("click", () => {
    trustDrawer.classList.remove("show");
  });
}

async function updateBlockchainStatus() {
  if (!trustBlockchainStatus) return;
  try {
    const res = await fetch(`${SERVER}/blockchain/status`);
    if (!res.ok) throw new Error("Offline");
    const data = await res.json();
    
    if (data.connected) {
      trustBlockchainStatus.textContent = "🟢 CONNECTED";
      trustBlockchainStatus.className = "status-val status-verified";
      trustContractAddress.textContent = data.contract_address;
      trustContractAddress.title = data.contract_address;
      
      // Update status of components based on state
      trustPersonaStatus.textContent = "✓ VERIFIED";
      trustPersonaStatus.className = "status-val status-verified";
      
      // Auto verify consent
      verifyConsentOnChain(false);
    } else {
      setBlockchainOffline();
    }
  } catch (err) {
    setBlockchainOffline();
  }
  if (trustLastCheck) {
    trustLastCheck.textContent = new Date().toLocaleString();
  }
}

function setBlockchainOffline() {
  if (trustBlockchainStatus) {
    trustBlockchainStatus.textContent = "⚠️ OFFLINE";
    trustBlockchainStatus.className = "status-val status-failed";
  }
  if (trustContractAddress) trustContractAddress.textContent = "N/A";
  
  if (trustConsentStatus) {
    trustConsentStatus.textContent = "⚠️ UNKNOWN";
    trustConsentStatus.className = "status-val status-unknown";
  }
  if (trustPersonaStatus) {
    trustPersonaStatus.textContent = "⚠️ UNKNOWN";
    trustPersonaStatus.className = "status-val status-unknown";
  }
  if (trustMemoryStatus) {
    trustMemoryStatus.textContent = "⚠️ UNKNOWN";
    trustMemoryStatus.className = "status-val status-unknown";
  }
  if (trustResponseStatus) {
    trustResponseStatus.textContent = "⚠️ UNKNOWN";
    trustResponseStatus.className = "status-val status-unknown";
  }
}

async function verifyConsentOnChain(showToasts = true) {
  const personaName = getPersonaName();
  const userName = getUserName();
  
  try {
    const res = await fetch(`${SERVER}/blockchain/status`);
    const statusData = await res.json();
    if (!statusData.connected) {
      if (showToasts) showToast("Blockchain network is currently offline.");
      return;
    }
    
    const response = await fetch(`${SERVER}/blockchain/audit`);
    const auditLog = await response.json();
    
    const hasConsent = auditLog.some(entry => 
      entry.event_type === "CONSENT_GRANTED" && 
      (entry.status === "VERIFIED" || entry.status === "success") && 
      entry.details && 
      entry.details.persona_name === personaName && 
      entry.details.user_name === userName
    );
    
    const isRevoked = auditLog.some(entry =>
      entry.event_type === "CONSENT_REVOKED" &&
      (entry.status === "VERIFIED" || entry.status === "success") &&
      entry.details &&
      entry.details.persona_name === personaName &&
      entry.details.user_name === userName
    );
    
    if (hasConsent && !isRevoked) {
      if (trustConsentStatus) {
        trustConsentStatus.textContent = "✓ VERIFIED";
        trustConsentStatus.className = "status-val status-verified";
      }
      
      const lastConsentTx = [...auditLog].reverse().find(entry => 
        entry.event_type === "CONSENT_GRANTED" && 
        entry.details && 
        entry.details.persona_name === personaName && 
        entry.details.user_name === userName
      );
      if (lastConsentTx && trustLatestTx) {
        trustLatestTx.textContent = lastConsentTx.tx_hash;
        trustLatestTx.title = lastConsentTx.tx_hash;
      }
      
      if (showToasts) showToast("✓ Consent provenance verified on-chain!");
    } else if (isRevoked) {
      if (trustConsentStatus) {
        trustConsentStatus.textContent = "❌ REVOKED";
        trustConsentStatus.className = "status-val status-failed";
      }
      if (showToasts) showToast("⚠ Consent has been revoked on-chain.");
    } else {
      if (trustConsentStatus) {
        trustConsentStatus.textContent = "⚡ UNVERIFIED";
        trustConsentStatus.className = "status-val status-unknown";
      }
      if (showToasts) showToast("No on-chain consent record found. Please complete setup onboarding.");
    }
  } catch (err) {
    console.error("Verification error:", err);
    if (showToasts) showToast("Consent verification failed.");
  }
}

async function verifyMemoryIntegrityOnChain() {
  const personaName = getPersonaName();
  const userName = getUserName();
  
  if (trustMemoryStatus) {
    trustMemoryStatus.textContent = "⏳ VERIFYING...";
    trustMemoryStatus.className = "status-val status-unknown";
  }
  
  try {
    const res = await fetch(`${SERVER}/blockchain/verify-integrity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ persona_name: personaName, user_name: userName })
    });
    
    const data = await res.json();
    
    if (data.results.length === 0) {
      if (trustMemoryStatus) {
        trustMemoryStatus.textContent = "⚡ NO FACTS";
        trustMemoryStatus.className = "status-val status-unknown";
      }
      showToast("No memory facts stored locally to verify.");
      return;
    }
    
    if (data.all_intact) {
      if (trustMemoryStatus) {
        trustMemoryStatus.textContent = "✓ VERIFIED";
        trustMemoryStatus.className = "status-val status-verified";
      }
      if (trustResponseStatus) {
        trustResponseStatus.textContent = "✓ VERIFIED";
        trustResponseStatus.className = "status-val status-verified";
      }
      showToast("✓ All memory segments verified successfully. No tampering detected!");
    } else {
      if (trustMemoryStatus) {
        trustMemoryStatus.textContent = "⚠ TAMPERING DETECTED";
        trustMemoryStatus.className = "status-val status-failed";
      }
      if (trustResponseStatus) {
        trustResponseStatus.textContent = "⚠ UNTRUSTED";
        trustResponseStatus.className = "status-val status-failed";
      }
      showToast("⚠ MEMORY INTEGRITY FAILURE: Local memory hashes mismatch with blockchain records!");
    }
    
    const auditRes = await fetch(`${SERVER}/blockchain/audit`);
    const auditLog = await auditRes.json();
    const lastMemoryEntry = [...auditLog].reverse().find(entry => entry.event_type === "MEMORY_VERIFIED" || entry.event_type === "MEMORY_CREATED");
    if (lastMemoryEntry && trustLatestTx) {
      trustLatestTx.textContent = lastMemoryEntry.tx_hash || "N/A";
      trustLatestTx.title = lastMemoryEntry.tx_hash || "N/A";
    }
  } catch (err) {
    console.error(err);
    if (trustMemoryStatus) {
      trustMemoryStatus.textContent = "❌ ERROR";
      trustMemoryStatus.className = "status-val status-failed";
    }
    showToast("Memory integrity check failed.");
  }
}

async function renderAuditTrail() {
  try {
    const res = await fetch(`${SERVER}/blockchain/audit`);
    const logs = await res.json();
    
    if (!auditEntries) return;
    auditEntries.innerHTML = "";
    if (logs.length === 0) {
      auditEntries.innerHTML = `<div style="text-align:center;color:var(--text-muted);font-size:11px;padding:12px;">No audit logs recorded yet.</div>`;
    } else {
      [...logs].reverse().forEach(entry => {
        const item = document.createElement("div");
        item.className = "audit-entry";
        
        let statusClass = "status-unknown";
        if (entry.status === "VERIFIED" || entry.status === "success") statusClass = "status-verified";
        if (entry.status === "TAMPERING_DETECTED") statusClass = "status-failed";
        
        item.innerHTML = `
          <div class="audit-header">
            <span style="color:var(--accent-lavender);">${entry.event_type}</span>
            <span class="${statusClass}">${entry.status}</span>
          </div>
          <div class="audit-time">${entry.timestamp}</div>
          <div class="audit-hash">Hash: ${entry.hash}</div>
          <div class="audit-tx">Tx: ${entry.tx_hash || "N/A"}</div>
        `;
        auditEntries.appendChild(item);
      });
    }
    
    if (auditTrailBox) {
      auditTrailBox.style.display = "block";
      auditTrailBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  } catch (err) {
    showToast("Failed to retrieve audit trail.");
  }
}

// Bind Buttons
if (btnVerifyConsent) btnVerifyConsent.addEventListener("click", () => verifyConsentOnChain(true));
if (btnVerifyIntegrity) btnVerifyIntegrity.addEventListener("click", verifyMemoryIntegrityOnChain);
if (btnViewAudit) btnViewAudit.addEventListener("click", renderAuditTrail);

// Check blockchain status automatically on load
setTimeout(updateBlockchainStatus, 1500);

// Polling background loop to resolve PENDING blockchain response provenance registrations
setInterval(async () => {
  const pendingBadges = document.querySelectorAll(".provenance-badge.status-unknown");
  if (pendingBadges.length === 0) return;
  
  try {
    const res = await fetch(`${SERVER}/blockchain/audit`);
    if (!res.ok) return;
    const auditLogs = await res.json();
    
    pendingBadges.forEach(badge => {
      const idAttr = badge.getAttribute("id");
      if (!idAttr) return;
      const evId = idAttr.replace("prov-", "");
      
      const entry = auditLogs.find(log => log.event_id === evId);
      if (entry) {
        const textSpan = badge.querySelector(".badge-text");
        if (entry.status === "CONFIRMED" || entry.status === "success") {
          badge.className = "provenance-badge status-verified";
          if (textSpan) textSpan.textContent = "✓ Blockchain Verified";
          badge.title = `On-Chain Response Hash: ${badge.getAttribute("data-hash")}\nTx: ${entry.transaction_hash}\nBlock: ${entry.block_number}`;
          
          const historyIndex = chatHistory.findIndex(h => h.blockchainProvenance && h.blockchainProvenance.event_id === evId);
          if (historyIndex !== -1) {
            chatHistory[historyIndex].blockchainProvenance.status = "CONFIRMED";
            localStorage.setItem(HISTORY_KEY, JSON.stringify(chatHistory));
          }
        } else if (entry.status === "FAILED") {
          badge.className = "provenance-badge status-failed";
          if (textSpan) textSpan.textContent = "❌ Verification Failed";
          
          const historyIndex = chatHistory.findIndex(h => h.blockchainProvenance && h.blockchainProvenance.event_id === evId);
          if (historyIndex !== -1) {
            chatHistory[historyIndex].blockchainProvenance.status = "FAILED";
            localStorage.setItem(HISTORY_KEY, JSON.stringify(chatHistory));
          }
        }
      }
    });
  } catch (err) {
    console.error("Error polling transactions:", err);
  }
}, 3000);

window.addEventListener("DOMContentLoaded", initThreeJS);
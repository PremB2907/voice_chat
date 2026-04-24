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
    if (avatarView) {
      avatarView.style.transform = "scale(1)";
      avatarView.style.filter = "none";
    }
    return;
  }
  analyser.getByteFrequencyData(dataArray);
  const bars = document.querySelectorAll(".apb");
  let sum = 0;
  for (let i = 0; i < bars.length; i++) {
    const val = dataArray[i * 2 + 1] || 0;
    sum += val;
    const h = 4 + (val / 255) * 16;
    if (bars[i]) bars[i].style.height = h + "px";
  }
  
  // Avatar amplitude lip-sync (Option 1: Jaw mapping)
  const avg = sum / (bars.length || 1);
  const intensity = avg / 255;
  
  if (window.jawBone) {
    // Map intensity to jaw rotation (assuming X axis opens mouth down; might need adjustment based on rig)
    window.jawBone.rotation.x = window.jawBoneBaseRotation + (intensity * 0.35); // Max 0.35 radians drop
  } else if (window.headBone) {
    // If no jaw bone, bob the head slightly
    window.headBone.rotation.x = window.headBoneBaseRotation + (intensity * 0.15);
  } else if (avatarView) {
    const scale = 1 + intensity * 0.03;
    avatarView.style.transform = `scale(${scale})`;
    const glow = intensity * 15;
    if (glow > 2) {
      avatarView.style.filter = `drop-shadow(0px 0px ${glow}px rgba(253, 224, 0, 0.4))`;
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

  addMessage("Maitree", message, true);
  userInput.value = "";
  setLoading(true);

  try {
    const customContext = localStorage.getItem("customContext") || "";
    const mbti = localStorage.getItem("mbti") || "";
    const res = await fetch(`${SERVER}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, mbti, custom_context: customContext, generate_audio: isVoiceOn })
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();

    setLoading(false);
    const msgEl  = addMessage("Prem", data.reply, false);
    const bubble = msgEl.querySelector(".bubble");

    if (data.audio) {
      const audio = setupAudio(`${SERVER}/audio/${data.audio}`);
      audio.onplay   = () => { bubble.classList.add("playing");   showAudioPill(true);  };
      audio.onended  = () => { bubble.classList.remove("playing"); showAudioPill(false); };
      audio.onerror  = () => { bubble.classList.remove("playing"); showAudioPill(false); };

      audio.play().catch(() => {
        showToast("▶  TAP PREM'S MESSAGE TO PLAY");
        bubble.style.cursor = "pointer";
        bubble.onclick = () => { audio.play(); bubble.onclick = null; bubble.style.cursor = ""; };
      });
    }

  } catch (err) {
    setLoading(false);
    setServerStatus("offline", "Offline");
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

/* ═══ CLEAR ═══ */
clearBtn.addEventListener("click", () => {
  // Stop audio + clear persisted history
  try { globalAudio.pause(); } catch {}
  showAudioPill(false);
  chatHistory = [];
  localStorage.removeItem(HISTORY_KEY);
  document.querySelectorAll(".bubble.playing").forEach(b => b.classList.remove("playing"));

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
chatHistory.forEach(msg => addMessage(msg.sender, msg.text, msg.isUser, false));

/* ═══════════════════════════════════════════════════
   THREE.JS SETUP & FBX LOADER (3D Avatar)
═══════════════════════════════════════════════════ */
function initThreeJS() {
  const container = document.getElementById("three-canvas-container");
  if (!container) {
    console.error("❌ three-canvas-container not found!");
    return;
  }

  console.log("📐 Container dimensions:", container.clientWidth, "x", container.clientHeight);
  
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f0f0f);
  scene.fog = new THREE.FogExp2(0x0a0a0a, 0.02);

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

  // Lighting
  const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0);
  hemiLight.position.set(0, 20, 0);
  scene.add(hemiLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(0, 5, 5);
  scene.add(dirLight);

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
      
      // Find Jaw or Head bone for lip-sync
      model.traverse((child) => {
        if (child.isBone) {
          const name = child.name.toLowerCase();
          if ((name.includes("jaw") || name.includes("mouth")) && !window.jawBone) {
            window.jawBone = child;
            window.jawBoneBaseRotation = child.rotation.x;
            console.log("🦷 Found Jaw Bone:", child.name);
          }
          if (name.includes("head") && !window.headBone) {
            window.headBone = child;
            window.headBoneBaseRotation = child.rotation.x;
            console.log("👤 Found Head Bone:", child.name);
          }
        }
        if (child.isMesh) {
          child.castShadow = true;
          child.receiveShadow = true;
        }
      });

      scene.add(model);
      console.log("🎭 Character model added to scene");
    },
    (progress) => {
      const percent = Math.round((progress.loaded / progress.total) * 100);
      console.log(`📦 Model loading: ${percent}%`);
    },
    (error) => {
      console.error("❌ GLB Loader Error:", error);
      console.warn("Creating fallback 3D object...");
      
      // Fallback: Create a simple glowing sphere
      const geometry = new THREE.IcosahedronGeometry(1, 4);
      const material = new THREE.MeshPhongMaterial({
        color: 0xfdff00,
        emissive: 0xfdff00,
        emissiveIntensity: 0.3,
        wireframe: false
      });
      const fallbackMesh = new THREE.Mesh(geometry, material);
      scene.add(fallbackMesh);
      console.log("✨ Fallback object created (glowing sphere)");
    }
  );

  // Handle Resize
  window.addEventListener('resize', () => {
    if (!container) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });

  // Render Loop
  function animate() {
    requestAnimationFrame(animate);
    const delta = clock.getDelta();
    if (mixer) mixer.update(delta);
    renderer.render(scene, camera);
  }
  animate();
}

window.addEventListener("DOMContentLoaded", initThreeJS);
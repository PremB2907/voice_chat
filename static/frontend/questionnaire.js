const SERVER = window.location.origin;
const HISTORY_KEY = "un-miss-history";
const ratings = {};

// Build rating buttons
function buildRating(containerId, key) {
  const container = document.getElementById(containerId);
  for (let i = 1; i <= 10; i++) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "rating-btn";
    btn.textContent = i;
    btn.addEventListener("click", () => {
      container.querySelectorAll(".rating-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      ratings[key] = i;
    });
    container.appendChild(btn);
  }
}

buildRating("rating-emotion", "emotional_accuracy");
buildRating("rating-coherence", "conversational_coherence");
buildRating("rating-memory", "memory_recall");
buildRating("rating-voice", "voice_quality");
buildRating("rating-lipsync", "lip_sync_quality");
buildRating("rating-overall", "overall_experience");

// Load chat history from localStorage
function loadChatHistory() {
  const logEl = document.getElementById("chat-log");
  let history = [];
  try {
    history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    if (!Array.isArray(history)) history = [];
  } catch { history = []; }

  if (history.length === 0) {
    logEl.innerHTML = '<div style="color:#555; font-size:12px;">No conversation data found. Chat with Prem first!</div>';
    document.getElementById("stat-total").textContent = "0";
    document.getElementById("stat-user").textContent = "0";
    document.getElementById("stat-ai").textContent = "0";
    return;
  }

  let userCount = 0, aiCount = 0;
  logEl.innerHTML = "";
  history.forEach(msg => {
    if (msg.isUser) userCount++; else aiCount++;
    const entry = document.createElement("div");
    entry.className = "log-entry";
    entry.innerHTML = `<div class="log-sender ${msg.isUser ? 'user' : 'ai'}">${msg.sender}</div><div>${msg.text}</div>`;
    logEl.appendChild(entry);
  });

  document.getElementById("stat-total").textContent = history.length;
  document.getElementById("stat-user").textContent = userCount;
  document.getElementById("stat-ai").textContent = aiCount;
}

// Load knowledge base from server
async function loadKnowledgeBase() {
  const kbEl = document.getElementById("kb-container");
  const statKb = document.getElementById("stat-kb");
  try {
    const res = await fetch(`${SERVER}/chat-export`);
    if (!res.ok) throw new Error("Failed");
    const data = await res.json();
    const facts = data.knowledge_base || [];
    statKb.textContent = facts.length;

    if (facts.length === 0) {
      kbEl.innerHTML = '<div style="color:#555; font-size:12px;">No knowledge base entries found.</div>';
      return;
    }

    let html = '<ul class="kb-list">';
    facts.forEach(f => {
      const cat = f.category || "general";
      const detail = f.detail || f.text || JSON.stringify(f);
      html += `<li class="kb-item"><span class="kb-cat">[${cat.toUpperCase()}]</span> ${detail}</li>`;
    });
    html += '</ul>';
    kbEl.innerHTML = html;
  } catch (e) {
    kbEl.innerHTML = '<div style="color:#555; font-size:12px;">Could not load knowledge base. Is the server running?</div>';
    statKb.textContent = "--";
  }
}

// Submit form
document.getElementById("q-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("submit-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="loading-spinner"></span> SUBMITTING...';

  let history = [];
  try { history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); } catch {}

  const payload = {
    evaluator: document.getElementById("evalName").value,
    ratings: ratings,
    comments: document.getElementById("comments").value,
    total_messages: history.length,
    chat_log: history,
    timestamp: new Date().toISOString()
  };

  try {
    const res = await fetch(`${SERVER}/submit-questionnaire`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const toast = document.getElementById("toast");
      toast.textContent = "Evaluation submitted successfully!";
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 3500);
      document.getElementById("q-form").reset();
      document.querySelectorAll(".rating-btn.active").forEach(b => b.classList.remove("active"));
    }
  } catch (err) {
    alert("Error: " + err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = "SUBMIT EVALUATION";
  }
});

// Init
loadChatHistory();
loadKnowledgeBase();

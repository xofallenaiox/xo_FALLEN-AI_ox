const API = "http://127.0.0.1:8000";
const $ = (selector) => document.querySelector(selector);

const messages = $("#messages");
const input = $("#promptInput");
const coreState = $("#coreState");
const voiceLabel = $("#voiceLabel");
const systemStatus = $("#systemStatus");
const activityLog = $("#activityLog");
const coreStage = $("#coreStage");

const wave = $("#wave");
for (let i = 0; i < 28; i++) {
  const bar = document.createElement("i");
  bar.style.height = `${5 + Math.random() * 17}px`;
  wave.appendChild(bar);
}
const waveBars = [...wave.children];

function setState(state, label = state) {
  coreState.textContent = state;
  voiceLabel.textContent = label;
  coreStage.dataset.state = state;

  const colors = {
    IDLE: "#5f8f9a",
    LISTENING: "#6cf7ff",
    THINKING: "#a7a1ff",
    SPEAKING: "#79ffc4",
    ERROR: "#ff9f9f"
  };
  coreState.style.color = colors[state] || colors.IDLE;
}

function addMessage(text, role = "ai") {
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.innerHTML = `<div class="message-label">${role === "user" ? "YOU" : "FALLEN"}</div><div class="message-body"></div>`;
  el.querySelector(".message-body").textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
  return el;
}

function logActivity(text) {
  const line = document.createElement("div");
  line.textContent = text;
  activityLog.prepend(line);
  while (activityLog.children.length > 6) activityLog.lastElementChild.remove();
}

function updateClock() {
  $("#clock").textContent = new Date().toLocaleTimeString([], { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

function animateWave(active = false) {
  waveBars.forEach((bar, index) => {
    const base = active ? 5 + Math.random() * 19 : 4 + Math.random() * 5;
    bar.style.height = `${base + Math.abs(Math.sin(Date.now() / 180 + index)) * (active ? 10 : 2)}px`;
  });
}
setInterval(() => animateWave(coreState.textContent !== "IDLE"), 90);

function animateMetric(name, value) {
  const valueEl = $(`#${name}Value`);
  const barEl = $(`#${name}Bar`);
  if (valueEl) valueEl.textContent = `${Math.round(value)}%`;
  if (barEl) barEl.style.width = `${Math.max(3, Math.min(100, value))}%`;
}

async function refreshTelemetry() {
  try {
    const response = await fetch(`${API}/health`, { cache: "no-store" });
    if (!response.ok) throw new Error("offline");
    systemStatus.textContent = "SYSTEM ONLINE";
  } catch {
    systemStatus.textContent = "LOCAL UI MODE";
  }

  // Frontend-safe animated placeholders until the backend exposes telemetry.
  animateMetric("cpu", 28 + Math.random() * 48);
  animateMetric("mem", 38 + Math.random() * 22);
  animateMetric("gpu", 22 + Math.random() * 55);
  $("#netBar").style.width = `${80 + Math.random() * 19}%`;
}
setInterval(refreshTelemetry, 1200);
refreshTelemetry();

async function sendMessage(message) {
  addMessage(message, "user");
  input.value = "";
  setState("THINKING", "PROCESSING");
  logActivity("AI // processing command");
  const thinking = addMessage("Thinking…", "ai");

  try {
    const response = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed");

    setState("SPEAKING", "RESPONDING");
    logActivity("AI // response received");
    thinking.querySelector(".message-body").textContent = data.reply;
    setTimeout(() => setState("IDLE", "READY"), 1300);
  } catch (error) {
    setState("ERROR", "ERROR");
    logActivity(`ERR // ${error.message}`);
    thinking.querySelector(".message-body").textContent = `Connection error: ${error.message}`;
    setTimeout(() => setState("IDLE", "READY"), 1700);
  }
}

$("#chatForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (message) sendMessage(message);
});

$("#listenBtn").addEventListener("click", () => {
  if (!("SpeechRecognition" in window || "webkitSpeechRecognition" in window)) {
    addMessage("Voice recognition is not available in this browser. Use Chrome or Edge on Windows.", "ai");
    setState("ERROR", "VOICE N/A");
    setTimeout(() => setState("IDLE", "READY"), 1300);
    return;
  }

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new Recognition();
  recognition.lang = navigator.language || "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  setState("LISTENING", "LISTENING");
  logActivity("VOICE // microphone active");

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript.trim();
    input.value = transcript;
    setState("THINKING", "PROCESSING");
    sendMessage(transcript);
  };
  recognition.onerror = () => {
    setState("ERROR", "VOICE ERROR");
    setTimeout(() => setState("IDLE", "READY"), 1200);
  };
  recognition.onend = () => {
    if (coreState.textContent === "LISTENING") setState("IDLE", "READY");
  };
  recognition.start();
});

$("#thinkBtn").addEventListener("click", () => {
  setState("THINKING", "THINKING");
  logActivity("CORE // neural cycle active");
  setTimeout(() => setState("IDLE", "READY"), 1800);
});

$("#stopBtn").addEventListener("click", () => {
  setState("IDLE", "READY");
  logActivity("SYS // operation stopped");
});

for (const button of document.querySelectorAll(".nav-btn")) {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
    button.classList.add("active");
    logActivity(`NAV // ${button.dataset.mode.toUpperCase()} module selected`);
  });
}

addMessage("System initialized. Neural link online. How can I assist?", "ai");
setState("IDLE", "READY");

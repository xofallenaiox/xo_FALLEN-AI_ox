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
  bar.style.height = "8px";
  wave.appendChild(bar);
}
const waveBars = [...wave.children];

let activeReader = null;
let abortController = null;

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
    const pulse = Math.abs(Math.sin(Date.now() / 170 + index * 0.7));
    const base = active ? 5 + pulse * 19 : 4 + pulse * 5;
    bar.style.height = `${base}px`;
  });
}
setInterval(() => animateWave(coreState.textContent !== "IDLE"), 70);

function setMetric(name, value) {
  const normalized = Math.max(0, Math.min(100, Number(value) || 0));
  const valueEl = $(`#${name}Value`);
  const barEl = $(`#${name}Bar`);
  if (valueEl) valueEl.textContent = `${Math.round(normalized)}%`;
  if (barEl) barEl.style.width = `${Math.max(3, normalized)}%`;
}

async function refreshTelemetry() {
  try {
    const response = await fetch(`${API}/telemetry`, { cache: "no-store" });
    if (!response.ok) throw new Error("telemetry offline");
    const data = await response.json();

    systemStatus.textContent = "SYSTEM ONLINE";
    setMetric("cpu", data.cpu);
    setMetric("mem", data.memory);

    if (typeof data.gpu === "number") {
      setMetric("gpu", data.gpu);
    } else {
      $("#gpuValue").textContent = "N/A";
      $("#gpuBar").style.width = "8%";
    }

    const rx = Number(data.network?.bytes_recv || 0);
    const tx = Number(data.network?.bytes_sent || 0);
    // Show a bounded activity meter based on cumulative network I/O.
    const networkActivity = Math.min(100, ((rx + tx) / (1024 * 1024 * 1024)) * 12);
    $("#netValue").textContent = "ONLINE";
    $("#netBar").style.width = `${Math.max(12, networkActivity)}%`;
  } catch {
    systemStatus.textContent = "LOCAL UI MODE";
    logActivity("NET // telemetry unavailable");
  }
}
setInterval(refreshTelemetry, 1200);
refreshTelemetry();

function updateStreamingText(element, text) {
  element.querySelector(".message-body").textContent = text;
  messages.scrollTop = messages.scrollHeight;
}

async function sendMessage(message) {
  addMessage(message, "user");
  input.value = "";
  setState("THINKING", "PROCESSING");
  logActivity("AI // request dispatched");
  const assistantMessage = addMessage("", "ai");
  abortController = new AbortController();

  try {
    const response = await fetch(`${API}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      signal: abortController.signal
    });

    if (!response.ok) {
      const fallback = await response.json().catch(() => ({}));
      throw new Error(fallback.detail || "Request failed");
    }

    if (!response.body) throw new Error("Streaming is unavailable");

    setState("SPEAKING", "RESPONDING");
    logActivity("AI // live response stream");

    activeReader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalText = "";

    while (true) {
      const { value, done } = await activeReader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (!payload || payload === "[DONE]") continue;
        try {
          const event = JSON.parse(payload);
          if (event.type === "delta" && event.text) {
            finalText += event.text;
            updateStreamingText(assistantMessage, finalText);
          } else if (event.type === "status" && event.label) {
            voiceLabel.textContent = event.label;
          } else if (event.type === "error") {
            throw new Error(event.message || "AI stream failed");
          }
        } catch (parseError) {
          if (parseError instanceof Error && /AI stream failed/.test(parseError.message)) throw parseError;
        }
      }
    }

    if (!finalText) updateStreamingText(assistantMessage, "No response received.");
    logActivity("AI // response complete");
    setTimeout(() => setState("IDLE", "READY"), 1000);
  } catch (error) {
    if (error.name === "AbortError") {
      logActivity("SYS // operation cancelled");
      setState("IDLE", "READY");
      return;
    }
    setState("ERROR", "ERROR");
    logActivity(`ERR // ${error.message}`);
    updateStreamingText(assistantMessage, `Connection error: ${error.message}`);
    setTimeout(() => setState("IDLE", "READY"), 1500);
  } finally {
    activeReader = null;
    abortController = null;
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
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.maxAlternatives = 1;
  setState("LISTENING", "LISTENING");
  logActivity("VOICE // microphone active");

  recognition.onresult = (event) => {
    const latest = event.results[event.results.length - 1][0].transcript.trim();
    input.value = latest;
    if (event.results[event.results.length - 1].isFinal && latest) {
      setState("THINKING", "PROCESSING");
      sendMessage(latest);
    }
  };
  recognition.onerror = (event) => {
    setState("ERROR", "VOICE ERROR");
    logActivity(`VOICE // ${event.error || "recognition error"}`);
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
  if (abortController) abortController.abort();
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

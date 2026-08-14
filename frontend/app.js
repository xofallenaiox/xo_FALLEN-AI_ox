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

let abortController = null;
let latestTelemetry = { cpu: 0, memory: 0, gpu: 0, network: null };
let interactionState = "idle";
let stateTimer = null;

function setState(state, label = state) {
  interactionState = state.toLowerCase();
  coreState.textContent = state;
  voiceLabel.textContent = label;
  coreStage.dataset.state = state;
  document.body.dataset.aiState = interactionState;

  const colors = {
    IDLE: "#5f8f9a",
    LISTENING: "#6cf7ff",
    THINKING: "#a7a1ff",
    SPEAKING: "#79ffc4",
    ERROR: "#ff9f9f"
  };
  coreState.style.color = colors[state] || colors.IDLE;
  if (state !== "IDLE") logActivity(`CORE // ${state.toLowerCase()} state`);
}

function scheduleIdle(ms = 900) {
  clearTimeout(stateTimer);
  stateTimer = setTimeout(() => setState("IDLE", "READY"), ms);
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

function getAnimationBoost() {
  const load = Math.max(latestTelemetry.cpu || 0, latestTelemetry.gpu || 0);
  const stateBoost = interactionState === "thinking" ? 1.8 : interactionState === "speaking" ? 1.45 : interactionState === "listening" ? 1.65 : 1;
  return Math.min(3.2, 1 + load / 100 * 1.15) * stateBoost;
}

function animateWave(active = false) {
  const boost = getAnimationBoost();
  waveBars.forEach((bar, index) => {
    const pulse = Math.abs(Math.sin(Date.now() / (170 / Math.max(1, boost)) + index * 0.7));
    const amplitude = active ? 18 * boost : 5 + boost;
    const base = active ? 5 + pulse * amplitude : 4 + pulse * 5;
    bar.style.height = `${Math.min(30, base)}px`;
  });
}
setInterval(() => animateWave(interactionState !== "idle"), 70);

function animateMetric(name, value, label = null) {
  const valueEl = $(`#${name}Value`);
  const barEl = $(`#${name}Bar`);
  if (valueEl && value != null) valueEl.textContent = label || `${Math.round(value)}%`;
  if (barEl && value != null) barEl.style.width = `${Math.max(3, Math.min(100, value))}%`;
}

async function refreshTelemetry() {
  try {
    const response = await fetch(`${API}/telemetry`, { cache: "no-store" });
    if (!response.ok) throw new Error("telemetry unavailable");
    const data = await response.json();
    latestTelemetry = {
      cpu: Number(data.cpu) || 0,
      memory: Number(data.memory) || 0,
      gpu: Number(data.gpu) || 0,
      network: data.network || null,
    };

    systemStatus.textContent = "SYSTEM ONLINE";
    animateMetric("cpu", latestTelemetry.cpu);
    animateMetric("mem", latestTelemetry.memory);
    animateMetric("gpu", latestTelemetry.gpu);

    if (latestTelemetry.network) {
      const sent = Number(latestTelemetry.network.bytes_sent || 0);
      const recv = Number(latestTelemetry.network.bytes_recv || 0);
      const net = Math.min(100, ((sent + recv) / (1024 * 1024 * 5)) * 100);
      animateMetric("net", net, "ONLINE");
    } else {
      animateMetric("net", 0, "N/A");
    }

    const load = Math.max(latestTelemetry.cpu, latestTelemetry.gpu);
    const intensity = Math.min(1.7, 0.8 + load * 0.007);
    document.documentElement.style.setProperty("--core-intensity", intensity.toFixed(2));
    document.documentElement.style.setProperty("--core-speed", `${Math.max(3.2, 9 - load * 0.045)}s`);
  } catch {
    systemStatus.textContent = "LOCAL UI MODE";
  }
}
setInterval(refreshTelemetry, 900);
refreshTelemetry();

function updateStreamingText(element, text) {
  element.querySelector(".message-body").textContent = text;
  messages.scrollTop = messages.scrollHeight;
}

async function speakResponse(text) {
  if (!text.trim()) return;
  try {
    setState("SPEAKING", "SPEAKING");
    logActivity("VOICE // starting FALLEN speech");
    const response = await fetch(`${API}/voice/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.ok === false) {
      throw new Error(result.message || result.status || "Voice playback failed");
    }
    logActivity("VOICE // FALLEN speech active");
    scheduleIdle(Math.max(1400, Math.min(7000, text.length * 48)));
  } catch (error) {
    logActivity(`VOICE // ${error.message}`);
    scheduleIdle(900);
  }
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

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalText = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (!payload || payload === "[DONE]") continue;
        const event = JSON.parse(payload);
        if (event.type === "delta" && event.text) {
          finalText += event.text;
          updateStreamingText(assistantMessage, finalText);
        } else if (event.type === "error") {
          throw new Error(event.message || "Stream error");
        }
      }
    }

    if (!finalText) {
      updateStreamingText(assistantMessage, "No response received.");
      scheduleIdle();
    } else {
      await speakResponse(finalText);
    }
    logActivity("AI // response complete");
  } catch (error) {
    if (error.name === "AbortError") {
      logActivity("SYS // operation cancelled");
      setState("IDLE", "READY");
      return;
    }
    setState("ERROR", "ERROR");
    logActivity(`ERR // ${error.message}`);
    updateStreamingText(assistantMessage, `Connection error: ${error.message}`);
    scheduleIdle(1500);
  } finally {
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
    scheduleIdle(1300);
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
    const result = event.results[event.results.length - 1];
    const latest = result[0].transcript.trim();
    input.value = latest;
    if (result.isFinal && latest) {
      setState("THINKING", "PROCESSING");
      sendMessage(latest);
    }
  };
  recognition.onerror = (event) => {
    setState("ERROR", "VOICE ERROR");
    logActivity(`VOICE // ${event.error || "recognition error"}`);
    scheduleIdle(1200);
  };
  recognition.onend = () => {
    if (interactionState === "listening") setState("IDLE", "READY");
  };
  recognition.start();
});

$("#thinkBtn").addEventListener("click", () => {
  setState("THINKING", "THINKING");
  logActivity("CORE // neural cycle active");
  scheduleIdle(1800);
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

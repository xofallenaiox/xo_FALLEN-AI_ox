const API = (window.FALLEN_API_URL || (window.location.port === "5500" ? "http://127.0.0.1:8000" : window.location.origin)).replace(/\/$/, "");
const $ = (selector) => document.querySelector(selector);

const messages = $("#messages");
const input = $("#promptInput");
const sendButton = $("#sendBtn");
const coreState = $("#coreState");
const voiceLabel = $("#voiceLabel");
const systemStatus = $("#systemStatus");
const activityLog = $("#activityLog");
const coreStage = $("#coreStage");
const wave = $("#wave");
const agentStatus = $("#agentStatus");
const neuralText = $("#neuralText");
const neuralProgress = $("#neuralProgress");

window.fallenAuthenticated = false;
window.fallenAgentId = null;
window.fallenCsrfToken = null;

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

window.fallenLog = (text) => {
  const line = document.createElement("div");
  line.textContent = text;
  activityLog.prepend(line);
  while (activityLog.children.length > 6) activityLog.lastElementChild.remove();
};

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
  if (state !== "IDLE") window.fallenLog(`CORE // ${state.toLowerCase()} state`);
}

function scheduleIdle(ms = 900) {
  clearTimeout(stateTimer);
  stateTimer = setTimeout(() => setState("IDLE", "READY"), ms);
}

function addMessage(text, role = "ai") {
  const el = document.createElement("div");
  el.className = `message ${role}`;

  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "YOU" : "FALLEN";

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = text;

  el.append(label, body);
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
  return el;
}

function updateClock() {
  $("#clock").textContent = new Date().toLocaleTimeString([], { hour12: false });
}

setInterval(updateClock, 1000);
updateClock();

function getAnimationBoost() {
  const load = Math.max(latestTelemetry.cpu || 0, latestTelemetry.gpu || 0);
  const stateBoost =
    interactionState === "thinking" ? 1.8 :
    interactionState === "speaking" ? 1.45 :
    interactionState === "listening" ? 1.65 : 1;

  return Math.min(3.2, 1 + load / 100 * 1.15) * stateBoost;
}

function animateWave(active = false) {
  const boost = getAnimationBoost();
  waveBars.forEach((bar, index) => {
    const pulse = Math.abs(
      Math.sin(Date.now() / (170 / Math.max(1, boost)) + index * 0.7)
    );
    const amplitude = active ? 18 * boost : 5 + boost;
    const base = active ? 5 + pulse * amplitude : 4 + pulse * 5;
    bar.style.height = `${Math.min(30, base)}px`;
  });
}

setInterval(() => animateWave(interactionState !== "idle"), 70);

function animateMetric(name, value, label = null) {
  const valueEl = $(`#${name}Value`);
  const barEl = $(`#${name}Bar`);

  if (valueEl && value != null) {
    valueEl.textContent = label || `${Math.round(value)}%`;
  }
  if (barEl && value != null) {
    barEl.style.width = `${Math.max(3, Math.min(100, value))}%`;
  }
}

async function authenticate() {
  if (window.fallenAuthenticated) return true;

  const token = window.prompt("Enter FALLEN_API_TOKEN:");
  if (!token) throw new Error("Authentication token is required.");

  const response = await fetch(`${API}/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ token: token.trim() })
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || "Authentication failed.");
  }

  window.fallenCsrfToken = body.csrf_token || null;
  window.fallenAuthenticated = true;
  window.fallenLog("SEC // authenticated session established");
  return true;
}

window.fallenFetch = async (path, options = {}) => {
  await authenticate();

  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && window.fallenCsrfToken) {
    headers.set("X-FALLEN-CSRF", window.fallenCsrfToken);
  }

  const response = await fetch(`${API}${path}`, {
    ...options,
    headers,
    credentials: "include"
  });

  if (response.status === 401) {
    window.fallenAuthenticated = false;
    window.fallenCsrfToken = null;
    throw new Error("Authentication expired.");
  }

  if (response.status === 403 && window.fallenAuthenticated) {
    window.fallenAuthenticated = false;
    window.fallenCsrfToken = null;
    throw new Error("Security validation failed. Please authenticate again.");
  }

  return response;
};

async function loadAgent() {
  try {
    const response = await window.fallenFetch("/agents", { cache: "no-store" });
    if (!response.ok) throw new Error("agent lookup failed");

    const agents = await response.json();
    const online = agents.find((agent) => agent.online);

    if (!online) {
      window.fallenAgentId = null;
      agentStatus.textContent = "OFFLINE";
      neuralText.textContent = "NO AGENT";
      neuralProgress.style.width = "35%";
      return;
    }

    window.fallenAgentId = online.agent_id;
    agentStatus.textContent = online.name.toUpperCase();
    neuralText.textContent = "AGENT ONLINE";
    neuralProgress.style.width = "100%";
    window.fallenLog(`AGT // ${online.name} connected`);
  } catch (error) {
    agentStatus.textContent = "AUTH REQUIRED";
    neuralText.textContent = "LOCKED";
    neuralProgress.style.width = "15%";
    throw error;
  }
}

async function initializeSession() {
  try {
    await authenticate();
    await loadAgent();

    systemStatus.textContent = "SYSTEM ONLINE";
    input.disabled = false;
    sendButton.disabled = false;

    const initial = messages.querySelector(".message-body");
    if (initial) {
      initial.textContent = window.fallenAgentId
        ? "Neural link online. Human confirmation gate armed."
        : "Cloud link online. Start the Windows Agent to enable local tools.";
    }
  } catch (error) {
    systemStatus.textContent = "AUTH REQUIRED";
    window.fallenLog(`SEC // ${error.message}`);
  }
}

async function refreshTelemetry() {
  if (!window.fallenAuthenticated) return;

  try {
    const response = await window.fallenFetch("/telemetry", { cache: "no-store" });
    if (!response.ok) throw new Error("telemetry unavailable");

    const data = await response.json();
    latestTelemetry = {
      cpu: Number(data.cpu) || 0,
      memory: Number(data.memory) || 0,
      gpu: Number(data.gpu) || 0,
      network: data.network || null
    };

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
    document.documentElement.style.setProperty(
      "--core-intensity",
      Math.min(1.7, 0.8 + load * 0.007).toFixed(2)
    );
    document.documentElement.style.setProperty(
      "--core-speed",
      `${Math.max(3.2, 9 - load * 0.045)}s`
    );
  } catch {
    systemStatus.textContent = "LINK DEGRADED";
  }
}

setInterval(refreshTelemetry, 2000);

async function speakResponse(text) {
  if (!text.trim()) return;

  try {
    setState("SPEAKING", "SPEAKING");
    window.fallenLog("VOICE // starting FALLEN speech");

    const response = await window.fallenFetch("/voice/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.ok === false) {
      throw new Error(result.status || "Voice playback failed");
    }

    window.fallenLog("VOICE // FALLEN speech active");
    scheduleIdle(Math.max(1400, Math.min(7000, text.length * 48)));
  } catch (error) {
    window.fallenLog(`VOICE // ${error.message}`);
    scheduleIdle(900);
  }
}

async function sendMessage(message) {
  if (!window.fallenAgentId) {
    addMessage("Windows Agent is offline. Start the agent before requesting local actions.", "ai");
    return;
  }

  addMessage(message, "user");
  input.value = "";
  setState("THINKING", "PROCESSING");
  window.fallenLog("AI // request dispatched");

  const assistantMessage = addMessage("", "ai");
  abortController = new AbortController();

  try {
    const response = await window.fallenFetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        agent_id: window.fallenAgentId
      }),
      signal: abortController.signal
    });

    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.detail || "Request failed");
    }

    const reply = body.reply || "No response received.";
    updateStreamingText(assistantMessage, reply);
    window.fallenLog("AI // response complete");

    await speakResponse(reply);
  } catch (error) {
    if (error.name === "AbortError") {
      window.fallenLog("SYS // operation cancelled");
      setState("IDLE", "READY");
      return;
    }

    setState("ERROR", "ERROR");
    window.fallenLog(`ERR // ${error.message}`);
    updateStreamingText(assistantMessage, `Connection error: ${error.message}`);
    scheduleIdle(1500);
  } finally {
    abortController = null;
  }
}

function updateStreamingText(element, text) {
  const body = element.querySelector(".message-body");
  body.textContent = text;
  messages.scrollTop = messages.scrollHeight;
}

$("#chatForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (message) sendMessage(message);
});

$("#listenBtn").addEventListener("click", () => {
  if (!("SpeechRecognition" in window || "webkitSpeechRecognition" in window)) {
    addMessage("Voice recognition is unavailable in this browser.", "ai");
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
  window.fallenLog("VOICE // microphone active");

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
    window.fallenLog(`VOICE // ${event.error || "recognition error"}`);
    scheduleIdle(1200);
  };

  recognition.onend = () => {
    if (interactionState === "listening") setState("IDLE", "READY");
  };

  recognition.start();
});

$("#thinkBtn").addEventListener("click", () => {
  setState("THINKING", "THINKING");
  window.fallenLog("CORE // neural cycle active");
  scheduleIdle(1800);
});

$("#stopBtn").addEventListener("click", () => {
  if (abortController) abortController.abort();
  setState("IDLE", "READY");
  window.fallenLog("SYS // operation stopped");
});

for (const button of document.querySelectorAll(".nav-btn")) {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn")
      .forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    window.fallenLog(`NAV // ${button.dataset.mode.toUpperCase()} module selected`);
  });
}

initializeSession();
setInterval(loadAgent, 5000);
setInterval(refreshTelemetry, 2000);

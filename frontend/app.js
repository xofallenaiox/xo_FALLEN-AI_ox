const API = "http://127.0.0.1:8000";
const form = document.querySelector("#form");
const input = document.querySelector("#message");
const chat = document.querySelector("#chat");
const status = document.querySelector("#status");

function addMessage(text, role) {
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.textContent = text;
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`);
    if (!r.ok) throw new Error();
    status.textContent = "ONLINE";
  } catch {
    status.textContent = "OFFLINE";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  addMessage(message, "user");
  input.value = "";
  addMessage("Thinking...", "assistant");
  const thinking = chat.lastElementChild;
  try {
    const r = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Request failed");
    thinking.textContent = data.reply;
  } catch (error) {
    thinking.textContent = `Error: ${error.message}`;
  }
});

addMessage("FALLEN AI initialized. How can I help?", "assistant");
checkHealth();

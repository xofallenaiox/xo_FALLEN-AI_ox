const confirmationState = {
  open: false,
  task: null,
  timer: null
};

function ensureConfirmationPanel() {
  if (document.querySelector("#fallenConfirmation")) return;

  const panel = document.createElement("section");
  panel.id = "fallenConfirmation";
  panel.className = "fallen-confirmation";
  panel.setAttribute("aria-hidden", "true");
  panel.innerHTML = `
    <div class="fallen-confirmation-backdrop"></div>
    <div class="fallen-confirmation-card" role="dialog" aria-modal="true"
         aria-labelledby="fallenConfirmationTitle">
      <div class="fallen-confirmation-eyebrow">FALLEN // PERMISSION GATE</div>
      <h2 id="fallenConfirmationTitle">Confirmation required</h2>
      <p id="fallenConfirmationDescription"></p>
      <div class="fallen-confirmation-grid">
        <div><span>OPERATION</span><strong id="fallenConfirmationTool">—</strong></div>
        <div><span>RISK</span><strong id="fallenConfirmationRisk">—</strong></div>
        <div><span>AGENT</span><strong id="fallenConfirmationAgent">—</strong></div>
        <div><span>EXPIRES</span><strong id="fallenConfirmationTimer">—</strong></div>
      </div>
      <div class="fallen-confirmation-arguments">
        <span>REQUESTED PARAMETERS</span>
        <pre id="fallenConfirmationArguments"></pre>
      </div>
      <div class="fallen-confirmation-actions">
        <button id="fallenConfirmationDeny" type="button">DENY</button>
        <button id="fallenConfirmationApprove" type="button">APPROVE</button>
      </div>
      <p id="fallenConfirmationStatus" class="fallen-confirmation-status" role="status"></p>
    </div>
  `;

  document.body.appendChild(panel);
  panel.querySelector("#fallenConfirmationDeny")
    .addEventListener("click", () => resolveConfirmation(false));
  panel.querySelector("#fallenConfirmationApprove")
    .addEventListener("click", () => resolveConfirmation(true));
}

function openConfirmation(task) {
  ensureConfirmationPanel();
  confirmationState.open = true;
  confirmationState.task = task;

  const panel = document.querySelector("#fallenConfirmation");
  const policy = task.policy || {};

  panel.querySelector("#fallenConfirmationDescription").textContent =
    policy.description || "FALLEN requested a protected operation.";
  panel.querySelector("#fallenConfirmationTool").textContent =
    task.tool || "UNKNOWN";
  panel.querySelector("#fallenConfirmationRisk").textContent =
    String(policy.risk || "UNKNOWN").toUpperCase();
  panel.querySelector("#fallenConfirmationAgent").textContent =
    task.agent_id || "UNKNOWN";
  panel.querySelector("#fallenConfirmationArguments").textContent =
    JSON.stringify(task.arguments || {}, null, 2);
  panel.querySelector("#fallenConfirmationStatus").textContent =
    "Review the operation before allowing it.";

  panel.setAttribute("aria-hidden", "false");
  panel.classList.add("open");
  panel.querySelector("#fallenConfirmationApprove").focus();

  updateConfirmationTimer();
  clearInterval(confirmationState.timer);
  confirmationState.timer = setInterval(updateConfirmationTimer, 1000);
}

function closeConfirmation() {
  const panel = document.querySelector("#fallenConfirmation");
  if (!panel) return;
  confirmationState.open = false;
  confirmationState.task = null;
  clearInterval(confirmationState.timer);
  confirmationState.timer = null;
  panel.classList.remove("open");
  panel.setAttribute("aria-hidden", "true");
}

function updateConfirmationTimer() {
  const task = confirmationState.task;
  if (!task) return;

  const remaining = Math.max(
    0,
    Math.ceil(120 - (Date.now() / 1000 - task.created_at))
  );
  const timer = document.querySelector("#fallenConfirmationTimer");
  if (timer) timer.textContent = `${remaining}s`;

  if (remaining <= 0) {
    const status = document.querySelector("#fallenConfirmationStatus");
    if (status) status.textContent = "This request expired.";
    setConfirmationButtonsDisabled(true);
    setTimeout(closeConfirmation, 500);
  }
}

function setConfirmationButtonsDisabled(disabled) {
  document.querySelector("#fallenConfirmationApprove").disabled = disabled;
  document.querySelector("#fallenConfirmationDeny").disabled = disabled;
}

async function resolveConfirmation(approved) {
  const task = confirmationState.task;
  if (!task) return;

  setConfirmationButtonsDisabled(true);

  try {
    const response = await window.fallenFetch(
      `/tasks/${encodeURIComponent(task.task_id)}/${approved ? "approve" : "cancel"}`,
      { method: "POST" }
    );
    const body = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(body.detail || "The request could not be updated.");
    }

    const status = document.querySelector("#fallenConfirmationStatus");
    status.textContent = approved
      ? "Approved. FALLEN may now execute this operation."
      : "Denied. The operation was cancelled.";

    setTimeout(closeConfirmation, 650);
    window.dispatchEvent(new CustomEvent("fallen:confirmation-resolved", {
      detail: { taskId: task.task_id, approved }
    }));
  } catch (error) {
    const status = document.querySelector("#fallenConfirmationStatus");
    status.textContent = error.message;
    setConfirmationButtonsDisabled(false);
  }
}

async function refreshPendingConfirmations() {
  if (!window.fallenAuthenticated) return;

  try {
    const response = await window.fallenFetch("/tasks/pending", {
      cache: "no-store"
    });

    if (!response.ok) return;
    const tasks = await response.json();

    if (!confirmationState.open && tasks.length > 0) {
      openConfirmation(tasks[0]);
      window.fallenLog("SEC // confirmation requested");
    }
  } catch {
    // The main HUD reports authentication/network failures.
  }
}

function initializeFallenConfirmations() {
  ensureConfirmationPanel();
  refreshPendingConfirmations();
  setInterval(refreshPendingConfirmations, 1000);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeFallenConfirmations);
} else {
  initializeFallenConfirmations();
}

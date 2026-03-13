const consoleOutput = document.getElementById("consoleOutput");
const configForm = document.getElementById("configForm");

function logResult(label, payload) {
  const rendered = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
  consoleOutput.textContent = `[${new Date().toLocaleTimeString()}] ${label}\n${rendered}\n\n${consoleOutput.textContent}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(typeof payload === "string" ? payload : JSON.stringify(payload));
  }
  return payload;
}

function setFormValues(values) {
  for (const [key, value] of Object.entries(values)) {
    const input = configForm.elements.namedItem(key);
    if (!input) continue;
    if (input.type === "checkbox") {
      input.checked = Boolean(value);
    } else {
      input.value = value ?? "";
    }
  }
}

function getFormValues() {
  const data = new FormData(configForm);
  return {
    llm_provider: data.get("llm_provider") || "deepseek",
    deepseek_api_key: data.get("deepseek_api_key") || "",
    deepseek_base_url: data.get("deepseek_base_url") || "",
    deepseek_model: data.get("deepseek_model") || "",
    openai_api_key: data.get("openai_api_key") || "",
    openai_base_url: data.get("openai_base_url") || "",
    openai_model: data.get("openai_model") || "",
    obsidian_mode: data.get("obsidian_mode") || "auto",
    obsidian_api_url: data.get("obsidian_api_url") || "",
    obsidian_api_key: data.get("obsidian_api_key") || "",
    obsidian_verify_ssl: configForm.elements.namedItem("obsidian_verify_ssl").checked,
    vault_root: data.get("vault_root") || "",
    sqlite_path: data.get("sqlite_path") || "",
    vector_store_path: data.get("vector_store_path") || "",
    log_level: data.get("log_level") || "INFO",
    dry_run: configForm.elements.namedItem("dry_run").checked,
    http_timeout_seconds: Number(data.get("http_timeout_seconds") || 30),
    http_retry_attempts: Number(data.get("http_retry_attempts") || 3),
    http_retry_backoff_seconds: Number(data.get("http_retry_backoff_seconds") || 0.5),
    review_folder: data.get("review_folder") || "90 Review",
    inbox_folder: data.get("inbox_folder") || "00 Inbox",
  };
}

function renderCards(target, items, formatter) {
  target.innerHTML = "";
  if (!items.length) {
    target.innerHTML = '<div class="result-card"><strong>No items</strong><small>The result set is empty.</small></div>';
    return;
  }
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "result-card";
    card.innerHTML = formatter(item);
    target.appendChild(card);
  }
}

async function loadRuntime() {
  const runtime = await api("/ui/api/runtime");
  document.getElementById("healthBadge").textContent = runtime.health;
  document.getElementById("envPath").textContent = runtime.env_path;
  setFormValues(runtime.settings);
  logResult("Runtime loaded", runtime);
}

async function loadReviews() {
  const payload = await api("/review/pending");
  renderCards(document.getElementById("reviewResults"), payload.items, (item) => `
    <strong>#${item.id} · ${item.proposal_type}</strong>
    <div>${item.source_note_path || ""}</div>
    <small>${item.target_note_path || "No target note"} · ${item.risk_level}</small>
  `);
  logResult("Review queue refreshed", payload);
}

async function runMaintenance(target) {
  const payload = await api(`/maintenance/${target}`);
  renderCards(document.getElementById("maintenanceResults"), payload.items, (item) => `
    <strong>${item.path}</strong>
    <div>${item.reason}</div>
    <small>score: ${item.score}</small>
  `);
  logResult(`Maintenance ${target}`, payload);
}

document.getElementById("saveConfig").addEventListener("click", async () => {
  const payload = await api("/ui/api/config", {
    method: "PUT",
    body: JSON.stringify(getFormValues()),
  });
  logResult("Config saved", payload);
  setFormValues(payload.settings);
});

document.getElementById("reloadRuntime").addEventListener("click", async () => {
  const payload = await api("/ui/api/reload", { method: "POST" });
  logResult("Runtime reloaded", payload);
  setFormValues(payload.settings);
});

document.getElementById("seedDemo").addEventListener("click", async () => {
  const payload = await api("/ui/api/seed-demo", { method: "POST" });
  logResult("Demo vault seeded", payload);
});

document.getElementById("reindex").addEventListener("click", async () => {
  const payload = await api("/ui/api/reindex", { method: "POST" });
  logResult("Vault reindexed", payload);
});

document.getElementById("runDigest").addEventListener("click", async () => {
  const payload = await api("/ui/api/weekly-digest", {
    method: "POST",
    body: JSON.stringify({ week_key: document.getElementById("weekKey").value }),
  });
  logResult("Weekly digest", payload);
});

document.getElementById("captureSubmit").addEventListener("click", async () => {
  const payload = await api("/capture/text", {
    method: "POST",
    body: JSON.stringify({
      title: document.getElementById("captureTitle").value,
      text: document.getElementById("captureText").value,
      source_ref: "ui",
    }),
  });
  logResult("Capture complete", payload);
});

document.getElementById("searchSubmit").addEventListener("click", async () => {
  const query = document.getElementById("searchQuery").value;
  const payload = await api(`/search?q=${encodeURIComponent(query)}`);
  renderCards(document.getElementById("searchResults"), payload.results, (item) => `
    <strong>${item.path}</strong>
    <div>${item.reason}</div>
    <small>score: ${item.score}</small>
  `);
  logResult("Search complete", payload);
});

document.getElementById("refreshReviews").addEventListener("click", loadReviews);
document.getElementById("refreshMaintenance").addEventListener("click", async () => {
  await runMaintenance("duplicates");
});

for (const button of document.querySelectorAll(".maintenance-trigger")) {
  button.addEventListener("click", async () => {
    await runMaintenance(button.dataset.target);
  });
}

document.getElementById("clearConsole").addEventListener("click", () => {
  consoleOutput.textContent = "Console cleared.";
});

loadRuntime()
  .then(loadReviews)
  .catch((error) => logResult("Startup error", error.message));

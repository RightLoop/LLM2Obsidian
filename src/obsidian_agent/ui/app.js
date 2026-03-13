const consoleOutput = document.getElementById("consoleOutput");
const configForm = document.getElementById("configForm");
const languageSelect = document.getElementById("languageSelect");

const translations = {
  "zh-CN": {
    documentTitle: "LLM2Obsidian 控制台",
    heroTitle: "控制台",
    heroLede: "配置模型与 Obsidian 连接，并在浏览器里直接运行核心工作流。",
    languageLabel: "语言",
    healthChecking: "检查中",
    envLoading: "正在加载运行时信息...",
    reloadRuntime: "重新加载运行时",
    runtimeConfig: "运行配置",
    saveConfig: "保存配置",
    llmProvider: "LLM 提供方",
    obsidianMode: "Obsidian 模式",
    vaultRoot: "Vault 根目录",
    sqlitePath: "SQLite 路径",
    vectorStorePath: "向量存储路径",
    obsidianApiUrl: "Obsidian API URL",
    obsidianApiKey: "Obsidian API Key",
    deepseekApiKey: "DeepSeek API Key",
    deepseekBaseUrl: "DeepSeek Base URL",
    deepseekModel: "DeepSeek 模型",
    openaiApiKey: "OpenAI API Key",
    openaiBaseUrl: "OpenAI Base URL",
    openaiModel: "OpenAI 模型",
    logLevel: "日志级别",
    reviewFolder: "Review 目录",
    inboxFolder: "Inbox 目录",
    httpTimeout: "HTTP 超时",
    retryAttempts: "重试次数",
    retryBackoff: "重试退避",
    verifySsl: "校验 SSL",
    dryRun: "Dry Run 预演",
    quickActions: "快捷操作",
    seedDemo: "生成演示知识库",
    reindex: "重建索引",
    weeklyDigest: "生成周报",
    captureText: "文本采集",
    captureTitlePlaceholder: "标题",
    captureTextPlaceholder: "粘贴一段笔记、文章摘录或想法...",
    captureToInbox: "采集到 Inbox",
    search: "搜索",
    searchPlaceholder: "搜索笔记",
    runSearch: "执行搜索",
    reviewQueue: "Review 队列",
    refresh: "刷新",
    maintenance: "维护",
    duplicates: "重复候选",
    orphans: "孤儿笔记",
    metadataIssues: "元数据问题",
    console: "控制台",
    clear: "清空",
    consoleWaiting: "等待操作...",
    noItemsTitle: "没有结果",
    noItemsBody: "当前结果集为空。",
    noTargetNote: "没有目标笔记",
    reviewConnector: "·",
    scoreLabel: "分数",
    runtimeLoaded: "已加载运行时",
    reviewQueueRefreshed: "已刷新 Review 队列",
    configSaved: "已保存配置",
    runtimeReloaded: "已重新加载运行时",
    demoVaultSeeded: "已生成演示知识库",
    vaultReindexed: "已重建索引",
    weeklyDigestDone: "周报任务结果",
    captureComplete: "采集完成",
    searchComplete: "搜索完成",
    startupError: "启动错误",
    consoleCleared: "控制台已清空。",
    maintenancePrefix: "维护结果",
  },
  en: {
    documentTitle: "LLM2Obsidian Control Panel",
    heroTitle: "Control Panel",
    heroLede: "Configure providers, connect Obsidian, and run the core workflows in the browser.",
    languageLabel: "Language",
    healthChecking: "checking",
    envLoading: "Loading runtime information...",
    reloadRuntime: "Reload Runtime",
    runtimeConfig: "Runtime Config",
    saveConfig: "Save Config",
    llmProvider: "LLM Provider",
    obsidianMode: "Obsidian Mode",
    vaultRoot: "Vault Root",
    sqlitePath: "SQLite Path",
    vectorStorePath: "Vector Store Path",
    obsidianApiUrl: "Obsidian API URL",
    obsidianApiKey: "Obsidian API Key",
    deepseekApiKey: "DeepSeek API Key",
    deepseekBaseUrl: "DeepSeek Base URL",
    deepseekModel: "DeepSeek Model",
    openaiApiKey: "OpenAI API Key",
    openaiBaseUrl: "OpenAI Base URL",
    openaiModel: "OpenAI Model",
    logLevel: "Log Level",
    reviewFolder: "Review Folder",
    inboxFolder: "Inbox Folder",
    httpTimeout: "HTTP Timeout",
    retryAttempts: "Retry Attempts",
    retryBackoff: "Retry Backoff",
    verifySsl: "Verify SSL",
    dryRun: "Dry Run",
    quickActions: "Quick Actions",
    seedDemo: "Seed Demo Vault",
    reindex: "Reindex Vault",
    weeklyDigest: "Weekly Digest",
    captureText: "Capture Text",
    captureTitlePlaceholder: "Title",
    captureTextPlaceholder: "Paste a note, article excerpt, or idea...",
    captureToInbox: "Capture to Inbox",
    search: "Search",
    searchPlaceholder: "Search notes",
    runSearch: "Run Search",
    reviewQueue: "Review Queue",
    refresh: "Refresh",
    maintenance: "Maintenance",
    duplicates: "Duplicates",
    orphans: "Orphans",
    metadataIssues: "Metadata Issues",
    console: "Console",
    clear: "Clear",
    consoleWaiting: "Waiting for action...",
    noItemsTitle: "No items",
    noItemsBody: "The result set is empty.",
    noTargetNote: "No target note",
    reviewConnector: "·",
    scoreLabel: "score",
    runtimeLoaded: "Runtime loaded",
    reviewQueueRefreshed: "Review queue refreshed",
    configSaved: "Config saved",
    runtimeReloaded: "Runtime reloaded",
    demoVaultSeeded: "Demo vault seeded",
    vaultReindexed: "Vault reindexed",
    weeklyDigestDone: "Weekly digest",
    captureComplete: "Capture complete",
    searchComplete: "Search complete",
    startupError: "Startup error",
    consoleCleared: "Console cleared.",
    maintenancePrefix: "Maintenance",
  },
};

function currentLanguage() {
  const stored = window.localStorage.getItem("ui-language");
  return stored && translations[stored] ? stored : "zh-CN";
}

function t(key) {
  return translations[currentLanguage()][key] || key;
}

function applyLanguage(lang) {
  window.localStorage.setItem("ui-language", lang);
  document.documentElement.lang = lang;
  document.title = translations[lang].documentTitle;
  languageSelect.value = lang;
  for (const node of document.querySelectorAll("[data-i18n]")) {
    node.textContent = translations[lang][node.dataset.i18n] || node.textContent;
  }
  for (const node of document.querySelectorAll("[data-i18n-placeholder]")) {
    node.placeholder =
      translations[lang][node.dataset.i18nPlaceholder] || node.placeholder;
  }
}

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
    target.innerHTML = `<div class="result-card"><strong>${t("noItemsTitle")}</strong><small>${t("noItemsBody")}</small></div>`;
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
  logResult(t("runtimeLoaded"), runtime);
}

async function loadReviews() {
  const payload = await api("/review/pending");
  renderCards(document.getElementById("reviewResults"), payload.items, (item) => `
    <strong>#${item.id} ${t("reviewConnector")} ${item.proposal_type}</strong>
    <div>${item.source_note_path || ""}</div>
    <small>${item.target_note_path || t("noTargetNote")} ${t("reviewConnector")} ${item.risk_level}</small>
  `);
  logResult(t("reviewQueueRefreshed"), payload);
}

async function runMaintenance(target) {
  const payload = await api(`/maintenance/${target}`);
  renderCards(document.getElementById("maintenanceResults"), payload.items, (item) => `
    <strong>${item.path}</strong>
    <div>${item.reason}</div>
    <small>${t("scoreLabel")}: ${item.score}</small>
  `);
  logResult(`${t("maintenancePrefix")} ${target}`, payload);
}

document.getElementById("saveConfig").addEventListener("click", async () => {
  const payload = await api("/ui/api/config", {
    method: "PUT",
    body: JSON.stringify(getFormValues()),
  });
  logResult(t("configSaved"), payload);
  setFormValues(payload.settings);
});

document.getElementById("reloadRuntime").addEventListener("click", async () => {
  const payload = await api("/ui/api/reload", { method: "POST" });
  logResult(t("runtimeReloaded"), payload);
  setFormValues(payload.settings);
});

document.getElementById("seedDemo").addEventListener("click", async () => {
  const payload = await api("/ui/api/seed-demo", { method: "POST" });
  logResult(t("demoVaultSeeded"), payload);
});

document.getElementById("reindex").addEventListener("click", async () => {
  const payload = await api("/ui/api/reindex", { method: "POST" });
  logResult(t("vaultReindexed"), payload);
});

document.getElementById("runDigest").addEventListener("click", async () => {
  const payload = await api("/ui/api/weekly-digest", {
    method: "POST",
    body: JSON.stringify({ week_key: document.getElementById("weekKey").value }),
  });
  logResult(t("weeklyDigestDone"), payload);
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
  logResult(t("captureComplete"), payload);
});

document.getElementById("searchSubmit").addEventListener("click", async () => {
  const query = document.getElementById("searchQuery").value;
  const payload = await api(`/search?q=${encodeURIComponent(query)}`);
  renderCards(document.getElementById("searchResults"), payload.results, (item) => `
    <strong>${item.path}</strong>
    <div>${item.reason}</div>
    <small>${t("scoreLabel")}: ${item.score}</small>
  `);
  logResult(t("searchComplete"), payload);
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
  consoleOutput.textContent = t("consoleCleared");
});

languageSelect.addEventListener("change", () => {
  applyLanguage(languageSelect.value);
});

applyLanguage(currentLanguage());

loadRuntime()
  .then(loadReviews)
  .catch((error) => logResult(t("startupError"), error.message));

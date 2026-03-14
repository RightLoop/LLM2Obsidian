const consoleOutput = document.getElementById("consoleOutput");
const configForm = document.getElementById("configForm");
const languageSelect = document.getElementById("languageSelect");
const adminTokenInput = document.getElementById("adminToken");

const translations = {
  "zh-CN": {
    documentTitle: "LLM2Obsidian 控制台",
    heroTitle: "控制台",
    heroLede: "配置模型和 Obsidian 连接，并在浏览器里直接运行核心工作流。",
    languageLabel: "语言",
    adminTokenPlaceholder: "输入 UI 管理 token",
    saveAdminToken: "保存 Token",
    uiAdminToken: "UI 管理 Token",
    healthChecking: "检查中",
    envLoading: "正在加载运行时信息...",
    reloadRuntime: "重新加载运行时",
    runtimeConfig: "运行配置",
    saveConfig: "保存配置",
    llmProvider: "LLM 提供方",
    embeddingsProvider: "Embedding 提供方",
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
    ollamaBaseUrl: "Ollama Base URL",
    ollamaChatModel: "Ollama Chat 模型",
    ollamaJsonModel: "Ollama JSON 模型",
    ollamaEmbeddingModel: "Ollama Embedding 模型",
    ollamaTimeout: "Ollama 超时",
    logLevel: "日志级别",
    reviewFolder: "Review 目录",
    inboxFolder: "Inbox 目录",
    smartNodesFolder: "Smart Nodes 目录",
    smartErrorsFolder: "Error Nodes 目录",
    httpTimeout: "HTTP 超时",
    retryAttempts: "重试次数",
    retryBackoff: "重试退避",
    verifySsl: "校验 SSL",
    dryRun: "Dry Run 预演",
    quickActions: "快捷操作",
    seedDemo: "生成示例知识库",
    reindex: "重建索引",
    weeklyDigest: "生成周报",
    captureText: "文本采集",
    captureTitlePlaceholder: "标题",
    captureTextPlaceholder: "粘贴一段笔记、文章摘录或想法...",
    captureToInbox: "采集到 Inbox",
    smartErrorCapture: "错题智能分析",
    smartTitlePlaceholder: "例如：把 sizeof 当成 strlen",
    smartPromptPlaceholder: "描述题目、错误结论和正确答案。",
    smartCodePlaceholder: "贴上相关的 C 代码。",
    smartAnalysisPlaceholder: "写下你当时的思路。",
    runSmartCapture: "生成 Error Node",
    nodePackPlaceholder: "输入 node_key，例如 error/sizeof-vs-strlen",
    runNodePack: "生成 Node Pack",
    runTeachPack: "生成 Teaching Pack",
    runRelink: "生成 Relink Review",
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
    scoreLabel: "分数",
    runtimeLoaded: "已加载运行时",
    reviewQueueRefreshed: "已刷新 Review 队列",
    configSaved: "已保存配置",
    runtimeReloaded: "已重新加载运行时",
    demoVaultSeeded: "已生成示例知识库",
    vaultReindexed: "已重建索引",
    weeklyDigestDone: "周报任务结果",
    captureComplete: "采集完成",
    searchComplete: "搜索完成",
    smartCaptureComplete: "错题分析完成",
    nodePackComplete: "Node Pack 已生成",
    teachPackComplete: "Teaching Pack 已生成",
    relinkComplete: "Relink Review 已生成",
    startupError: "启动错误",
    consoleCleared: "控制台已清空。",
    maintenancePrefix: "维护结果",
    tokenSaved: "已保存管理 token",
    tokenMissing: "请先输入 UI 管理 token。",
    unauthorized: "管理 token 缺失或无效。",
  },
  en: {
    documentTitle: "LLM2Obsidian Control Panel",
    heroTitle: "Control Panel",
    heroLede: "Configure providers, connect Obsidian, and run the core workflows in the browser.",
    languageLabel: "Language",
    adminTokenPlaceholder: "Enter the UI admin token",
    saveAdminToken: "Save Token",
    uiAdminToken: "UI Admin Token",
    healthChecking: "checking",
    envLoading: "Loading runtime information...",
    reloadRuntime: "Reload Runtime",
    runtimeConfig: "Runtime Config",
    saveConfig: "Save Config",
    llmProvider: "LLM Provider",
    embeddingsProvider: "Embeddings Provider",
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
    ollamaBaseUrl: "Ollama Base URL",
    ollamaChatModel: "Ollama Chat Model",
    ollamaJsonModel: "Ollama JSON Model",
    ollamaEmbeddingModel: "Ollama Embedding Model",
    ollamaTimeout: "Ollama Timeout",
    logLevel: "Log Level",
    reviewFolder: "Review Folder",
    inboxFolder: "Inbox Folder",
    smartNodesFolder: "Smart Nodes Folder",
    smartErrorsFolder: "Error Nodes Folder",
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
    smartErrorCapture: "Smart Error Capture",
    smartTitlePlaceholder: "Example: treating sizeof as strlen",
    smartPromptPlaceholder: "Describe the problem, the incorrect conclusion, and the correct answer.",
    smartCodePlaceholder: "Paste the relevant C code.",
    smartAnalysisPlaceholder: "Write down your original reasoning.",
    runSmartCapture: "Create Error Node",
    nodePackPlaceholder: "Enter a node_key such as error/sizeof-vs-strlen",
    runNodePack: "Build Node Pack",
    runTeachPack: "Build Teaching Pack",
    runRelink: "Build Relink Review",
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
    smartCaptureComplete: "Smart error capture complete",
    nodePackComplete: "Node pack generated",
    teachPackComplete: "Teaching pack generated",
    relinkComplete: "Relink review generated",
    startupError: "Startup error",
    consoleCleared: "Console cleared.",
    maintenancePrefix: "Maintenance",
    tokenSaved: "Admin token saved",
    tokenMissing: "Enter the UI admin token first.",
    unauthorized: "Missing or invalid admin token.",
  },
};

function currentLanguage() {
  const stored = window.localStorage.getItem("ui-language");
  return stored && translations[stored] ? stored : "zh-CN";
}

function adminToken() {
  return window.localStorage.getItem("ui-admin-token") || "";
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
    node.placeholder = translations[lang][node.dataset.i18nPlaceholder] || node.placeholder;
  }
}

function logResult(label, payload) {
  const rendered = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
  consoleOutput.textContent = `[${new Date().toLocaleTimeString()}] ${label}\n${rendered}\n\n${consoleOutput.textContent}`;
}

async function api(path, options = {}) {
  const token = adminToken();
  if (!token) {
    throw new Error(t("tokenMissing"));
  }
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Token": token,
      ...(options.headers || {}),
    },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    if (response.status === 401 || response.status === 503) {
      throw new Error(typeof payload === "string" ? payload : payload.detail || t("unauthorized"));
    }
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
    ui_admin_token: data.get("ui_admin_token") || "",
    llm_provider: data.get("llm_provider") || "deepseek",
    embeddings_provider: data.get("embeddings_provider") || "deterministic",
    deepseek_api_key: data.get("deepseek_api_key") || "",
    deepseek_base_url: data.get("deepseek_base_url") || "",
    deepseek_model: data.get("deepseek_model") || "",
    openai_api_key: data.get("openai_api_key") || "",
    openai_base_url: data.get("openai_base_url") || "",
    openai_model: data.get("openai_model") || "",
    ollama_base_url: data.get("ollama_base_url") || "",
    ollama_chat_model: data.get("ollama_chat_model") || "",
    ollama_json_model: data.get("ollama_json_model") || "",
    ollama_embedding_model: data.get("ollama_embedding_model") || "",
    ollama_timeout_seconds: Number(data.get("ollama_timeout_seconds") || 60),
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
    smart_nodes_folder: data.get("smart_nodes_folder") || "20 Smart",
    smart_errors_folder: data.get("smart_errors_folder") || "21 Errors",
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

function renderSmartResult(payload) {
  const target = document.getElementById("smartResults");
  const weaknesses = (payload.weaknesses || [])
    .map((item) => `<li>${item.name}: ${item.summary}</li>`)
    .join("");
  const relations = (((payload.pack || {}).edges) || [])
    .map((item) => `<li>${item.relation_type} -> ${item.to_node_key} (${item.confidence})</li>`)
    .join("");
  const teachingSections = (payload.sections || [])
    .map((item) => `<li><strong>${item.heading}</strong>: ${item.body}</li>`)
    .join("");
  const drills = (payload.drills || []).map((item) => `<li>${item}</li>`).join("");
  const preview = payload.action_preview
    ? `<small>dry-run: ${payload.action_preview.target_path}</small>`
    : `<small>${payload.node ? payload.node.note_path || "" : (payload.pack ? payload.pack.anchor.note_path || "" : "")}</small>`;
  const title = payload.error ? payload.error.title : (payload.title || (payload.pack ? payload.pack.anchor.title : ""));
  const summary = payload.error
    ? payload.error.summary
    : ((payload.pack && payload.pack.summary) || payload.overview || "");
  const secondary = payload.error
    ? payload.error.root_cause
    : (payload.overview || (payload.pack ? payload.pack.anchor.summary : ""));
  const listHtml = weaknesses || teachingSections || relations || drills || "<li>-</li>";
  const markdown = payload.markdown ? `<pre class="console-output">${payload.markdown}</pre>` : "";
  const reviewMeta = payload.review_id
    ? `<small>review #${payload.review_id}: ${payload.proposal_path || ""}</small>`
    : "";
  target.innerHTML = `
    <article class="result-card">
      <strong>${title}</strong>
      <div>${summary}</div>
      <div>${secondary}</div>
      <ul>${listHtml}</ul>
      ${preview}
      ${reviewMeta}
      ${markdown}
    </article>
  `;
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
    <strong>#${item.id} · ${item.proposal_type}</strong>
    <div>${item.source_note_path || ""}</div>
    <small>${item.target_note_path || t("noTargetNote")} · ${item.risk_level}</small>
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

document.getElementById("saveAdminToken").addEventListener("click", () => {
  if (!adminTokenInput.value.trim()) {
    logResult(t("startupError"), t("tokenMissing"));
    return;
  }
  window.localStorage.setItem("ui-admin-token", adminTokenInput.value.trim());
  logResult(t("tokenSaved"), { saved: true });
});

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

document.getElementById("smartCaptureSubmit").addEventListener("click", async () => {
  const payload = await api("/smart/error-capture", {
    method: "POST",
    body: JSON.stringify({
      title: document.getElementById("smartTitle").value,
      prompt: document.getElementById("smartPrompt").value,
      code: document.getElementById("smartCode").value,
      user_analysis: document.getElementById("smartAnalysis").value,
      language: "c",
      source_ref: "ui-smart",
    }),
  });
  document.getElementById("nodePackKey").value = payload.node.node_key;
  renderSmartResult(payload);
  logResult(t("smartCaptureComplete"), payload);
});

document.getElementById("nodePackSubmit").addEventListener("click", async () => {
  const payload = await api("/smart/node-pack", {
    method: "POST",
    body: JSON.stringify({
      node_key: document.getElementById("nodePackKey").value,
      top_k: 5,
    }),
  });
  renderSmartResult(payload);
  logResult(t("nodePackComplete"), payload);
});

document.getElementById("teachSubmit").addEventListener("click", async () => {
  const payload = await api("/smart/teach", {
    method: "POST",
    body: JSON.stringify({
      node_key: document.getElementById("nodePackKey").value,
      top_k: 5,
    }),
  });
  renderSmartResult(payload);
  logResult(t("teachPackComplete"), payload);
});

document.getElementById("relinkSubmit").addEventListener("click", async () => {
  const payload = await api("/smart/relink", {
    method: "POST",
    body: JSON.stringify({
      node_key: document.getElementById("nodePackKey").value,
      top_k: 5,
      create_review: true,
      dry_run: false,
    }),
  });
  renderSmartResult(payload);
  logResult(t("relinkComplete"), payload);
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
adminTokenInput.value = adminToken();

loadRuntime()
  .then(loadReviews)
  .catch((error) => logResult(t("startupError"), error.message));

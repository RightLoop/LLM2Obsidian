# Operations

- 设置 `VAULT_ROOT` 指向本地 Vault。
- 启动服务前确认 `data/processed/` 可写。
- 生产中推荐开启 Obsidian Local REST API，并配置 `OBSIDIAN_API_URL`。
- `OBSIDIAN_MODE=auto` 时优先尝试 REST，失败后回退到本地文件模式。
- `LLM_PROVIDER=deepseek` 时会通过 DeepSeek 的 OpenAI-compatible 接口生成结构化输出。
- `DRY_RUN=true` 时，系统只返回计划动作，不写 Vault。

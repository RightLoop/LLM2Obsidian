# Operations

- 设置 `VAULT_ROOT` 指向本地 Vault。
- 启动服务前确认 `data/processed/` 可写。
- 生产中推荐开启 Obsidian Local REST API，并配置 `OBSIDIAN_API_URL`。
- `DRY_RUN=true` 时，系统只返回计划动作，不写 Vault。

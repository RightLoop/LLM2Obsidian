# develop 分支审阅报告

## 1. 审阅范围
- 基于 `develop` 分支当前 worktree，对最近功能落地做静态审阅。
- 重点关注 API 暴露面、UI 控制面板、Vault 读写链路、外部 HTTP 集成与存储层实现。
- 结论来源于代码阅读与局部验证。

## 2. 总结
- **整体结论**：当前实现可运行，但默认暴露面偏大，存在高优先级安全问题。
- 架构分层基本清晰，`api / workflows / services / storage / integrations` 的边界大致成立，但多个高风险入口直接穿透到敏感配置和外部 HTTP 请求。
- 其中最突出的问题是：**未鉴权的控制面板接口**、**任意 URL 抓取导致 SSRF**、**Obsidian REST 默认关闭 TLS 校验**。
- 此外，向量索引全量重建存在明显的 O(n²) I/O 放大，数据量增大后会拖慢重建过程。
- 测试还把明文 API Key 回显/落盘视为“正确行为”，会固化不安全接口设计。

## 3. 详细问题

### 问题 1
- **标题**：未鉴权控制面板可读写敏感配置
- **等级**：P1
- **位置**：
  - `src/obsidian_agent/api/routes_ui.py:100-149`
  - `src/obsidian_agent/api/routes_ui.py:152-178`
- **说明**：`/ui/api/runtime`、`/ui/api/config`、`/ui/api/reload`、`/ui/api/seed-demo`、`/ui/api/reindex`、`/ui/api/weekly-digest` 当前均未做鉴权。`GET /ui/api/config` 会返回 `.env` 解析结果和 `raw_env`，`PUT /ui/api/config` 可以直接覆盖 API Key、Vault 路径、SQLite 路径等关键配置。
- **影响**：只要能访问服务端口，攻击者就可以读取 `DEEPSEEK_API_KEY`、`OPENAI_API_KEY`、`OBSIDIAN_API_KEY` 等敏感信息，或篡改 vault / 数据库 / 向量索引配置，并进一步触发重载、重建索引、写入演示数据等高影响操作。
- **建议**：至少为 `/ui/api/*` 增加统一鉴权和来源限制，默认禁止未认证访问；同时避免返回原始密钥，改为脱敏展示。

### 问题 2
- **标题**：`/capture/url` 允许任意 URL 抓取，存在 SSRF 风险
- **等级**：P1
- **位置**：
  - `src/obsidian_agent/api/routes_capture.py:33-42`
  - `src/obsidian_agent/integrations/html_fetcher.py:28-35`
- **说明**：`POST /capture/url` 直接把请求中的 `url` 传入 `httpx.AsyncClient().get()`，没有限制 scheme、目标地址、重定向目标或内网地址。
- **影响**：攻击者可以借服务端发起任意 HTTP 请求，探测 `127.0.0.1`、局域网、云元数据地址或其他内部系统；如果服务部署在可信网络内，会形成典型 SSRF 攻击面。
- **建议**：只允许 `http/https`，解析并拦截内网、环回、本地链路和保留地址；必要时加入 allowlist，并限制重定向与响应大小。

### 问题 3
- **标题**：Obsidian REST 客户端默认关闭 TLS 校验
- **等级**：P2
- **位置**：
  - `src/obsidian_agent/config.py:31`
  - `src/obsidian_agent/integrations/obsidian_rest_client.py:17-27`
  - `src/obsidian_agent/integrations/obsidian_rest_client.py:35-38`
- **说明**：`obsidian_verify_ssl` 与 `ObsidianRestClient.verify_ssl` 默认值都是 `False`。一旦配置为通过 HTTPS 访问 Obsidian Local REST API，请求将默认跳过证书校验。
- **影响**：如果 `OBSIDIAN_API_URL` 指向非 localhost、远程主机或被代理/转发的 HTTPS 入口，API Key 和请求内容可能遭受中间人攻击；即使当前主要面向本地场景，这个默认值也会把不安全行为固化到配置模型中。
- **建议**：把默认值改为 `True`，仅在用户显式确认风险时才允许关闭；UI 中若使用 `https://` 地址，应默认启用校验并提示风险。

### 问题 4
- **标题**：向量索引重建过程中反复读写 JSON，存在 O(n²) I/O
- **等级**：P2
- **位置**：
  - `src/obsidian_agent/services/indexing_service.py:31-55`
  - `src/obsidian_agent/storage/vector_store.py:19-28`
- **说明**：`reindex_all()` 会遍历每篇 note 并调用 `vector_store.upsert()`；而 `upsert()` 每次都会完整读取一次 JSON、修改后再完整写回一次。
- **影响**：随着 note 数量增长，重建过程会产生显著的重复 I/O 和序列化开销。当前 demo 数据量下可能不明显，但在真实 vault 上会拖慢 `/maintenance/reindex` 或 UI 触发的重建流程。
- **建议**：在 `reindex_all()` 中批量聚合向量后一次性写入，或为 `vector_store` 增加批量接口，避免每条记录都全量读写整个 JSON 文件。

### 问题 5
- **标题**：测试把明文 API Key 暴露/落盘固化为“正确行为”
- **等级**：P2
- **位置**：
  - `tests/integration/test_ui_routes.py:45-53`
- **说明**：集成测试对 `/ui/api/config` 的行为做了正向断言，并把 `DEEPSEEK_API_KEY=demo-key` 直接写入 `.env` 视为预期结果。
- **影响**：这会让后续开发把“读取、回显、覆盖明文密钥”继续当成稳定接口契约，增加修复鉴权、脱敏和最小暴露面的改造成本。
- **建议**：调整测试目标，改为校验脱敏输出、受控写入或权限失败分支，不要继续把明文配置暴露视为正确行为。

## 4. 架构观察
- 当前整体链路是 `api -> workflows -> services -> storage/integrations`，主体结构清楚，`ObsidianService` 负责与 vault 交互。
- 主要问题不在分层本身，而在**高权限能力直接暴露到无保护 HTTP 入口**，导致配置写入、网络抓取、索引重建都能被外部请求直接触发。
- UI 相关接口目前更像“运维控制面板”而不是普通业务路由，安全边界应当单独处理。

## 5. 额外风险提示
- `routes_ui.py` 中的 reload / reindex / seed 等接口都具备较强副作用，除鉴权外还应补充审计与幂等控制。
- URL 抓取能力如果后续扩展到更多协议、附件下载或内容解析，SSRF 风险会进一步放大。
- TLS 默认关闭的问题与 SSRF、未鉴权面板叠加时，整体攻击面会明显扩大。

## 6. 验证说明
- 本次结论以静态代码审阅为主。
- 未对所有路径做动态利用验证，但关键风险点代码证据充分。
- 尝试运行 `pytest -q` 时，当前环境存在临时目录相关问题；如需补做验证，建议先固定 `TMPDIR/TEMP` 或显式设置 pytest 的 `basetemp`。

## 7. 修复优先级建议
1. **先修 P1**：为 `/ui/api/*` 增加鉴权/访问控制，并修复 `/capture/url` 的 SSRF。
2. **再修 P2 安全项**：将 TLS 校验默认打开，收紧明文配置暴露。
3. **随后处理 P2 性能项**：重构向量索引写入路径，避免全量重建时的重复 I/O。
4. **最后补测试**：围绕鉴权、SSRF、TLS 默认值和配置脱敏补齐回归测试。

## 8. 结论
- **develop 分支当前不适合直接作为可信部署基线。**
- 如果仅用于本地 demo，短期风险主要体现在默认暴露过多高权限能力；如果进入共享网络、服务器或团队环境，上述问题需要先修复再继续推进。

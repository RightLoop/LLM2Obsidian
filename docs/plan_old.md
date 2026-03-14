# plan.md

## 1. 文档目的

本文件是 **LLM + Obsidian 自动化知识体系整合 Agent** 的唯一开发主控文档（single source of execution truth）。

目标是让 Codex 能够基于此文档，按阶段、按模块、按验收标准，逐步实现一个可运行、可扩展、可审计的知识整合系统。该系统以 **Obsidian Vault 作为知识真相源**，以 **外部 Agent 服务** 作为自动化编排器，以 **Review-first** 作为核心安全策略。

---

## 2. 项目总目标

构建一个本地优先（local-first）的知识整合系统，完成以下能力：

1. 接收外部输入（网页、PDF 摘录、聊天记录、剪贴板文本、手动输入）。
2. 自动生成结构化 Inbox 笔记。
3. 检索 Vault 中相关旧笔记。
4. 判断新内容应当：新建、补充、合并候选、仅进入审阅队列。
5. 生成候选修改（摘要、双链、frontmatter、建议插入内容）。
6. 将高风险修改写入 `90 Review/`，而不是直接覆盖主笔记。
7. 提供周期性维护能力：重复检测、孤儿笔记检测、元数据缺失检测、周报/月报整合。

---

## 3. 非目标（明确不做）

以下内容不属于 MVP 范围，除非后续阶段明确纳入：

1. 不做云端多人协同同步方案。
2. 不做复杂权限系统。
3. 不做移动端原生 UI。
4. 不做自动删除笔记。
5. 不做“无审阅直接修改 evergreen 主笔记”的危险功能。
6. 不做一次性支持所有输入源；先做最常见的 3~4 个输入源。
7. 不以 Obsidian 插件作为第一优先实现；MVP 优先采用外部服务架构。

---

## 4. 关键架构决策（已拍板，Codex 不要擅自偏离）

### 4.1 总体架构

采用以下架构：

- **Obsidian Vault**：知识真相源，保存最终 Markdown 笔记。
- **Obsidian Local REST API**：作为 Vault 的程序化访问接口。
- **External Agent Service**：核心编排器，负责检索、推理、写回、审计。
- **SQLite**：元数据与任务状态存储。
- **Vector Index**：语义检索层。
- **Review Queue (`90 Review/`)**：所有中高风险变更的人工审阅入口。

### 4.2 为什么不优先做 Obsidian 插件内嵌 Agent

原因：

1. 外部服务更容易调试。
2. 更容易接入向量索引、SQLite、异步任务。
3. 更容易切换模型供应商。
4. 更适合后续封装为 MCP server。
5. 可以降低插件侧复杂度，避免 Obsidian UI/生命周期耦合过深。

### 4.3 写入策略

必须严格遵守：

- **低风险**：可自动创建新 Inbox 笔记。
- **中风险**：生成候选修改并进入 Review。
- **高风险**：绝不自动覆盖主笔记，仅生成 Review 文档。

### 4.4 LLM API 策略

- **必须使用 Responses API**。
- **不得新开发基于 Assistants API 的方案**。
- 工具调用统一采用结构化 JSON schema。
- 提示词与工具层严格分离。

### 4.5 MCP 策略

- **MVP 不强依赖 MCP**。
- 但系统在模块设计上必须保留未来封装为 MCP server 的能力。
- 工具层接口必须独立、清晰、无 UI 耦合。

---

## 5. 预期目录结构

Codex 应创建如下目录结构（允许在实现中补充，但不得破坏主结构）：

```text
repo-root/
├─ README.md
├─ plan.md
├─ pyproject.toml
├─ .env.example
├─ .gitignore
├─ src/
│  └─ obsidian_agent/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ logging.py
│     ├─ app.py
│     ├─ cli.py
│     ├─ api/
│     │  ├─ __init__.py
│     │  ├─ routes_capture.py
│     │  ├─ routes_search.py
│     │  ├─ routes_review.py
│     │  └─ routes_maintenance.py
│     ├─ domain/
│     │  ├─ __init__.py
│     │  ├─ models.py
│     │  ├─ schemas.py
│     │  ├─ enums.py
│     │  └─ policies.py
│     ├─ services/
│     │  ├─ __init__.py
│     │  ├─ capture_service.py
│     │  ├─ normalize_service.py
│     │  ├─ retrieval_service.py
│     │  ├─ synthesis_service.py
│     │  ├─ review_service.py
│     │  ├─ maintenance_service.py
│     │  ├─ obsidian_service.py
│     │  ├─ llm_service.py
│     │  ├─ embeddings_service.py
│     │  └─ indexing_service.py
│     ├─ integrations/
│     │  ├─ __init__.py
│     │  ├─ obsidian_rest_client.py
│     │  ├─ openai_client.py
│     │  ├─ html_fetcher.py
│     │  ├─ pdf_ingest.py
│     │  └─ clipboard_ingest.py
│     ├─ storage/
│     │  ├─ __init__.py
│     │  ├─ db.py
│     │  ├─ repositories.py
│     │  ├─ vector_store.py
│     │  └─ migrations/
│     ├─ prompts/
│     │  ├─ system/
│     │  ├─ tasks/
│     │  └─ output_schemas/
│     ├─ workflows/
│     │  ├─ __init__.py
│     │  ├─ capture_workflow.py
│     │  ├─ link_workflow.py
│     │  ├─ synthesis_workflow.py
│     │  └─ maintenance_workflow.py
│     └─ utils/
│        ├─ markdown.py
│        ├─ frontmatter.py
│        ├─ diffing.py
│        ├─ slugify.py
│        └─ time.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
├─ scripts/
│  ├─ bootstrap_dev.sh
│  ├─ run_dev.sh
│  ├─ reindex_all.py
│  └─ seed_demo_data.py
└─ docs/
   ├─ architecture.md
   ├─ prompts.md
   ├─ api.md
   └─ operations.md
```

---

## 6. 技术栈要求

Codex 默认使用以下技术选型：

### 后端
- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 或 SQLModel（二选一，优先简单稳定）
- SQLite

### 检索与向量
- Embeddings：通过统一 `EmbeddingsService` 封装，不在业务层写死供应商细节
- 向量库：MVP 可用本地轻量方案（例如 Chroma 或 sqlite+faiss 风格封装）
- 关键词检索：先用 SQLite FTS 或简单 BM25 实现

### Obsidian 接入
- 优先通过 Obsidian Local REST API
- 严禁直接在多个模块中散落文件系统写入逻辑
- 所有 Vault 读写都必须走 `ObsidianService`

### 模型接入
- 统一走 `LLMService`
- 工具调用、JSON 校验、重试、限流在这一层实现

### 测试
- pytest
- httpx / pytest-asyncio（如需要）

---

## 7. Obsidian Vault 约定

Codex 不负责替用户改造整个现有 Vault，但必须默认兼容以下约定。

### 7.1 推荐目录

```text
00 Inbox/
01 Daily/
02 Literature/
03 Projects/
04 Evergreen/
05 Entities/
90 Review/
99 Templates/
```

### 7.2 frontmatter 规范

所有新建笔记必须支持以下字段：

```yaml
---
id: 20260313-xxxx
kind: inbox | literature | project | evergreen | fleeting | entity | review | digest
status: inbox | draft | review | stable | archived
source_type: url | pdf | chat | clipboard | manual
source_ref: ""
created_at: 2026-03-13T00:00:00+09:00
updated_at: 2026-03-13T00:00:00+09:00
tags: []
entities: []
topics: []
related: []
confidence: 0.0
generated_by: obsidian-agent
review_required: true
review_after: null
---
```

### 7.3 命名规则

- Inbox 笔记：`YYYY-MM-DD HHmm - Title.md`
- Review 笔记：`Review - <target or source title> - <timestamp>.md`
- Digest 笔记：`Weekly Digest - YYYY-[W]WW.md`

---

## 8. 核心能力拆分

系统拆成四个主要 Agent/工作流，但在实现上不需要做成四个独立进程。

### 8.1 Capture Workflow

职责：接收新内容并标准化为 Inbox 笔记。

输入：
- URL
- 纯文本
- 剪贴板内容
- PDF 文本（MVP 可先做文本提取版）

输出：
- 标准化 JSON
- Inbox Markdown
- 初始 tags / entities / topics

### 8.2 Linking Workflow

职责：为新内容召回相关旧笔记，并给出链接建议。

要求：
- 同时支持语义召回与关键词召回
- 输出相关笔记列表及关联理由
- 不直接改动旧笔记正文

### 8.3 Synthesis Workflow

职责：根据新内容与旧内容，生成：
- 摘要候选
- 合并建议
- 补充建议
- 双链候选
- Review 文档

### 8.4 Maintenance Workflow

职责：定期巡检 Vault：
- 重复内容候选
- 孤儿笔记
- 元数据缺失
- 低质量短笔记
- 周报/月报整合

---

## 9. 数据模型（必须实现）

至少实现以下表：

### 9.1 notes
记录系统已知笔记的元数据快照。

字段建议：
- id
- vault_path
- title
- kind
- status
- created_at
- updated_at
- source_type
- source_ref
- content_hash
- word_count
- indexed_at

### 9.2 note_links
记录显式或建议性链接。

字段建议：
- id
- from_note_id
- to_note_id
- link_type (`explicit`, `suggested`, `semantic`, `entity_match`)
- score
- created_at

### 9.3 ingestion_jobs
记录采集任务。

字段建议：
- id
- input_type
- input_ref
- state
- error_message
- created_at
- updated_at

### 9.4 review_items
记录审阅项。

字段建议：
- id
- source_note_id
- target_note_id
- proposal_type
- proposal_path
- state (`pending`, `approved`, `rejected`, `applied`)
- risk_level
- created_at
- updated_at

### 9.5 maintenance_reports
记录周期巡检结果。

---

## 10. 工具层契约（非常重要）

Codex 必须优先实现以下内部工具函数/服务方法。模型层只能调用这些高层能力，不能越层。

### 10.1 Vault 工具

- `search_notes(query, top_k, filters)`
- `read_note(path)`
- `read_notes(paths)`
- `create_note(folder, title, frontmatter, body)`
- `append_to_note(path, section, content)`
- `replace_section(path, section_heading, content)`
- `update_frontmatter(path, patch)`
- `move_note(path, target_folder)`

### 10.2 检索工具

- `keyword_search(text, top_k)`
- `semantic_search(text, top_k)`
- `hybrid_search(text, top_k)`
- `find_related_notes(note_path, top_k)`

### 10.3 Review 工具

- `create_review_item(proposal)`
- `render_review_markdown(proposal)`
- `apply_approved_review(review_id)`

### 10.4 Maintenance 工具

- `find_orphan_notes()`
- `find_duplicate_candidates()`
- `find_metadata_issues()`
- `generate_weekly_digest(week_key)`

### 10.5 LLM 工具

- `normalize_capture(input_payload)`
- `classify_integration_action(new_note, related_notes)`
- `generate_link_suggestions(new_note, related_notes)`
- `generate_review_proposal(new_note, target_note)`
- `generate_digest(note_set)`

---

## 11. 风险分级策略（必须编码实现）

### 11.1 低风险
可自动执行：
- 新建 Inbox 笔记
- 更新索引
- 生成建议 tags/entities/topics

### 11.2 中风险
必须进入 Review：
- 给旧笔记追加“相关笔记”段落
- 给旧笔记追加“参考资料”段落
- 更新部分 frontmatter 的 related 字段

### 11.3 高风险
严禁自动执行：
- 覆盖主摘要
- 合并两篇旧笔记为一篇
- 修改 evergreen 核心结论
- 删除内容
- 删除文件

---

## 12. 关键 Prompt 规则

Codex 需要将提示词模板文件化，并遵守以下规则：

1. 模型不得把推断写成事实。
2. 模型必须区分：
   - 原始来源事实
   - 从来源抽取的结构化字段
   - 基于上下文的整合推断
3. 不确定时选择保守策略。
4. 冲突内容必须显式输出 `conflicts` 字段。
5. 所有模型输出必须经过 Pydantic schema 校验。
6. 所有失败必须可重试且可观测。

建议输出 schema 类似：

```json
{
  "title": "...",
  "summary": "...",
  "entities": ["..."],
  "topics": ["..."],
  "tags": ["..."],
  "related_candidates": [
    {
      "path": "03 Projects/xxx.md",
      "reason": "...",
      "score": 0.82
    }
  ],
  "decision": "new_note | append_candidate | merge_candidate | review_only",
  "confidence": 0.84,
  "conflicts": []
}
```

---

## 13. API 设计（MVP）

FastAPI 至少实现以下接口：

### 13.1 Capture
- `POST /capture/url`
- `POST /capture/text`
- `POST /capture/pdf-text`
- `POST /capture/clipboard`

### 13.2 Search
- `GET /search?q=...`
- `GET /notes/related?path=...`

### 13.3 Review
- `GET /review/pending`
- `POST /review/{id}/approve`
- `POST /review/{id}/reject`
- `POST /review/{id}/apply`

### 13.4 Maintenance
- `POST /maintenance/reindex`
- `GET /maintenance/orphans`
- `GET /maintenance/duplicates`
- `GET /maintenance/metadata-issues`
- `POST /maintenance/weekly-digest`

---

## 14. 详细开发阶段

---

### Phase 0：项目初始化

#### 目标
搭建可运行的工程骨架。

#### 任务
1. 初始化 Python 项目。
2. 建立目录结构。
3. 配置 lint / format / test 基础设施。
4. 提供 `.env.example`。
5. 提供基础日志与配置模块。
6. 编写 README 的启动说明。

#### 验收标准
- `uvicorn` 或等价开发命令可启动。
- 健康检查接口可用。
- 单元测试框架可运行。

---

### Phase 1：Obsidian 接入层

#### 目标
打通 Obsidian Local REST API。

#### 任务
1. 实现 `ObsidianRestClient`。
2. 实现读取、创建、更新 frontmatter、追加内容等基础能力。
3. 封装 `ObsidianService`，业务层只依赖该服务。
4. 补充集成测试（使用 mock server 或本地 stub）。

#### 验收标准
- 能读取指定笔记。
- 能创建 Inbox 笔记。
- 能更新 frontmatter。
- 能追加内容到指定 section。

---

### Phase 2：本地元数据与索引层

#### 目标
建立 SQLite + 向量索引的最小双索引系统。

#### 任务
1. 初始化数据库与迁移。
2. 建立 notes / review_items / note_links / ingestion_jobs 表。
3. 实现全量扫描 Vault 元数据。
4. 实现内容 hash、词数统计、更新时间同步。
5. 实现 EmbeddingsService 与 VectorStore 抽象。
6. 实现 `reindex_all.py`。

#### 验收标准
- 可以扫描 Vault 并写入数据库。
- 可以为至少一批笔记建立向量索引。
- 可以通过 path 找到本地元数据记录。

---

### Phase 3：Capture Workflow

#### 目标
让系统能把外部输入转成 Inbox 笔记。

#### 任务
1. 实现 `POST /capture/text`。
2. 实现 `POST /capture/url`。
3. URL 模式下至少支持：抓正文、提取标题、清理 HTML。
4. 调用 LLM 生成结构化输出。
5. 基于模板渲染 Markdown。
6. 写入 `00 Inbox/`。
7. 在 DB 中记录 ingestion job。

#### 验收标准
- 输入一段文本可生成 Inbox 笔记。
- 输入一个 URL 可生成 Inbox 笔记。
- 新笔记具备 frontmatter。

---

### Phase 4：检索与链接建议

#### 目标
为新内容召回相关旧笔记并给出理由。

#### 任务
1. 实现关键词搜索。
2. 实现语义搜索。
3. 实现 hybrid search。
4. 实现 `find_related_notes(note_path)`。
5. 输出每个候选的：路径、得分、关联理由。

#### 验收标准
- 对一篇新笔记，能返回 top-k 相关旧笔记。
- 结果中同时融合关键词与语义线索。

---

### Phase 5：Synthesis 与 Review

#### 目标
生成整合建议，但默认不危险写回。

#### 任务
1. 实现决策分类：
   - `new_note`
   - `append_candidate`
   - `merge_candidate`
   - `review_only`
2. 实现 Review proposal schema。
3. 渲染 `90 Review/` Markdown。
4. 写入 review_items 表。
5. 实现审批与应用接口。

#### 验收标准
- 系统可对新笔记生成一条 Review 文档。
- 人工 approve 后可安全应用低/中风险变更。
- 高风险 proposal 不允许自动 apply。

---

### Phase 6：Maintenance Workflow

#### 目标
让系统具备“知识库维护”能力。

#### 任务
1. 重复候选检测（标题近似 + 内容相似）。
2. 孤儿笔记检测（无显式/建议链接）。
3. frontmatter 缺失检测。
4. 周报生成：按最近一周的 Inbox / Review / Stable note 汇总。

#### 验收标准
- 可生成一份周报 Markdown。
- 可输出重复候选清单。
- 可输出孤儿笔记清单。

---

### Phase 7：可用性提升

#### 目标
让系统从“能跑”提升到“可长期使用”。

#### 任务
1. 增加错误分类与重试。
2. 增加日志 trace id。
3. 增加配置项说明。
4. 增加 dry-run 模式。
5. 增加 demo 数据与截图文档。
6. 增加 prompt 版本化。

#### 验收标准
- 主要流程支持 dry-run。
- 主要错误可追踪。
- README 足够让新开发者启动。

---

## 15. Markdown 渲染模板要求

Codex 应将 Markdown 渲染模板单独管理，不允许在业务代码中散落大段字符串。

至少提供：
- Inbox note 模板
- Review note 模板
- Weekly digest 模板

### 15.1 Inbox 模板建议

```md
---
<frontmatter>
---

# <Title>

## Summary
<summary>

## Key Points
- ...

## Entities
- ...

## Related Notes (Suggested)
- [[...]]

## Source
- <source_ref>

## Raw Excerpt
<raw_excerpt>
```

### 15.2 Review 模板建议

```md
---
<frontmatter>
---

# Review: <Title>

## Proposal Type
<proposal_type>

## Source Note
[[...]]

## Target Note
[[...]]

## Rationale
...

## Suggested Patch
...

## Risk
medium | high

## Decision Checklist
- [ ] Facts verified
- [ ] Links look correct
- [ ] Safe to apply
```

---

## 16. 代码质量要求

Codex 必须遵守：

1. 业务逻辑与 I/O 分层。
2. 禁止把 prompt、HTTP 调用、Markdown 生成混写在单个函数里。
3. 每个 service 保持单一职责。
4. 所有外部集成必须封装到 `integrations/`。
5. 所有 schema 必须集中定义。
6. 为核心路径补充单元测试与集成测试。
7. 关键函数写 docstring。
8. 不允许写“魔法字符串”到处散落。

---

## 17. 测试计划

### 17.1 单元测试
覆盖：
- frontmatter 解析与 patch
- Markdown 模板渲染
- 决策分类结果校验
- 风险分级策略
- 内容 hash 与 slug 生成

### 17.2 集成测试
覆盖：
- Capture text -> Inbox note
- Capture URL -> Inbox note
- Related search -> proposal generation
- Review approve/apply
- Maintenance weekly digest

### 17.3 回归测试样例
需要准备至少以下 fixtures：
- 3 篇相似主题文献笔记
- 2 篇项目笔记
- 1 篇 evergreen 笔记
- 1 条新输入样本

---

## 18. 安全与审计要求

### 18.1 必须记录审计日志
至少记录：
- 谁/什么流程触发
- 输入来源
- 生成的目标路径
- proposal 类型
- 是否自动应用
- 错误信息

### 18.2 必须支持 dry-run
当开启 dry-run：
- 不写 Vault
- 不写 review 文件
- 仅返回将要执行的动作

### 18.3 必须保守处理删除操作
MVP 不实现自动删除。

---

## 19. Codex 执行顺序（严格建议）

Codex 应按以下顺序推进，不要一开始就写完整智能体：

1. 搭骨架（Phase 0）
2. 打通 Obsidian API（Phase 1）
3. 建 DB 与索引（Phase 2）
4. 完成 Capture（Phase 3）
5. 完成检索（Phase 4）
6. 完成 Review（Phase 5）
7. 完成 Maintenance（Phase 6）
8. 最后再做可用性与 polish（Phase 7）

禁止跳步去写“大而全”的单文件 agent。

---

## 20. 每阶段交付物要求

每个阶段结束时，Codex 必须产出：

1. 代码改动
2. 对应测试
3. README 或 docs 更新
4. 明确的已完成/未完成说明
5. 下一阶段阻塞项说明（如果有）

---

## 21. MVP 完成定义（Definition of Done）

满足以下条件即视为 MVP 完成：

1. 可通过 API 提交文本和 URL。
2. 系统可生成结构化 Inbox 笔记。
3. 系统可检索相关旧笔记。
4. 系统可生成 Review proposal。
5. 审批后可应用低/中风险修改。
6. 系统可生成一份 weekly digest。
7. 具备基础日志、测试、文档。

---

## 22. 后续扩展路线（MVP 后）

以下是后续版本方向，不属于 MVP 强制项，但架构需预留：

1. MCP Server 封装
2. PDF 真正版面解析
3. 邮件/消息平台接入
4. 浏览器扩展快速采集
5. CLI / TUI
6. Obsidian 辅助插件（仅做 UI 入口）
7. 实体知识图谱视图
8. 多模型策略与评估框架

---

## 23. 给 Codex 的明确实现约束

1. 先实现稳定基础设施，再实现智能化细节。
2. 任何会覆盖现有笔记正文的能力，都必须走 Review gate。
3. 任何 LLM 输出都必须经过 schema 验证。
4. 不要写一个巨大的 `agent.py` 承载全部逻辑。
5. 不要把供应商 API 细节泄漏到业务层。
6. 不要依赖用户当前 Vault 恰好格式完美。
7. 保持模块边界清晰，以便未来替换模型与接入方式。

---

## 24. 第一轮开发任务单（可直接执行）

### Task 1
初始化仓库骨架、配置、日志、FastAPI app、健康检查、README 启动说明。

### Task 2
实现 `ObsidianRestClient` 与 `ObsidianService`，支持：读取、创建、frontmatter 更新、section 追加。

### Task 3
实现 SQLite schema、迁移、notes/review_items/ingestion_jobs 表与基础 repository。

### Task 4
实现 `POST /capture/text`，把文本变为标准化 Inbox 笔记。

### Task 5
实现 `POST /capture/url`，至少完成 HTML 提取 + 结构化摘要 + Inbox 写入。

### Task 6
实现 keyword + semantic + hybrid search。

### Task 7
实现 Review proposal 生成、Markdown 渲染、写入 `90 Review/`。

### Task 8
实现 `approve/reject/apply` 基础流程。

### Task 9
实现 weekly digest 与 orphan/duplicate 检测。

### Task 10
补齐测试、dry-run、docs、demo 数据。

---

## 25. 最终原则

这个系统的本质不是“让 LLM 接管 Obsidian”，而是：

- 让 Obsidian 保持知识真相源
- 让 Agent 负责整理与建议
- 让 Review 机制防止错误扩散
- 让检索和元数据把零散笔记逐步变成体系

Codex 在整个实现过程中，必须优先保证：

**可控性 > 炫技**

**可审计性 > 全自动**

**模块边界清晰 > 快速堆功能**


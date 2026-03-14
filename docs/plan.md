# smart-upgrade-plan-aligned.md

## 1. 文档定位

本文件是在**阅读当前项目实际代码与目录结构之后**，对上一版 `smart-upgrade-plan.md` 进行的**现实对齐版修订**。

目标不是从零重新设想系统，而是：

1. 以当前仓库已经落地的实现为基线；
2. 删除不符合当前工程现状的假设；
3. 保留正确的升级方向；
4. 重新组织“让系统更聪明”的下一阶段开发计划；
5. 让 Codex 后续能直接沿当前代码推进，而不是推翻重来。

---

## 2. 当前项目实际状态（基于代码审阅得出）

### 2.1 当前已经存在的核心系统

当前项目不是“概念稿”，而是一个已经具备基础闭环的服务化系统，核心骨架已经存在：

- `FastAPI` 应用工厂：`src/obsidian_agent/app.py`
- 配置中心：`src/obsidian_agent/config.py`
- Vault 读写服务：`src/obsidian_agent/services/obsidian_service.py`
- LLM 统一入口：`src/obsidian_agent/services/llm_service.py`
- Capture 工作流：`capture_workflow.py` + `capture_service.py`
- 检索服务：`retrieval_service.py`
- Review 服务：`review_service.py`
- Maintenance 服务：`maintenance_service.py`
- Indexing 服务：`indexing_service.py`
- SQLite 元数据层：`storage/db.py` + `repositories.py`
- JSON 向量索引：`storage/vector_store.py`
- Web 控制台：`src/obsidian_agent/ui/`
- 已有 API 路由：
  - `/capture/*`
  - `/search`
  - `/notes/related`
  - `/review/*`
  - `/maintenance/*`
  - `/ui/*`

### 2.2 当前模型接入真实状态

当前模型接入方式是：

- `DeepSeekChatClient`
- `OpenAIResponsesClient`

都通过 `LLMService` 统一编排。

这意味着：
- 模型多后端抽象已经初步存在；
- 但**目前尚未接入 Ollama**；
- 当前 `LLMService` 还主要围绕 `normalize_capture()` / `classify_integration_action()` / `generate_review_proposal()` 这类基础能力运行；
- 还没有“错误诊断 / 关系提炼 / 教学组织 / 压缩上下文”这些更高层智能任务。

### 2.3 当前检索与索引真实状态

当前系统已具备：

- 基于 SQLite note metadata 的索引记录；
- 基于 `VectorStore(JSON)` 的简单向量检索；
- 基于全文读取后的关键词匹配；
- `keyword + semantic -> hybrid` 的基本融合检索。

但当前仍然是：

- **按整篇 note 粒度检索**；
- 没有 section / node 级索引；
- `EmbeddingsService` 目前是**本地 deterministic 占位实现**，不是实际 LLM embedding 模型；
- 关系层仍较薄，当前仅有 `note_links` 表，但没有真正的“知识节点边模型”。

### 2.4 当前 UI / 交互真实状态

当前存在的是：

- 内置 Web 控制台（`/` 与 `/ui`）
- 可编辑 `.env`
- 可 reload runtime
- 可 seed demo
- 可 reindex
- 可运行 weekly digest

**当前并不存在真正的 Obsidian 插件代码。**

因此上一版方案里“插件命令入口优先接入”的表述需要修正：

- 短期主入口应仍然是 **FastAPI + Web 控制台 + API**
- Obsidian 插件集成应作为后续增强层，而不是当前第一实现路径

### 2.5 当前 Review 能力真实状态

当前 Review 机制已经落地，但能力边界很明确：

- 能生成 review markdown
- 能把 review item 持久化到数据库
- 能 approve / reject
- 能对 `append_candidate` 执行自动 apply
- 高风险 proposal 被禁止自动 apply

但当前**并没有复杂 patch engine**，还做不到：

- 多节点批量 apply
- 复杂 merge apply
- section 级语义合并
- 节点图级别的批量关系写入审批

这意味着下一阶段设计必须尽量沿着“安全可追加”的方向增强，而不是一开始就设计高度复杂的自动 patch。

---

## 3. 对上一版升级方案的修正结论

以下是需要保留与需要修正的部分。

### 3.1 应保留的方向

上一版方案中，这些方向是正确的，应继续保留：

1. 围绕“错误 -> 薄弱点 -> 相关知识 -> 教学输出”构建智能层。
2. 引入本地模型（Ollama）承担高频、低成本、结构化任务。
3. 使用关系提炼与上下文压缩减少远端大模型 token 消耗。
4. 将输出从“整篇长摘要”升级为“节点群 + 关系”。
5. 为 C 语言错题场景做领域特化。

### 3.2 需要修正的地方

#### 修正 A：不要假设已有 Obsidian 插件可直接对接
当前项目真实交互入口是 Web 控制台和 API。

所以本阶段应先实现：
- 新服务层
- 新 API 路由
- 新 prompt bundle
- 新节点写入机制
- 新 UI 面板/按钮

之后再考虑 Obsidian 插件接入。

#### 修正 B：不要假设已有图谱级 schema
当前仓库只有 notes / note_links / review_items 等表。

所以下一阶段应采用：
- **增量扩表**，而不是直接假设已有知识图谱基础设施；
- 优先让“节点仍然落在 Markdown note 中”，关系先落 SQLite 与 frontmatter 双处；
- 避免一开始引入太重的 graph database 方案。

#### 修正 C：不要假设已有真实 embedding 后端
当前 `EmbeddingsService` 是占位实现。

因此“Ollama 本地模型接入”必须包含：
- 本地 embedding 支持
- provider-aware embeddings routing
- 重新定义向量刷新与回填策略

#### 修正 D：不要把远端 LLM 当默认主引擎
当前项目默认是 `DeepSeek`，其次 `OpenAI`，已经存在 provider 抽象。

所以更合理的升级方式是：
- 扩展现有 `LLMService` 为多后端路由器；
- 新增 `OllamaClient` 与 `OllamaEmbeddingsClient`；
- 不要重写整个模型层。

#### 修正 E：不要一开始追求复杂自动 patch
当前 review apply 只安全支持追加型变更。

因此“节点化知识增长”第一阶段应优先采取：
- 创建新节点
- 追加轻量 backlinks / related section
- 更新 frontmatter.related / relation metadata
- 写 review note

而不是大规模自动重写已有 evergreen。

---

## 4. 现实对齐后的升级总目标

下一阶段升级目标应重述为：

> 在当前 **FastAPI + ObsidianService + SQLite + JSON VectorStore + Review Queue + Web UI** 的基础上，新增一层“错误诊断与知识节点生成智能层”，优先服务于 **C 语言错题/薄弱点积累场景**，并通过 **Ollama 本地模型 + 远端大模型混合路由**，实现：
>
> - 错误抽取
> - 薄弱点诊断
> - 相关知识节点召回
> - 节点关系提炼
> - 上下文压缩
> - 教学输出组织
> - 安全写入与 review

这不是一次“重构系统”，而是一次**在现有系统上增量叠加智能层**。

---

## 5. 下一阶段应该新增而不是重写的模块

基于当前代码结构，新增模块建议如下。

### 5.1 integrations/
新增：
- `ollama_client.py`
- `ollama_embeddings_client.py`

原因：
当前 provider integrations 已经放在 `integrations/`，Ollama 也应保持同样位置，方便通过 `LLMService` 与 `EmbeddingsService` 调用。

### 5.2 services/
新增：
- `error_extractor_service.py`
- `weakness_diagnoser_service.py`
- `relation_miner_service.py`
- `context_compressor_service.py`
- `teaching_planner_service.py`
- `node_writer_service.py`
- `routing_policy_service.py`

说明：
这几个新服务不应塞进 `LLMService`。`LLMService` 继续做“统一模型调用抽象”，而新服务负责业务智能。

### 5.3 workflows/
新增：
- `smart_error_workflow.py`
- `node_growth_workflow.py`
- `teaching_pack_workflow.py`

说明：
当前项目已经采用 workflow 编排层，因此智能升级也应复用该模式，而不是用一个巨大的 `smart_agent.py`。

### 5.4 api/
新增路由文件：
- `routes_smart.py`

建议增加的 API：
- `POST /smart/error-capture`
- `POST /smart/node-pack`
- `POST /smart/teach`
- `GET /smart/related-nodes`
- `POST /smart/relink`

### 5.5 prompts/
当前 prompt bundle 过于薄，仅包含 capture。

应新增：
- `system/error_extraction.md`
- `system/weakness_diagnosis.md`
- `system/relation_mining.md`
- `system/context_compression.md`
- `system/teaching_generation.md`
- `output_schemas/error_object.json`
- `output_schemas/weakness_object.json`
- `output_schemas/relation_pack.json`
- `output_schemas/node_pack.json`
- `tasks/error_node.md.tmpl`
- `tasks/concept_node.md.tmpl`
- `tasks/contrast_node.md.tmpl`
- `tasks/pitfall_node.md.tmpl`
- `tasks/teaching_pack.md.tmpl`

---

## 6. 数据层的现实对齐升级方案

### 6.1 不建议直接引入独立图数据库
当前项目已经有 SQLite，且 Review/Note 元数据都在这里。

因此下一阶段优先策略是：

- 继续使用 SQLite
- 增加节点表与关系表
- Markdown 仍然是知识最终落库形态
- DB 负责加速与关系元数据

### 6.2 建议新增表

#### knowledge_nodes
用于记录被系统识别出的“知识节点元数据”。

字段建议：
- id
- note_path
- node_type (`error`, `concept`, `pitfall`, `contrast`, `review`)
- domain (`c`)
- title
- canonical_key
- confidence
- created_at
- updated_at

#### knowledge_edges
用于记录节点关系。

字段建议：
- id
- from_node_id
- to_node_id
- relation_type
- score
- reason
- created_by_model
- created_at
- reviewed

#### error_occurrences
用于跟踪“同类错误多次出现”。

字段建议：
- id
- error_node_id
- source_problem_ref
- raw_input_hash
- created_at
- notes

### 6.3 对现有表的处理策略

- `notes`：继续保留，作为 Vault note 元数据主表
- `note_links`：保留，用于 note 级链接记录；但未来“语义关系边”应逐步转向 `knowledge_edges`
- `review_items`：继续保留，用于智能生成后的人工审阅

---

## 7. 现实对齐后的“聪明化”主流程

### Flow 1：用户提交一道 C 语言错题分析

输入可能来自：
- `/capture/text` 之后二次增强
- 新增的 `/smart/error-capture`
- Web 控制台中的专门表单

处理流程应为：

1. 读取原始输入（题目、代码、用户分析）
2. `ErrorExtractorService` 生成 `ErrorObject`
3. `WeaknessDiagnoserService` 生成 `WeaknessObject`
4. 检索最相关旧节点 / 旧 note
5. `RelationMinerService` 判断关系
6. `ContextCompressorService` 生成 `RelationPack`
7. `RoutingPolicyService` 判断：
   - 仅本地 Ollama 完成
   - 或送远端 DeepSeek/OpenAI 生成更高质量教学输出
8. `TeachingPlannerService` 规划输出形状
9. `NodeWriterService` 生成：
   - ErrorNode
   - 相关 ConceptNode / ContrastNode / PitfallNode
10. 写入 Vault（优先创建新 note，必要时轻量追加现有 note）
11. 记录 `knowledge_nodes` / `knowledge_edges`
12. 对中风险写入生成 review item

### Flow 2：旧节点重新关系挖掘

用于已有积累内容的“补链”。

步骤：
1. 选择某个 note/node
2. 检索候选旧节点
3. 本地模型判关系
4. 生成关系建议
5. 更新数据库关系边
6. 可选更新 frontmatter.related
7. 对正文追加操作进入 Review

### Flow 3：生成教学包

输入：
- 一个 ErrorNode 或一组相关节点

输出：
- 一份用户可读的分层讲解
- 可同时生成一个教学 note

---

## 8. 为什么本阶段要先做“节点 note”，而不是 section/块级复杂图谱

结合当前工程现状，优先采用“每个核心知识对象先落为单独 note”的方案更合理，原因：

1. 当前 `ObsidianService` 已天然支持 create_note / append_to_note / update_frontmatter。
2. 当前索引系统是按 note 处理，扩展到 node-note 比扩展到块级数据库更自然。
3. Review 系统也是围绕 note 操作构建的。
4. C 语言错题知识点本身很适合 note 化：
   - 一个错误 = 一个 ErrorNode note
   - 一个概念 = 一个 ConceptNode note
   - 一个对比点 = 一个 ContrastNode note

因此本阶段不建议先做：
- block-level graph
- paragraph-level retrieval
- AST-level note fragments

这些都可以放到后续版本。

---

## 9. 与当前 EmbeddingsService 对齐的升级路线

### 9.1 当前问题

当前 `EmbeddingsService` 是占位实现，只能保证最小闭环，不能满足：
- 错误相似度判断
- 概念节点精确召回
- 复习聚类
- 高质量 relation mining 前筛选

### 9.2 下一步改法

不要删除 `EmbeddingsService`，而是把它升级成 provider-aware facade：

建议支持：
- `deterministic`（现有占位逻辑，用于离线测试）
- `ollama`（本地 embedding）
- `openai`（可选远端 embedding）

### 9.3 配置建议

在 `Settings` 中新增：
- `embeddings_provider`
- `ollama_base_url`
- `ollama_chat_model`
- `ollama_json_model`
- `ollama_embedding_model`
- `ollama_timeout_seconds`

这样可保持当前配置风格一致。

---

## 10. 与当前 LLMService 对齐的升级路线

### 10.1 当前状态

`LLMService` 目前是一个较薄的统一模型层，主要做：
- capture normalization
- integration action classification
- review proposal generation

### 10.2 下一步不要做的事

不要把所有新智能任务都直接塞进 `LLMService`。

### 10.3 正确做法

`LLMService` 继续做“通用模型调用适配层”，新增能力可以是：
- `run_structured_task(task_name, instructions, input_text, schema_name)`
- `provider_capabilities()`
- `supports_tool_calling()`
- `supports_embeddings()`

而业务智能逻辑由各 service 负责，例如：
- `ErrorExtractorService` 调 `LLMService`
- `RelationMinerService` 调 `LLMService`
- `ContextCompressorService` 调 `LLMService`

这样更符合当前项目分层。

---

## 11. 现实对齐后的 Prompt 工程目标

当前 prompt 资产只有 capture 相关内容，明显不足以支持“更聪明”。

因此下一阶段的 prompt 工程目标不是“微调现有 capture prompt”，而是建立新的 prompt bundle v2。

### 11.1 Prompt Bundle v2 内容

至少应包括：

#### A. Error Extraction
从错题文本中抽取：
- 具体错误
- 错误本质
- 错误假设
- 代码片段

#### B. Weakness Diagnosis
从错误上升到：
- 薄弱点标签
- 前置知识缺口
- 应补知识点

#### C. Relation Mining
给定当前节点与候选旧节点，判断：
- 是否相关
- 什么关系
- 理由是什么
- 置信度如何

#### D. Context Compression
给定一批相关节点，压缩成：
- 当前错误摘要
- 最关键相关概念
- 不需要重复讲的点
- 推荐输出形状

#### E. Teaching Generation
将 Relation Pack 转化为最终教学话术。

### 11.2 模板化输出原则

所有最终落库的 note 都尽量模板化渲染，不让模型自由决定排版。

---

## 12. 关系提炼的现实落地策略

### 12.1 先做“候选关系 -> 审批 -> 写入”

关系提炼不要直接对正文做大改。

优先实现：
- 数据库里记录边
- frontmatter 中记录 related 节点
- note 正文中写“Related Concepts / Related Errors / Related Notes”段

### 12.2 首批关系类型

结合 C 语言学习场景，建议先做以下关系：

- `reveals_gap_in`
- `requires`
- `contrasts_with`
- `commonly_confused_with`
- `is_example_of`
- `fixes`
- `repeated_in`

这些已经足够支持“错题 -> 知识点 -> 对比概念 -> 修正方式”的网络。

---

## 13. C 语言专用化应如何接到当前仓库里

### 13.1 先做 domain profile，而不是写死全局逻辑

建议新增：
- `src/obsidian_agent/domain_profiles/c_language.py`

其中放：
- 标签体系
- 关系类型白名单
- 默认 node 模板映射
- 关键词扩展
- C 语言常见误区库

### 13.2 为什么这样做

当前系统是通用知识整合系统；
如果直接把 C 语言逻辑硬编码进 capture/retrieval/review，会污染主干。

更合理方式是：
- 主系统保持通用
- 通过 domain profile 注入场景特化能力

---

## 14. 与当前 Web 控制台对齐的交互升级

因为当前项目已有 `/ui`，所以本阶段最现实的交互增强是**先扩展控制台**。

### 14.1 建议新增 UI 面板

#### A. Error Capture 面板
字段：
- 题目标题
- 原题文本
- 代码
- 用户自我分析
- 域选择（默认 C）

#### B. Node Pack 预览面板
显示：
- 将生成的节点列表
- 每个节点的标题、类型、关系
- 是否进入 review

#### C. Relation Review 面板
显示：
- 候选关系边
- 理由
- 分数
- 是否接受

#### D. Teaching Pack 面板
显示最终教学输出。

### 14.2 这比“先写插件”更合理的原因

因为：
- 当前 UI 代码已存在；
- 接入成本低；
- 便于调 prompt 与调模型；
- 更容易做 dry-run 与 debug。

因此 Obsidian 插件集成应放到本阶段末尾或下一阶段。

---

## 15. 现实对齐后的 Token 优化策略

上一版关于 token 优化的方向正确，但应结合当前代码落地。

### 15.1 新增 `ContextCompressorService`

它的职责不是读全 Vault，而是：
- 接受 retrieval 的候选结果
- 读取候选 note 摘要 / 部分正文
- 调本地 Ollama 生成 `RelationPack`

### 15.2 `RelationPack` 应直接服务现有 Synthesis/Teaching 流程

建议作为中间对象存在，而不是仅在 prompt 里拼字符串。

字段建议：
- current_error
- weakness_labels
- top_related_nodes
- relation_summary
- do_not_repeat
- recommended_output_shape
- token_budget_hint

### 15.3 Novelty Filter

在写新节点前增加：
- 是否只是已有错误节点的新实例？
- 是否只应更新 repeat_count / examples？

这样能减少重复 note 爆炸。

---

## 16. 实际可执行的 Phase 重新划分

### Phase 1：模型与配置接入对齐

目标：在不破坏现有 DeepSeek/OpenAI 支持的前提下接入 Ollama。

任务：
1. 扩展 `Settings` 增加 Ollama 配置
2. 新增 `ollama_client.py`
3. 新增 `ollama_embeddings_client.py`
4. 扩展 `build_container()` 支持 Ollama provider
5. 升级 `EmbeddingsService` 为 provider-aware

验收：
- 可以通过配置选择 Ollama 做结构化 JSON 输出
- 可以通过配置选择 Ollama 做 embeddings
- 现有 DeepSeek/OpenAI 路径不回归

### Phase 2：错误对象与节点对象建模

目标：让系统从“普通 note”升级到“错误节点 / 概念节点”。

任务：
1. 新增 Pydantic schema：
   - `ErrorObject`
   - `WeaknessObject`
   - `KnowledgeNodeSchema`
   - `KnowledgeEdgeSchema`
   - `RelationPack`
2. 新增数据库表：
   - `knowledge_nodes`
   - `knowledge_edges`
   - `error_occurrences`
3. 新增 Markdown 模板

验收：
- 系统可生成结构化 ErrorObject
- 系统可把一个节点写成 note + DB record

### Phase 3：智能分析服务落地

目标：把“更聪明”的核心能力做出来。

任务：
1. 实现 `ErrorExtractorService`
2. 实现 `WeaknessDiagnoserService`
3. 实现 `RelationMinerService`
4. 实现 `ContextCompressorService`
5. 实现 `TeachingPlannerService`

验收：
- 一道 C 语言错题可被解析成错误、薄弱点、候选知识点与关系候选

### Phase 4：Node Writer 与安全写入

目标：把分析结果落库到 Obsidian 与 SQLite。

任务：
1. 实现 `NodeWriterService`
2. 安全创建 ErrorNode / ConceptNode / ContrastNode
3. 更新关系元数据
4. 对需要正文追加的部分走 review

验收：
- 能生成一组节点 note
- 能记录节点间关系
- 不会危险覆盖既有 note

### Phase 5：API 与 UI 对齐

目标：把智能层暴露给当前系统的真实入口。

任务：
1. 新增 `/smart/*` API
2. 扩展 `/ui` 控制台
3. 增加 dry-run 显示
4. 增加预览/确认页

验收：
- 用户可通过现有 Web 控制台提交一条 C 错题并获得节点群输出

### Phase 6：教学输出与 token 优化

目标：把本地结构化分析与远端教学表达真正串起来。

任务：
1. 实现 routing policy
2. 实现 RelationPack -> final teaching output
3. 加入 token 统计与日志
4. 加入 novelty filter

验收：
- 相比直接把所有原文送远端，远端上下文明显缩短
- 最终教学输出质量可接受

### Phase 7：回归与质量评估

目标：保证智能层在现系统上稳定可用。

任务：
1. 单元测试
2. 集成测试
3. 端到端 demo
4. C 语言专项样例验证

验收：
- 覆盖 `sizeof / strlen / 指针-数组混淆 / 参数退化` 等典型案例

---

## 17. 第一轮最值得 Codex 立刻做的任务

### Task 1
扩展 `Settings`、`build_container()`、`LLMService`、`EmbeddingsService`，加入 Ollama 支持，但保持 DeepSeek/OpenAI 向后兼容。

### Task 2
新增 `ErrorObject` / `WeaknessObject` / `KnowledgeNodeSchema` / `RelationPack` 等 schema。

### Task 3
新增 `error_extractor_service.py` 与 `weakness_diagnoser_service.py`，先实现从一段 C 语言错题分析中抽出结构化错误对象。

### Task 4
新增 `knowledge_nodes` / `knowledge_edges` / `error_occurrences` 表与 repository。

### Task 5
新增 `node_writer_service.py`，支持把 ErrorNode / ConceptNode 写入 Obsidian note。

### Task 6
新增 `/smart/error-capture` 接口，完成：
- 输入错题
- 输出 ErrorObject
- 生成至少一个 ErrorNode note

### Task 7
新增 `relation_miner_service.py`，复用现有 retrieval，再由本地模型做关系判定。

### Task 8
新增 `context_compressor_service.py`，生成 `RelationPack`。

### Task 9
扩展 `/ui` 控制台，加入 Error Capture 表单与 Node Pack 预览。

### Task 10
补充专项测试，围绕你给出的 `sizeof` / `strlen` / 指针与数组混淆示例打通完整演示链路。

---

## 18. 这一版计划的核心原则

### 原则 1
**以当前代码为基线做增量增强，不推倒重来。**

### 原则 2
**先服务层和 API 层智能化，再谈插件化。**

### 原则 3
**先节点 note 化与关系元数据化，再做更复杂的块级图谱。**

### 原则 4
**让本地 Ollama 先做结构化与压缩，高参数远端模型只做高价值教学表达。**

### 原则 5
**沿用现有 Review-first 安全策略，不引入大规模危险自动覆盖。**

---

## 19. 最终结论

基于当前真实项目状态，下一阶段最合理的路径不是：

- 直接做 Obsidian 插件优先；
- 直接上重型知识图谱；
- 直接让远端大模型接管全部分析；
- 直接把所有历史 note 原文塞给多参数模型。

而是：

1. 在当前服务层中接入 Ollama；
2. 新增错误诊断与关系提炼服务；
3. 让 note 从“普通采集笔记”升级为“错误节点 / 概念节点 / 对比节点”；
4. 用 RelationPack 压缩上下文；
5. 只把高价值上下文送给远端模型生成最终教学表达；
6. 继续依托当前 Web 控制台、API、Review 机制和 ObsidianService 来完成落库。

**这样才是真正与当前实现对齐的“让系统更聪明”的升级方案。**

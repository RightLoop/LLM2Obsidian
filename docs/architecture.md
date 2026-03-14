# Architecture

系统由 FastAPI 服务、ObsidianService、SQLite 元数据层、JSON 向量索引和 Review 队列组成。所有 Vault 写操作统一经过 `ObsidianService`，所有模型调用统一经过 `LLMService`。

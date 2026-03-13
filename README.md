# LLM2Obsidian

本项目实现一个本地优先的 LLM + Obsidian 知识整合 Agent。Obsidian Vault 是知识真相源，所有中高风险修改都进入 `90 Review/`，不直接覆盖主笔记。

## 快速开始

1. 创建虚拟环境并安装依赖：

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
```

2. 复制环境变量：

```bash
copy .env.example .env
```

默认推荐：
- `LLM_PROVIDER=deepseek`
- `OBSIDIAN_MODE=auto`

3. 启动开发服务：

```bash
uvicorn obsidian_agent.app:create_app --factory --reload
```

4. 运行测试：

```bash
pytest
```

## MVP 能力

- `POST /capture/text`
- `POST /capture/url`
- `GET /search`
- `GET /notes/related`
- Review 审批与应用
- Maintenance reindex / orphan / duplicate / metadata issues / weekly digest

更多约束见 [docs/plan.md](docs/plan.md) 与 [docs/specs/git-flow.md](docs/specs/git-flow.md)。

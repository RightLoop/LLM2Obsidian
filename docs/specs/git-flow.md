# Git Flow 开发规范（强制）

## 1. 分支模型
- `main`：生产可发布分支，只接受 release/hotfix 合并。
- `develop`：日常集成分支，所有 feature 最终汇入此分支。
- `feature/*`：功能开发分支，从 `develop` 切出。
- `release/*`：发版加固分支，从 `develop` 切出。
- `hotfix/*`：线上紧急修复分支，从 `main` 切出。

## 2. 分支命名规范
- `feature/<issue-id>-<short-topic>`
- `release/<version>`
- `hotfix/<version>-<short-topic>`

示例：
- `feature/12-sliding-window-retransmit`
- `release/v0.2.0`
- `hotfix/v0.2.1-doorbell-dup-fix`

## 3. 开发流程
1. 在 GitHub issue 中明确需求和验收标准。
2. 从 `develop` 切 `feature/*` 分支。
3. 本地开发 + 单元测试 + 必要压测。
4. 提交 PR 到 `develop`，完成评审后合并。
5. 发版阶段从 `develop` 切 `release/*`，做回归与修复。
6. release 合并到 `main` 并打 tag，再回合并到 `develop`。

## 4. 提交规范
- 采用 Conventional Commits：
  - `feat(scope): ...`
  - `fix(scope): ...`
  - `perf(scope): ...`
  - `refactor(scope): ...`
  - `test(scope): ...`
  - `docs(scope): ...`
  - `chore(scope): ...`

要求：
- 一次提交只做一件逻辑相对完整的事。
- 提交信息必须能说明“改了什么 + 为什么改”。

## 5. PR 规范
- `feature/*` 只能提 PR 到 `develop`。
- `release/*` PR 到 `main`，随后回合并到 `develop`。
- `hotfix/*` PR 到 `main`，随后 cherry-pick/回合并到 `develop`。
- PR 必须包含：
  - 变更摘要
  - 风险评估
  - 测试证据（日志/截图/数据）
  - 回滚方案

## 6. 保护策略
- `main`、`develop` 必须开启分支保护。
- 禁止直接 push。
- 必须通过 CI。
- 至少 1 位 reviewer 通过后才可合并。

## 7. 合并策略
- `feature/*` 建议 squash merge（保证历史整洁）。
- `release/*` 和 `hotfix/*` 建议 merge commit（保留语义边界）。

## 8. 发版流程
1. `develop` -> `release/<version>`。
2. 运行回归、性能、安全检查。
3. 修正版本号与变更日志。
4. 合并到 `main` 并打 `v<version>` tag。
5. 将 release 分支回合并到 `develop`。

## 9. 热修流程
1. `main` -> `hotfix/<version>-<topic>`。
2. 快速修复并验证。
3. 合并到 `main`，打 patch tag。
4. 回合并或 cherry-pick 到 `develop`。

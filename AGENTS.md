# AGENTS.md

## 项目概况

- 目标：沉淀术数文献知识编译、模型协作、质量门槛与 APP 接入规范。
- 当前技术形态：Markdown 设计文档；后续计划加入 YAML/JSON Schema、示例任务包和确定性校验器。
- 启动命令：暂无应用运行时。
- 环境：`bash tools/jules_setup.sh`（Python 3.14 + `.venv/`）；跑测试前 `export LC_ALL=C.UTF-8`（macOS 用 `en_US.UTF-8`）。
- 测试命令：`pipeline/` 下 11 个包各自 `.venv/bin/python -m unittest discover -s pipeline/<包>/tests -t .`；文档变更另执行 `git diff --check`。
- **接手先读 `docs/handoff/CLOUD-HANDOFF.md`（2026-09-23 本线移交云端的现状与前因后果）。**
- **待办唯一入口是仓库根 `TODO.md`**，一次做一条。云端执行者（如 Jules）的任务书在 `docs/jules/`，按任务书执行，回报写在同目录。

## Git 安全铁律

1. 只在本仓库目录内工作；禁止切换到或修改其他 worktree。
2. 禁止执行 `git reset --hard`、`git checkout -- .`、`git clean -f`、`git push --force`、`git stash drop`、`git stash clear`、`git branch -D`、`git rebase` 或删除 `.git`。
3. 每完成一个可验证子任务立即提交；消息使用 Conventional Commits。
4. 不向 `main`/`master` 合并、rebase 或 push；合并只由人类执行。
5. 会话结束前提交所有改动，并更新 `HANDOFF.md` 和 `PLAN.md`。

   受限执行 Agent 例外：当已审查的 ACT 明确禁止执行 Agent 修改 `PLAN.md`、`HANDOFF.md` 或总 TODO 时，执行 Agent 以最终证据报告完成交接，不得违反 ACT；上述协调文档由主 Agent 在独立验收后统一更新。

## 会话启动协议

依次阅读 `AGENTS.md`、`HANDOFF.md`、`PLAN.md`，从 `PLAN.md` 第一项未完成任务继续，不重做已完成任务。

## 交接协议

`HANDOFF.md` 使用以下结构：

```text
# HANDOFF
更新时间：
当前分支/worktree：
刚完成：
进行到一半的事（精确到文件和章节）：
下一步（第一件事）：
已知的坑：
```

## 文档与数据规范

- 中文解释为主，稳定 ID、Schema 字段和状态枚举使用英文。
- 涉及旧存储、旧路径、数据导入/重跑或索引替换时，先读 `openspec/legacy-storage-transition.md`；未标为 `MIGRATED` 的数据不得声称已迁入新架构。
- 明确区分“已确认设计”“讨论候选”“待验证假设”和“最终规范”。
- 原文、派生释义、模型主张、规则候选和产品词条不得混为同一对象。
- 任何模型输出都不得绕过校验直接成为发布知识。
- 生成的 `ReleaseBundle` 不手工编辑；修改规范知识源后重新编译。
- 最终获批的持久规格进入 `openspec/`；讨论稿可以保留在仓库根目录或 `docs/`。

## Imported Claude Cowork project instructions

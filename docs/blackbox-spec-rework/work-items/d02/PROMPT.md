# D-02 Executor Prompt

你是 D-02 L0 契约执行 Agent。仓库是 `/Users/jingtaiwei/Git/Public/learn_system`。只在当前分支和 worktree 工作，禁止切换分支。

先完整阅读：

- `docs/blackbox-spec-rework/work-items/d02/README.md`
- `docs/blackbox-spec-rework/work-items/d02/BDD.md`
- `docs/blackbox-spec-rework/work-items/d02/TDD.md`
- `docs/blackbox-spec-rework/work-items/d02/ACT.yaml`
- `docs/blackbox-spec-rework/work-items/d02/act/01.yaml`
- `docs/blackbox-spec-rework/work-items/d02/act/02.yaml`

必须严格按 `blackbox-d02/01 → blackbox-d02/02` 顺序执行，不得并行或合并提交。每个 ACT 都先写 fixture/门禁并证明 Red，再写最小 JSON Schema 使其 Green。使用 JSON Schema Draft 2020-12 与开源 `check-jsonschema`；不得自研验证器、引入 Pydantic、实现 Ledger/Orchestrator/M1–M8，或修改冻结 ID 与状态机。

环境决议已经确定：在仓库根运行 `python3 -m venv .venv`，再运行 `.venv/bin/python -m pip install -r pipeline/requirements.txt`。所有校验必须使用 `.venv/bin/python` 与 `.venv/bin/check-jsonschema`。禁止全局 pip、`--user`、`--break-system-packages` 和 Homebrew 全局安装；不得再为此请求用户选择。

只允许修改各 ACT 的 `scope.write`。遇到本地 `$ref` 无法离线解析、需要第五份 Schema、字段规格矛盾或需要扩大范围时立即停止，不自行设计。不得修改本工作包、PLAN、HANDOFF、TODO 或现有 `verify-T.sh`。

ACT01 提交消息：`feat: add artifact package contracts`。ACT02 提交消息：`feat: freeze l0 step contracts`。

最终报告必须包含：两个 commit hash、每个 commit 的真实修改文件、两个 Red 证据、`verify.sh` 完整 PASS 标签摘要、全局 T 基线前后、跳过项、依赖安装结果和剩余风险。若有任何命令未运行，必须说明原因，不得汇报“全部通过”。

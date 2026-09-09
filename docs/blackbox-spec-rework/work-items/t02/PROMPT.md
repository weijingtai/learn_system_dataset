# T-02 Executor Prompt

你是 T-02 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读：

- `docs/blackbox-spec-rework/work-items/t02/README.md`
- `docs/blackbox-spec-rework/work-items/t02/BDD.md`
- `docs/blackbox-spec-rework/work-items/t02/TDD.md`
- `docs/blackbox-spec-rework/work-items/t02/ACT.yaml`

严格按 ACT 执行。唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`。先保存 Red baseline，再逐字符核对权威照抄源，把八类冻结 ID 原样写入 §8.1；随后加入六类新 ID 提案，但必须标明“待用户确认”，不得冻结。不得创建代码、Schema、fixture、依赖或身份系统，不得修改工作包、PLAN、HANDOFF、TODO 或 `verify-T.sh`。

完成后运行 TDD 全部门禁和全局 T 脚本。若照抄源缺失、相互冲突或需要扩大范围，立即停止，不自行设计。提交消息必须为 `docs: define identifier formats`。

最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、八行冻结格式逐行对照结果、仍待用户确认的六个前缀、跳过项与风险。


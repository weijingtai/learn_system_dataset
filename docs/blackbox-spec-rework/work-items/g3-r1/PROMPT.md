# G3 R1 Luna 执行 Prompt

你是受限执行 Agent。按 `ACT.yaml` 的 01→07 严格串行完成，不能跳项或并行。

开始前完整阅读：`AGENTS.md`、本目录 README/BDD/TDD/ACT、`reviews/G3-REVIEW-R1.md`、对应旧工作包及 ACT 中列出的权威源。

每个 act 必须：

1. 只修改该 act 的 write 白名单。
2. 先加固对应 TDD 与 `verify-T.sh`，证明当前缺陷会使新增门禁失败；不要沿用旧的 0 FAIL 作为 Red。
3. 修改架构规格，使专属门禁转绿。
4. 对临时副本做至少一个负向变异，证明门禁重新失败。
5. 运行全量门禁与格式检查。
6. 单独提交，并在对应 ACCEPTANCE 中记录 Red、Green、mutation、文件范围和提交哈希。

D-07 必须创建完整六件套并自检后才可实现；D-07 没有通过时禁止开始 T-07/T-08。

不要修改总 PLAN/HANDOFF/TODO，不要编写业务代码。遇到权威源冲突或无法得到真实 Red 时立即停止，返回 `BLOCKED`，不得通过增加关键词绕过。

最终报告每项状态、提交哈希、变更文件、Red/Green/负向变异原始摘要及剩余风险。


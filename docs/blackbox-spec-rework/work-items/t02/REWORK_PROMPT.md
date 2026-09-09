# T-02 最小返工 Prompt

你是 T-02 文档返工 Agent。仓库为 `/Users/jingtaiwei/Git/Public/learn_system`，在当前分支继续工作，禁止切换分支或进入其他 worktree。

第一轮提交为 `6e317cc0ddac36935fc2f34f5507ebc8cf1213a5`。八类冻结格式、其余五类新前缀、版本轴分离和原有机器门禁均已通过；不得重写或扩大范围。本轮只修复以下两个阻断项：

1. 将 `pkg_<stage>_<32hex>` 明确定义为 StagePackage 的逻辑身份（`stage_package_id`），而不是物理修订。修正同一个 StagePackage 时保留 `stage_package_id`，每个不可变版本另取新的 `artifact_revision_id=rev_<32hex>`。明确 StagePackage 的 ArtifactRef 同时携带 `stage_package_id` 与 `artifact_revision_id`。
2. 将 `<stage>` 明确冻结为 `m1`、`m2`、`m3`、`m4`、`m5`、`m6`、`m7`、`m8` 闭集；其他值非法。不得自行加入基础设施阶段。

同步删除或改写把 `pkg_<stage>_<32hex>` 当成 Content Revision／物理修订的所有表述。唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；不得修改 BDD、TDD、ACT、验收文档、TODO、PLAN、HANDOFF、Schema、代码或依赖。

完成后运行 `docs/blackbox-spec-rework/work-items/t02/TDD.md` 的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh` 和 `git diff --check`。全局仍应为 17 FAIL，T-02 与 T-02b 均 PASS。提交消息使用 `docs: clarify stage package identity`。

最终报告：commit hash、唯一修改文件、两个阻断项的逐项修复位置、全部门禁摘要、跳过项与剩余风险。

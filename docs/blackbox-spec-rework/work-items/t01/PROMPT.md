# T-01 Executor Prompt

你是 T-01 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t01/README.md`
- `docs/blackbox-spec-rework/work-items/t01/BDD.md`
- `docs/blackbox-spec-rework/work-items/t01/TDD.md`
- `docs/blackbox-spec-rework/work-items/t01/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 14 FAIL，T-01 为 FAIL）。
4. 在 `openspec/learn-system-blackbox-architecture.md` 写入以下两处修改：
   - **位置 1（`§5 总体组织`）**：在基础设施 `Contract Registry` 描述后追加：`schemas/shared/canon` 与 `schemas/shared/homographs` 由其登记并作为 M4 的冻结输入 Artifact。
   - **位置 2（`§12 M4 Knowledge Extraction`）**：在「M4 将 SemanticSpan 分别提取为候选」之前插入小节「12.1 术语判层前置步骤（三层模型）」，严格依照 `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md` §二与 §三 写入三层模型：
     - **L1 共享源数据层**：路径 `schemas/shared/canon/`，ID `co_shared_<domain>_NN`，闭集匹配；**必须在正文明确声明：L1 匹配为确定性字典匹配路径，不调用大模型（免模型），零成本直接命中**；
     - **L2 同形异义层**：路径 `schemas/shared/homographs/`，字面共享锚 `homograph_id=hg_<4位数字>`，各技法独立义项 `concept_id=co_<technique>_<6位数字>`；**必须在正文明确声明：命中时必须按当前技法选择对应义项绑定带技法的 concept_id，绝对禁止裸绑字面**；
     - **L3 技法独有层**：维持现存各技法表，ID `co_<technique>_<6位数字>`，未命中 L1/L2 的技法新词进入候选；
     - 将后续候选提取顺延为「12.2 知识候选提取」。
5. 完成后运行 `docs/blackbox-spec-rework/work-items/t01/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 14 严格减少至 13，且 T-01 为 PASS）以及 `git diff --check`。
6. 确认无误后提交修改，提交消息必须严格为：`docs: integrate three-tier terminology model into M4`。
7. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、三层模型与两处修改对比核查及全局 T 结果。

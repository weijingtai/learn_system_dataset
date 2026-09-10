# T-04 Executor Prompt

你是 T-04 文档执行 Agent。请在 `/Users/jingtaiwei/Git/Public/learn_system` 当前分支工作，禁止切换分支或进入其他 worktree。

先完整阅读并严格遵循：

- `docs/blackbox-spec-rework/work-items/t04/README.md`
- `docs/blackbox-spec-rework/work-items/t04/BDD.md`
- `docs/blackbox-spec-rework/work-items/t04/TDD.md`
- `docs/blackbox-spec-rework/work-items/t04/ACT.yaml`

【关键执行铁律与特别指示】：
1. 遇到任何照抄源冲突、规格歧义或意外失败，严禁自己做决定，必须立即停止并向上汇报！
2. 唯一允许修改的文件是 `openspec/learn-system-blackbox-architecture.md`；严禁修改任何代码、JSON Schema、测试、工作包文档、TODO、PLAN 或 `verify-T.sh`。
3. **【铁律：不得新造门禁名】**：全规格只允许出现 `G1`、`G2`、`G3`、`G4`、`G5`、`G6`、`G7` 这七个名字，绝对禁止自创新门禁代号。
4. 先保存 Red baseline（运行 `bash docs/blackbox-spec-rework/verify-T.sh` 并确认 13 FAIL，T-04/T-04b/T-04c 为 FAIL）。
5. 在 `openspec/learn-system-blackbox-architecture.md` 写入以下两处修改：
   - **位置 1（`§13 M5 Automatic Validation`）**：
     将 Validator 清单逐条对接 G1–G6，明确标注每条在 M5 执行还是延到 M8（依据 `DATASET_ACCEPTANCE_STANDARD.md §4`）：
     - G1 来源与可重放性：M5 执行（raw/transcript/patch/unit 哈希匹配、无未决字符、重放一致性）；
     - G2 全书覆盖：M5 执行（含正文 section 100% 覆盖、无重叠重复、拼接还原一致性、expected/actual 计数对账）；
     - G3 身份、引用与证据锚点：M5 执行（全局稳定 ID 无重复、无悬空引用、source offset 与 quote hash 锚点对账、evidence 范围校验、direct proposition 忠实性；OCR 扫描页/图像哈希/字框范围）；
     - G4 内容分层：M5 执行（命例入 Case 层、注文/异文/校勘入独立 editorial layer、条件/例外结构化、school_ids 不留空）；
     - G5 概念与检索：M5 执行（confirmed concept 声明引用/mentions/assertions/evidence 100% 对账、candidate concept 不得进入 release、检索正负例校验）；
     - G6 盘面确定性匹配：M5 执行（规则可执行性、FactSet AST/条件完整性）+ 延至 M8 执行（RuleIndexPack 与 SearchIndexPack 索引产出后复验）；
     - G7 状态、审查与发布：延至 M8 执行。
   - **位置 2（`§16 M8 Dataset Compilation`）**：
     - 在冻结项清单中追加显式输入参数：「消费级别（Consumption Level）」，取值限定为 `INTERNAL_DEMO` / `DEV_SEARCH` / `PUBLIC_RELEASE`；
     - 抄入原文强约束：「**编译器必须显式接收目标级别，并以 fail-closed 方式拒绝不满足条件的数据。不得由 APP 自行解释或绕过状态。**」；
     - 增加一张小表：「各消费级别的准入状态门槛」，直接引用 G7 的三条规则：
       - `INTERNAL_DEMO`：可展示 `machine_*`，但必须隔离并加水印；用于内部查看原句、调试定位；已知缺陷必须披露，不得声称全书完备或权威。
       - `DEV_SEARCH`：可判断内容至少为 `cross_model_reviewed`，否则只能作为原文候选展示；用于隔离的开发检索与接口联调；全源覆盖、引用图、索引正负例及 release/hash 一致性必须通过；未复核内容不得作为确定判断。
       - `PUBLIC_RELEASE`：所有可查询 assertions 必须为 `expert_verified`；机器态记录不得泄漏；用于正式 APP、用户查询与模型上下文；所有硬门禁通过，不得包含 candidate 或 dev 数据。
6. 完成后运行 `docs/blackbox-spec-rework/work-items/t04/TDD.md` 中的全部 Green checks、`bash docs/blackbox-spec-rework/verify-T.sh`（FAIL 数必须从 13 严格减少至 10，且 T-04、T-04b、T-04c 均 PASS）以及 `git diff --check`。
7. 确认无误后提交修改，提交消息必须严格为：`docs: connect consumption levels and G1-G7 gates`。
8. 最终报告必须包含：commit hash、真实修改文件、Red baseline、Green 原始摘要、G1–G7 对接与三级消费级别核验及全局 T 结果。

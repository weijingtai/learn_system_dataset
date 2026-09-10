# T-04 BDD 验收场景

## B1 M8 显式接收消费级别与 fail-closed 约束

Given 权威源 `pipeline/DATASET_ACCEPTANCE_STANDARD.md §3` 规定了消费级别机制，
When 执行者查看架构规格 §16 M8 Dataset Compilation，
Then 「消费级别」（Consumption Level）被列为 M8 编译的显式输入参数，取值限定为 `INTERNAL_DEMO`、`DEV_SEARCH`、`PUBLIC_RELEASE`，
And 规格正文明确声明：「编译器必须显式接收目标级别，并以 fail-closed 方式拒绝不满足条件的数据。不得由 APP 自行解释或绕过状态」。

## B2 各消费级别准入状态门槛对齐 G7

Given 权威源 `pipeline/DATASET_ACCEPTANCE_STANDARD.md §4-G7` 确立了各级别的状态准入门槛，
When 执行者查看架构规格 §16 M8 Dataset Compilation，
Then 规格包含三级消费级别的准入状态门槛表，直接对接 G7：
- `INTERNAL_DEMO`：可展示 `machine_*`，但必须隔离并加水印；用于内部查看原句与调试定位；已知缺陷必须披露，不得声称全书完备或权威。
- `DEV_SEARCH`：可判断内容至少为 `cross_model_reviewed`，否则只能作为原文候选展示；用于隔离的开发检索与接口联调；全源覆盖、引用图、索引正负例及 release/hash 一致性必须通过；未复核内容不得作为确定判断。
- `PUBLIC_RELEASE`：所有可查询 assertions 必须为 `expert_verified`；机器态记录不得泄漏；用于正式 APP、用户查询与模型上下文；所有硬门禁通过，不得包含 candidate 或 dev 数据。

## B3 G1–G6 门禁在 M5 与 M8 明确接线

Given 权威源 `pipeline/DATASET_ACCEPTANCE_STANDARD.md §4` 确立了 G1–G7 一票否决硬门禁，
When 执行者查看架构规格 §13 M5 Automatic Validation，
Then M5 的 Validator 清单逐条对接 G1 至 G6，且明确标注各自执行工位：
- G1（来源与可重放性）：M5 执行；
- G2（全书覆盖）：M5 执行；
- G3（身份、引用与证据锚点）：M5 执行；
- G4（内容分层）：M5 执行；
- G5（概念与检索）：M5 执行；
- G6（盘面确定性匹配）：M5 执行（规则可执行性）+ 延至 M8（索引产出后复验）；
- G7（状态、审查与发布）：延至 M8 执行；
And 全规格严禁新造其他门禁代号，只使用 G1–G7。

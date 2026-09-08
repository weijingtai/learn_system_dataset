# Pipeline 数据集验收标准（草案）

状态：`DRAFT_FOR_REVIEW`  
适用范围：非 OCR 与 OCR 书源进入 Learn System 后，从固定原始版本到可发布数据集的完整流水线。  
暂不包含：Embedding、Tag UI、社交与注解实现。

## 1. 为什么需要独立验收

“每个 unit 格式合法”不等于“整本书完整、语义正确、可被 APP 使用”。验收必须同时回答四个问题：

1. 原书有没有被完整收入，是否有章节被静默漏掉；
2. 每条派生知识能否准确回到同一处原文，而不是只证明这句话在书中某处出现过；
3. 条件、例外、命例、编者注文和流派信息有没有被放进正确的数据层；
4. 给定排盘事实时，系统能否返回全部且仅返回适用的知识。

任何单层 PASS 都不得替代全链发布验收。

## 2. 固定验收对象

每次验收必须冻结并记录以下完整链条：

```text
raw
→ transcript + deterministic patches
→ outline + batches
→ segments + spans
→ concepts
→ assertions + paraphrases
→ units
→ index
→ ReleaseBundle + ReleaseManifest
```

每一层必须有版本、内容哈希、生成工具版本、输入哈希和输出计数。发布物不可手工修改；知识源改变后必须重新编译。

## 3. 三种消费级别

| 级别 | 允许用途 | 最低要求 |
|---|---|---|
| `INTERNAL_DEMO` | 内部查看原句、调试定位 | 已知缺陷必须披露；机器态内容必须有水印；不得声称全书完备或权威 |
| `DEV_SEARCH` | 隔离的开发检索与接口联调 | 全源覆盖、引用图、索引正负例及 release/hash 一致性必须通过；未复核内容不得作为确定判断 |
| `PUBLIC_RELEASE` | 正式 APP、用户查询与模型上下文 | 所有硬门禁通过；可消费 assertion 必须专家签发；不得包含 candidate 或 dev 数据 |

编译器必须显式接收目标级别，并以 fail-closed 方式拒绝不满足条件的数据。不得由 APP 自行解释或绕过状态。

## 4. 一票否决的硬门禁

### G1 来源与可重放性

- raw、transcript、patch、task snapshot、unit、index、release 的哈希 100% 存在并匹配。
- 相同输入和工具版本重放后，所有签发产物哈希完全一致。
- 所有人工勘误必须进入确定性 patch/revision，不得只存在于某次模型输出。
- PUA、乱码占位符和未决字符为 0；经批准的不确定字必须显式登记，不得静默替换。

### G2 全书覆盖

- 每个含正文的 source section 必须恰好进入一个 batch；不得因标题层级静默排除。
- batch 字符覆盖率为 100%，且无重叠重复覆盖。
- 已签发 segments 按源顺序拼接后必须等于对应 source revision。
- 各层 expected/actual 计数必须对账；下游 100% 不能抵消上游漏编。

### G3 身份、引用与证据锚点

- 全局稳定 ID 无重复，所有引用无悬空，source/technique/revision 一致。
- 每个 span 必须有 source offset 或等价的确定性 anchor，以及 quote hash。
- 每条 assertion 的 evidence 必须位于所声明 span 内。
- direct proposition 不得引入原文没有且会改变含义的词；不忠实改写直接 FAIL。
- OCR 书源还必须能追到扫描页、图像哈希和 OCR 字框范围。

### G4 内容分层

- 命例只能进入 Case 层，不得被当作通则 assertion。
- 编者注文、异文和校勘说明必须进入独立 editorial layer。
- 条件、必要条件、加强条件、例外和反例必须结构化，不得只压在 proposition 文本里。
- `school_ids`、适用域和冲突信息不可在需要时留空。

### G5 概念与检索

- 每个 source/technique 分别验收，禁止其他书或其他技法的数据掩盖零命中。
- `confirmed` concept 的声明引用、mentions、assertions 和 evidence 必须逐项对账，召回率/精确率均为 100%。
- `candidate` concept 不得进入可消费 release。
- 每种查询必须有正例和负例；指定概念零命中、错误跨书命中或条件不满足仍命中均为 FAIL。

### G6 盘面确定性匹配

- 查询输入必须是版本化 `FactSet`，规则必须是可执行的 `ApplicabilityRule`，不能依赖自由文本猜测。
- 给定事实时，必须返回全部且仅返回适用规则，并说明已满足条件、缺失条件和触发例外。
- 任一条件不全或例外成立时，不得输出肯定判断。
- 代表性门禁至少覆盖首/中/末、十干十二月、十神/官杀、复杂条件、例外、命例和注文。

### G7 状态、审查与发布

- `INTERNAL_DEMO` 可展示 `machine_*`，但必须隔离并水印。
- `DEV_SEARCH` 的可判断内容至少为 `cross_model_reviewed`，否则只能作为原文候选展示。
- `PUBLIC_RELEASE` 中所有可查询 assertions 必须为 `expert_verified`；机器态记录不得泄漏。
- 任一 critical semantic error 直接阻断整批，并扩大到同风险簇全检。
- 正式发布必须包含 ReleaseManifest、unit/tool/dependency hashes、rights、审批快照和最低 APP 版本；`source_release=dev` 必须被拒绝。

## 5. 内容质量抽验

自动校验负责完整计数、哈希、重放、引用图、状态、字符异常、Case/Note 分层和查询正负例；它不能代替语义复核。

跨模型盲审至少抽取 `max(200, 10%)` 条 assertions，并按首/中/末、干月组合、十神/官杀、复杂条件、例外、命例、注文分层。审阅者不得看到原生成模型或既有 verdict。公开发布前：

- critical error 必须为 0；
- major error rate 必须不高于 0.5%，且 95% 置信上界满足门槛；
- assertions 逐条由领域专家签发；
- paraphrase 至少全检高风险段，并分层随机复核 20%；
- 所有失败项修复后必须重新运行同一批门禁。

## 6. 必须通过的行为场景

1. 给定固定 raw 和转换器版本，全链重放产生完全相同的 transcript 与下游哈希。
2. 给定任一含正文 section，生成 coverage 后它恰好属于一个 batch。
3. 给定任一 assertion，可唯一追到 unit、span、source offset、quote hash 和 release。
4. 给定任一断裂的 ID、哈希、状态或引用，ReleaseCompiler 拒绝发布。
5. 给定 `丙日干 + 亥月` FactSet，返回全部且仅返回适用的十月丙火规则，并保留必要条件与反例。
6. 给定官杀等 confirmed concept，返回声明 spans、相关 assertions 和 evidence；该书/技法零命中即失败。
7. 给定条件不全或例外成立的规则，不返回肯定判断。
8. 给定命例或编者注文，编译后分别只出现在 Case 或 editorial layer。
9. 给定改变原意的 proposition，direct evidence 校验失败。
10. 给定 index 与 units 不同 release/hash，APP adapter 拒绝启动或装载。

## 7. 每次验收必须固化的证据

- Git commit、source/release ID，以及 raw/transcript/patch/task/unit/index hashes；
- 每层 expected/actual counts、字符覆盖率和重复覆盖报告；
- validator 精确命令、工具版本、退出码和原始日志；
- 全局 ID/引用图和所有负例执行结果；
- 盲审样本、随机种子、双模型独立判定和仲裁记录；
- 专家身份、签发范围、错误分类和复验结果；
- 首/中/末、丙亥、官杀、条件/例外、命例/注文的查询快照；
- waiver 的负责人、到期时间和被禁止的消费级别。

## 8. 《穷通宝鉴》当前基线（2026-09-08）

当前判定：`NOT_READY`。

- manifest 登记 transcript `body_chars: 31635`，outline 只登记 `total_chars: 29251`；两者口径差 2,384 字，已定位到《论木》《论火》《论土》《论水》等带正文的二级章节被 outline 生成规则排除。按源文重算约 7.5% 未进入下游。
- 137 个八字 units 能通过现有 unit validator，但这只证明局部结构与“引文在整本 transcript 某处存在”，不能证明全书覆盖或 assertion 语义正确。
- SQLite 的 13 条 mentions 全属于奇门；八字 concept mentions 为 0。现有 RAG validator 只检查全库非空，因而仍然 PASS。
- 1,317 条八字 assertions 全为 `machine_extracted`；138 条 paraphrases 全为 `machine_translated`；没有八字专家签发记录。
- 已抽到漏主张、不忠实改写、命例误提、编者标记未分层、条件/例外埋在自由文本等确定性问题。
- “十月丙火”可以按原文或 assertion ID 定位，但尚无 `BaziFactSet + ApplicabilityRule`，不能支持 APP 对“丙日干 + 亥月”的确定性完整召回。

因此当前数据只允许限域内部演示；修复全书覆盖和索引前不得称为开发检索数据集，完成结构化规则、语义复核、专家签发与正式 ReleaseBundle 前不得进入公开 APP。

## 9. 最小修复顺序

1. 修复 outline 选择规则，补齐全部漏编正文，并冻结 100% source/batch/segment coverage 基线。
2. 把 PUA 勘误纳入可重放 source revision，刷新 task snapshots 与签发 segments。
3. 修复完整 span ID 的 concept 索引，按八字 118 concepts / 152 声明引用逐项对账。
4. 增加 proposition↔quote、Case 排除、editorial layer、条件/例外结构化的 fail-closed validator。
5. 对既有 assertions/paraphrases 分层盲审，清理已确认的漏主张、改写和命例误提。
6. 定义并实现 `BaziFactSet`、`ApplicabilityRule` 和“丙日干 + 亥月”验收 fixture。
7. 领域专家签发后，通过 KnowledgeReleaseCompiler 生成正式 ReleaseBundle，才允许 APP 消费。

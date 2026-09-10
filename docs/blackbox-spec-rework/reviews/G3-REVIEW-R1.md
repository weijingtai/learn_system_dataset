# G3 T 类转录交叉验收 R1

日期：2026-09-09
结论：`REWORK_REQUIRED`

## 独立证据

- `bash docs/blackbox-spec-rework/verify-T.sh`：退出 0，显示 0 FAIL；但下列语义核查证明存在字符串假绿。
- `git diff --check`：退出 0。
- T-01 至 T-13 的 12 个实现提交均只修改 `openspec/learn-system-blackbox-architecture.md`，提交范围合规。
- 72 份 G3 六件套文件在验收时仍未被 Git 跟踪；T-13 的 Acceptance 仍为 `READY`。

## 逐项结论

| 工作项 | R1 结论 | 摘要 |
|---|---|---|
| T-01 | PASS | L1/L2/L3、ID、冻结输入、确定性路径与禁止裸绑完整。 |
| T-03 | PASS | 内容状态、错误码、八类审核及 D-03 两套状态机完整且无回退。 |
| T-04 | FAIL | 未按权威源完整接入 G1–G7；门禁只检查代号和少数关键词。 |
| T-05 | PASS | 两档 evidence_level 与 PUBLIC_RELEASE 门槛完整。 |
| T-06 | FAIL | 无损链遗漏 KnowledgeEntry，并倒置 Assertion 与 EvidenceLink。 |
| T-07 | FAIL/BLOCKED | 违反 D-07 前置；query-contract 被提前错归到两个 IndexPack。 |
| T-08 | FAIL/BLOCKED | 违反 D-07 前置；把只校验的 M5 写成字段生产者，并混用两套 G4 编号。 |
| T-09 | PASS | 六项查询、五队列与进度事件上报完整。 |
| T-10 | PASS | 三种异常页终态、证据要求及放行/阻断规则完整。 |
| T-11 | FAIL | 多项“当前事实”和文件路径已经错误，且所谓必 FAIL 判据并不可判定。 |
| T-12 | PASS | L0/L1/L2/Module 拓扑、层级列与施工顺序说明完整。 |
| T-13 | FAIL | 漏掉 §16 建议句的局部“讨论候选”标注；门禁只统计标签数量。 |

## 可机械执行的返工项

- [ ] T-04 修复：按 `pipeline/DATASET_ACCEPTANCE_STANDARD.md:50-99` 将 G1–G7 的全部强制语义接入 §13/§16，包括全链哈希、确定性 patch/revision、source/technique/revision 一致、适用域与冲突、逐 source/technique 验收、全部且仅返回适用规则、已满足/缺失/例外说明、风险簇全检、完整 ReleaseManifest、最低 APP 版本及拒绝 `source_release=dev`。｜通过标准：上述语义逐项章节限定断言；临时删除任一项时门禁必须失败。
- [ ] T-04 加固：重写 `work-items/t04/TDD.md` 和 `verify-T.sh` 的 T-04 判据，增加 G1–G7 名称闭集与完整语义探针。｜通过标准：仅保留 G1–G7 标题或少数摘要时必红，完整内容时才绿。
- [ ] T-06 修复：把 §16 证据链改为 `KnowledgeEntry → Assertion → EvidenceLink → SourceSpan → SourceAnchor → OcrPage / 字框坐标 → SourceAsset 页标识`。｜通过标准：在 §16 限定区间按该顺序一次性匹配成功。
- [ ] T-06 加固：修正 `work-items/t06/TDD.md` 中固化错误顺序的断言。｜通过标准：缺 KnowledgeEntry、交换 Assertion/EvidenceLink 或删除终点任一情况均失败。
- [ ] T-07 前置：先完成并验收 D-07 `TechniqueProfilePack / QueryContractPack`。｜通过标准：D-07 状态为 ACCEPTED，且 `QueryContractPack` 含 `getEntry/getSourceSpan/searchKnowledge/matchFacts`。
- [ ] T-07 修复：D-07 完成后将 §16.2 的 `query-contract` 映射至 `QueryContractPack`。｜通过标准：只解析 §16.2 表，15 项各出现且仅出现一次，query-contract 的唯一归属正确。
- [ ] T-08 修复：D-07 完成后重新接线 Tag 接口；M5 只作为 Validator，不得列为 `omen_carrying` 或 `condition_affordance` 的生产 Module。｜通过标准：§16.3 生产 Module 列不存在 M5，校验职责另列。
- [ ] T-08 修复：把 Tag 侧 G4 写成“`TAG_SYSTEM_DESIGN.md §12.2` 的 G4 依赖倒挂问题”，不得与本规格 G4 内容分层门禁混同。｜通过标准：两个 G4 的命名空间和含义可由机器分别定位。
- [ ] T-08 加固：将 TDD 改为 §16.3 区间内逐接口、逐字段、生产 Module、子包归属及 M5 负断言。｜通过标准：字段重复堆砌或错误 Module 不能通过。
- [ ] T-11 修复：§19 将不存在的 `tools/ingest_epub.py` 改为真实的 `pipeline/tools/ingest_epub.py`。｜通过标准：前者不存在、后者存在，规格只引用后者。
- [ ] T-11 修复：更新已被 G2 消除的私有依赖、启动覆盖、保存即 verified 和“仅 1 个测试”陈述；当前 tracked 非 OCR 测试为 3 个。｜通过标准：规格不再把四项旧事实写成当前缺口，命令排除 `.venv` 并与 HEAD 一致。
- [ ] T-11 加固：为每一条仍存在的差距提供“当前非零、修好归零”或等价二元断言。｜通过标准：任何事实改变而规格未同步时门禁失败；观察型命令不得冒充 PASS/FAIL 判据。
- [ ] T-13 修复：在 §16 的“建议一个 Technique 一个 Release”处单独标明 `状态：讨论候选`，不改变 §16 章节级状态。｜通过标准：对该句上下文的局部状态断言成功。
- [ ] T-13 加固：门禁逐节校验 §3–§18 的章节号→期望状态映射，并检查 §16 局部候选。｜通过标准：任一节错标、漏标或删除局部候选均失败。

## 归档判定

G3 当前不得标记完成。T-04、T-06、T-11、T-13 完成返工，且 D-07 → T-07 → T-08 严格完成后，必须重新运行全量交叉验收；`verify-T.sh = 0` 只是必要条件，不是充分条件。

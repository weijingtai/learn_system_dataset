# T-07 KnowledgePack ↔ PublicationPackage 双向映射表转录：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

在架构规格 `§16 M8 Dataset Compilation` 末尾新增 `16.2 KnowledgePack 与 PublicationPackage 双向映射表`，消除历史草案与现行黑箱架构之间的概念歧义：
1. 完整对照 `LEARN_SYSTEM_TARGET.md §9`（行 185-202）中定义的 KnowledgePack 全部 14/15 个目录；
2. 逐项明确其在现行 `PublicationPackage` 八个子包中的归属，不得留空行；
3. 对于暂未产出的项目（如 `optional-vector-index`），显式标注「本期不产出（依据 §21）」；
4. 明确写入概念取代声明：架构规格以结构化的 `PublicationPackage`（及核心子包 `KnowledgeDataPack`）正式取代早期草案中扁平单一的 `KnowledgePack` 概念。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-07
- `LEARN_SYSTEM_TARGET.md §9`（行 185-202，KnowledgePack 目录结构）
- `openspec/learn-system-blackbox-architecture.md` §16 与 §21
- `docs/blackbox-spec-rework/verify-T.sh`（T-07 判据）

## Dependencies

- T-06：已 `ACCEPTED`；
- T-05：已 `ACCEPTED`；
- T-04：已 `ACCEPTED`；
- 本任务与后续 T 类修改同一架构规格，必须严格串行派发。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：`§16 M8 Dataset Compilation` 末尾（在 §17 之前新增 16.2 小节）。

## Forbidden

- 严禁遗漏 TARGET §9 中 14/15 项目录中的任何一项（`release-manifest`, `schema`, `concepts`, `entries`, `assertions`, `applicability-rules`, `school-views`, `evidence-links`, `source-spans`, `source-anchors`, `scan-assets-or-references`, `exact-search-index`, `fulltext-index`, `optional-vector-index`, `query-contract`）。
- 严禁留空行，无归宿项必须明确标注「本期不产出（依据 §21）」。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源目录名与架构已有子包存在归属矛盾；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；完整转录 TARGET §9 十五个条目，无遗漏、无擅自变更名称。
- **可执行性**：通过；唯一定位点（§16 末尾），映射表与取代声明明确。
- **可验收性**：通过；覆盖全部 10 个 grep 检验关键字，验收后 FAIL 总数由 8 严格降为 7。
- **防越界性**：通过；单文件写作用域，禁止代码与依赖改动。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。

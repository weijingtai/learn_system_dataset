# T-08 Tag 区三个耦合接口与字段承接转录：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

依据 `tag_system/README.md:30-32` 与 `tag_system/TAG_SYSTEM_DESIGN.md`，在黑箱架构规格中完整承接与 Tag 系统交互的三个耦合接口及五个关键字段：
1. **三个耦合接口承接**：
   - `最小盘面概念字典`：规模约 100–200 个概念，仅含稳定 ID + 名称 + 基础类象，**严格声明不含规则 DSL**，由 `KnowledgeDataPack` 供给，解决 G4 依赖倒挂；
   - `MarkContentBinding` 内容供给：提供吉凶、条件与流派分歧展示字段，由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给；
   - `EvidenceBundle` 服务：由 `EvidenceMapPack` 供给，为 AI 解盘和端侧证据交互提供底层无损证据链切片。
2. **五个关键字段归属与明确**：
   - `omen_carrying`（吉凶承载性）
   - `condition_affordance`（条件可供性）
   - `school_variance_display`（流派分歧展示）
   - `concept_id`（概念标识）
   - 「是否改变当前判断」（内容状态字段，由知识层供给，UI 不得猜测）
3. 规格落点：
   - `§1 系统边界`：在边界描述处明确声明对外部 Tag 系统的三个承接接口；
   - `§16 M8 Dataset Compilation`：新增小节定义三接口在 PublicationPackage 中的产出承载点与字段矩阵。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-08
- `tag_system/README.md` 行 30-32
- `tag_system/TAG_SYSTEM_DESIGN.md` 行 222-225、307、438
- `openspec/learn-system-blackbox-architecture.md` §1 与 §16
- `docs/blackbox-spec-rework/verify-T.sh`（T-08, T-08b 判据）

## Dependencies

- T-07：已 `ACCEPTED`；
- T-06：已 `ACCEPTED`；
- 本任务与后续 T 类修改同一架构规格，必须严格串行派发。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：
  1. `§1 系统边界`：补充对 Tag 系统的三接口承接声明；
  2. `§16 M8 Dataset Compilation`：新增 16.3 小节，承接 Tag 系统三个接口与关键字段映射表。

## Forbidden

- 严禁篡改字段名（`omen_carrying`、`condition_affordance`、`school_variance_display`）。
- 严禁丢掉「最小盘面概念字典约 100–200 个概念，仅稳定 ID + 名称 + 基础类象，**不含规则 DSL**」这条硬限制。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源字段定义与架构已有定义冲突；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；直接原样搬运 Tag 系统设计文档中的三个接口定义与五个字段名。
- **可执行性**：通过；两个落点（§1 与 §16），命令与判据确定。
- **可验收性**：通过；覆盖 T-08 与 T-08b 两项机器判据，验收后全局 FAIL 数由 7 降至 5。
- **防越界性**：通过；单文件写作用域，禁止代码与依赖改动。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。

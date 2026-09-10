# T-05 evidence_level 枚举转录：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

将证据精细度级别 `evidence_level` 两档枚举写入黑箱架构规格，并确立其与消费级别的强约束关系：
1. 枚举两档：
   - `offset_level`（通用档：source offset + quote hash）
   - `glyphbox_level`（扫描档：追加扫描页 + 图像哈希 + OCR 字框四点范围）
2. 写入可发布性强结论：
   - `offset_level` 仅作为开发级证据，只可用于 `INTERNAL_DEMO` 与 `DEV_SEARCH`；
   - `PUBLIC_RELEASE` 必须达到 `glyphbox_level`（依据 `LEARN_SYSTEM_TARGET.md:140`：「纯文本引用只能算开发级证据，不能算最终无损证据链」）。
3. 规格落点：`§11 M3 Corpus Compilation` 末尾新增 11.1 子节，并在 `§13 M5 Automatic Validation` 的 G3 门禁条件中体现。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-05
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md` §4-G3
- `LEARN_SYSTEM_TARGET.md` 行 140
- `openspec/learn-system-blackbox-architecture.md` §11 与 §13
- `docs/blackbox-spec-rework/verify-T.sh`（T-05 判据）

## Dependencies

- T-04：已 `ACCEPTED`，三级消费级别与 G1–G7 门禁已建立；
- T-03：已 `ACCEPTED`；
- T-01：已 `ACCEPTED`；
- 本任务与后续 T 类修改同一架构规格，必须严格串行派发。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：
  1. `§11 M3` 末尾：增加「11.1 证据级别枚举（evidence_level）与发布约束」；
  2. `§13 M5`：在 G3 Validator 描述与校验标准中明确加入 `evidence_level` 校验条件（`offset_level` vs `glyphbox_level`）。

## Forbidden

- 严禁擅自发明第三种 `evidence_level` 取值。
- 严禁降低 `PUBLIC_RELEASE` 的证据要求（不得允许仅凭纯文本 offset 发布公开包）。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源与架构已有章节出现冲突；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；严格按照 `DATASET_ACCEPTANCE_STANDARD.md §4-G3` 与 `LEARN_SYSTEM_TARGET.md:140` 转录。
- **可执行性**：通过；两个明确修改落点（§11 与 §13），命令与预期清晰。
- **可验收性**：通过；对应 `verify-T.sh` 的 T-05 判据，验收后 FAIL 总数由 10 降为 9。
- **防越界性**：通过；单文件只写规范，禁止代码与依赖变更。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。

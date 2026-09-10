# T-06 EvidenceMapPack 内容定义转录：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

依据 `LEARN_SYSTEM_TARGET.md §6`（行 130-138）与 `pipeline/DATASET_ACCEPTANCE_STANDARD.md §4-G3`，在架构规格 `§16 M8 Dataset Compilation` 的 PublicationPackage 子包清单下为 `EvidenceMapPack` 补充明确的内容与约束说明：
1. 逐段写出完整无损证据链：`EvidenceLink → Assertion → SourceSpan → SourceAnchor → OcrPage / 字框坐标 → SourceAsset 页标识`；
2. 写入坐标系硬约束：字框坐标系必须与 `SourceAssetPack` 中页图的像素尺寸同源可换算（保证客户端可精确定位与高亮）；
3. 写入门禁约束：该链路的完整性是 `ValidationReport` 的 fail-closed 检查项；
4. 明确禁止将 SourceAnchor 仅留在 M3 内部而不进发布包。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-06
- `LEARN_SYSTEM_TARGET.md §6`（行 130-138）
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md §4-G3`
- `openspec/learn-system-blackbox-architecture.md` §16
- `docs/blackbox-spec-rework/verify-T.sh`（T-06 判据）

## Dependencies

- T-05：已 `ACCEPTED`；
- T-04：已 `ACCEPTED`；
- 本任务与后续 T 类修改同一架构规格，必须严格串行派发。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：`§16 M8 Dataset Compilation`，在 PublicationPackage 结构树下方为 `EvidenceMapPack` 添加详细内容与约束说明。

## Forbidden

- 严禁将 SourceAnchor 仅作为 M3 内部中间体而不在发布包中提供。
- 严禁遗漏坐标同源可换算与 fail-closed 门禁要求。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源链路定义与架构规格存在冲突；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；完整转录 `LEARN_SYSTEM_TARGET.md §6` 的六段证据链条与 `DATASET_ACCEPTANCE_STANDARD §4-G3` 约束。
- **可执行性**：通过；唯一定位点（§16 PublicationPackage 说明），命令与判据确定。
- **可验收性**：通过；对应 `verify-T.sh` 中 T-06 判据，验收后全局 FAIL 数由 9 降至 8。
- **防越界性**：通过；单文件写作用域，禁止代码与依赖改动。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。

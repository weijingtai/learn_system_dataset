# T-10 M2 异常页终态枚举转录：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

依据 `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-10 规范，在黑箱架构规格 §10 M2 末尾完整转录异常页的三种终态枚举及 M2 Gate 放行规则：
1. **三种终态枚举**：
   - `manually_transcribed`（人工转录完成）：由人工介入录入或修正，具备完整文本与对应元数据；
   - `known_unrecognizable`（已知客观不可识别）：如纯图、无文本页、严重残卷或手绘盘面图（证据见 `ocr/data_work/logs/anomalies.jsonl` 中登记的 page_002 无文本、page_010 盘面页），必须附理由与证据 Artifact，严禁裸标；
   - `deferred`（暂缓处理/未决）：暂未处理或等待后续工具链支持（如弧线字切分原型 `ocr/experiments/curve_segment.py` 尚未完成生产化接入）。
2. **M2 Gate 放行与阻断规则**：
   - `manually_transcribed` 与 `known_unrecognizable` 允许 M2 Gate 放行；
   - `deferred` 严格阻断 M2 Gate 通过，禁止推进到 M3；
   - 规则与理由声明：这与 §6.1「失败为零」原则不冲突，因为「客观不可识别」属于已受控登记的输入边界局限，不是加工流程执行失败；
   - 严禁将任何异常页静默跳过或绕过 Gate。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-10
- `ocr/data_work/logs/anomalies.jsonl`
- `openspec/learn-system-blackbox-architecture.md` §10
- `docs/blackbox-spec-rework/verify-T.sh`（T-10 判据）

## Dependencies

- T-09：已 `ACCEPTED`；
- 本任务与后续 T 类修改同一架构规格，必须严格串行派发。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：`§10 M2 Digitization & Correction` 末尾（增加子节「10.1 异常页终态枚举与 M2 Gate 放行规则」）。

## Forbidden

- 严禁允许 `deferred` 状态放行 M2 Gate。
- 严禁允许裸标 `known_unrecognizable`（必须附理由与证据 Artifact）。
- 严禁静默跳过异常页。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源与现有 §10 描述存在冲突；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；直接原样转录三种终态枚举与 M2 Gate 放行/阻断条件。
- **可执行性**：通过；落点明确位于 §10 末尾，命令与判据确定。
- **可验收性**：通过；对接 `verify-T.sh` 中的 T-10 判据，验收后全局 FAIL 数由 4 降至 3。
- **防越界性**：通过；单文件写作用域，禁止代码与依赖改动。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。

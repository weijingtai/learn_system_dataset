# T-13 §3–§18 逐节加状态标签：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

依据 `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-13 规范与 `AGENTS.md:39` 要求，在黑箱架构规格 `§3` 至 `§18` 的每个二级章节标题下一行统一添加状态标签：
1. **状态标签四态体系**：
   - `已确认设计`
   - `讨论候选`
   - `待验证假设`
   - `最终规范`
2. **标签判定规则（严格对照，严禁自由发挥）**：
   - 已在 `§2 已确认原则` 中有对应条目的章节 → `状态：已确认设计`（§5, §6, §18）
   - 本轮 R1 返工正在改动的章节（§4, §7, §8, §10, §11, §12, §13, §14, §16, §17）→ `状态：待验证假设`
   - `§16` 那句「建议一个 Technique 一个 Release」→ 单独标 `讨论候选`
   - 其余章节（§3, §9, §15）→ `状态：讨论候选`
3. **铁律限制**：
   - **绝对禁止将任何一节标注为 `最终规范`**（整份架构规格尚未正式获批）。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-13
- `openspec/learn-system-blackbox-architecture.md` §3–§18
- `docs/blackbox-spec-rework/verify-T.sh`（T-13, T-13b 判据）

## Dependencies

- T-12：已 `ACCEPTED`；
- 本任务为 G3 阶段 T 类转录的收尾任务。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：`§3` 至 `§18` 各二级标题（`## `）下一行。

## Forbidden

- 严禁将任何章节标注为 `最终规范`。
- 严禁漏加任何一个章节（§3 到 §18 共 16 个章节必须全部包含）。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 章节标题缺失或序号错乱；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；完全原样遵循 T-transcribe.md 规定的四态映射规则。
- **可执行性**：通过；16 个章节位置明确，逐节加标签。
- **可验收性**：通过；对接 `verify-T.sh` 中的 T-13 与 T-13b 判据，验收后全局 FAIL 数降至 0。
- **防越界性**：通过；单文件写作用域，禁止代码与依赖改动。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。

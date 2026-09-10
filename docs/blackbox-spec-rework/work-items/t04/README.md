# T-04 三级消费级别与 G1–G7 门禁接线：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

将三级消费级别与 G1–G7 一票否决硬门禁体系完整接线至黑箱架构规格：
1. 在 `§16 M8 Dataset Compilation` 输入参数中将「消费级别」列为显式输入参数（取值 `INTERNAL_DEMO` / `DEV_SEARCH` / `PUBLIC_RELEASE`），并写入「编译器必须显式接收目标级别，并以 fail-closed 方式拒绝不满足条件的数据」强约束；
2. 在 `§16` 建立各消费级别的准入状态门槛表，直接引用 G7 的三级判定规则；
3. 在 `§13 M5 Automatic Validation` 建立 Validator 清单，逐条对应 G1–G6，并明确标注每条在 M5 执行还是延到 M8（G1–G5 在 M5，G6 在 M5+M8，G7 在 M8）。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-04
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md` §3（三级消费级别）与 §4（G1–G7 全文）
- `openspec/learn-system-blackbox-architecture.md` §13 与 §16
- `docs/blackbox-spec-rework/verify-T.sh`（T-04, T-04b, T-04c 判据）

## Dependencies

- T-03：已 `ACCEPTED`，内容成熟度 7 值与审核类型已冻结；
- T-01：已 `ACCEPTED`，三层术语模型已就绪；
- 本任务修改 `openspec/learn-system-blackbox-architecture.md`，执行必须与后续任务严格串行。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：
  1. `§13 M5 Automatic Validation`：将 Validator 清单逐条对接 G1–G6 门禁，标注执行工位（M5 或 M8）；
  2. `§16 M8 Dataset Compilation`：在冻结项中追加显式输入参数「消费级别」及 fail-closed 约束，并增加三级消费级别的准入状态门槛表（引用 G7）。

## Forbidden

- 严禁新造任何门禁名称；全规格只允许出现 G1、G2、G3、G4、G5、G6、G7 这七个代号。
- 严禁擅自修改三种消费级别的名称（`INTERNAL_DEMO`, `DEV_SEARCH`, `PUBLIC_RELEASE`）。
- 严禁遗漏 `fail-closed` 强制声明。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源与架构已有章节出现分配冲突；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；直接原样转录 `pipeline/DATASET_ACCEPTANCE_STANDARD.md` §3 与 §4，无自行发明门禁代号。
- **可执行性**：通过；两个明确落点（§13 与 §16），指令确定。
- **可验收性**：通过；涵盖 T-04（G1–G7 全收录）、T-04b（三级消费级别）、T-04c（fail-closed 声明），验收后全局 FAIL 数从 13 下降至 10。
- **防越界性**：通过；单文件写作用域，禁止代码与依赖改动。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。

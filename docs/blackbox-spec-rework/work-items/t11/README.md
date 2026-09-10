# T-11 §19 差距表修正三行低估 + 补十二项遗漏：执行工作包

状态：`READY`（已按标准六件套建立，等待串行派发执行 Agent）

## Goal

依据 `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-11 规范，在黑箱架构规格 `§19` 差距表格中修正三行低估并补充十二项遗漏：
1. **修正三行低估（写入实测精确数字）**：
   - `M1`：当前实现补充 `pipeline/registry/works/`、`tools/ingest_epub.py`；当前差距补充「转录不可由记录的 raw+tool 重放」；
   - `M6`：补充数据体全空实测数字：`496 rules`，`original_text` 非空 0，`is_verified=1` 为 0，`ge_ju_versions` 0 行，`conditions` 404，`chapter` 486；
   - `M8`：将「零命中假绿」改为「span→mentions 映射键碰撞：`148` span 塌缩为 18 键、6 组碰撞，修好解析后将链到错误页」。
2. **补充八项/十二项遗漏行（附判据命令）**：
   - 工作台唯一键 `{patternId, schoolId}` 禁止多书多主张
   - `ge_ju_schools` 把 book(1) 与 school(2) 混存同表
   - 干净环境不可构建（依赖内网）
   - 启动覆盖本地库 + 保存即 verified（已在 R0 排期消除）
   - 测试宿主匮乏：全仓非 OCR 部分仅 1 个 748B 脚手架
   - goldens 只有 bazi/qtbj，无非八字 fixture
   - OCR R7 横排分支取轴错误
   - `pipeline/TODO.md:12-14` 三项 P0 语义阻断（忠实性门禁、命例/注文/通则分层、条件例外结构化）
3. **反向排除说明**：
   - `pipeline/requirements.txt` 已存在且含环境自检，PLAN.md 中「pipeline 无依赖声明」的旧表述已不成立，严禁计入遗漏。

## Authority

- `docs/blackbox-spec-rework/T-transcribe.md` 中的 T-11
- `openspec/learn-system-blackbox-architecture.md` §19
- `docs/blackbox-spec-rework/verify-T.sh`（T-11 判据）

## Dependencies

- T-10：已 `ACCEPTED`；
- 本任务与后续 T 类修改同一架构规格，必须严格串行派发。

## Scope

- WRITE：仅 `openspec/learn-system-blackbox-architecture.md`
- 规格落点：`§19 当前实现映射与差距` 表格。

## Forbidden

- 严禁篡改实测数字（`496`、`148`、`18 键`）。
- 严禁将「pipeline 无依赖声明」写入遗漏（`pipeline/requirements.txt` 已存在）。
- 严禁修改任何代码、JSON Schema、测试、数据库文件、PLAN、TODO 或 `verify-T.sh`。

## Stop conditions

遇到以下情况必须立即停止并向上汇报：
1. 照抄源与现有 §19 结构冲突；
2. Green checks 未通过或全局回归出现未预期退化；
3. 发现需要修改单文件作用域之外的任何文件。

## ACT review（wjt-react 四查）

- **忠实性**：通过；完全原样转录 T-transcribe.md 审查核准的实测数字与遗漏项。
- **可执行性**：通过；直接修改 §19 表格，实测数字与行数判据明确。
- **可验收性**：通过；对接 `verify-T.sh` 中的 T-11 判据，验收后全局 FAIL 数由 3 降至 2。
- **防越界性**：通过；单文件写作用域，禁止代码与依赖改动。

结论：工作包六件套完备，符合 G0 交付门禁，状态置为 `READY`。

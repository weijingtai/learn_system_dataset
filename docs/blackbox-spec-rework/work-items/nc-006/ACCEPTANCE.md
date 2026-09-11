# NC-006 独立验收

当前：NOT_EXECUTED。派发前置：NC-005 ACCEPTED。

1. ACT 审查：未参与编写者做 wjt-react 四查；本文不自签 READY。
2. 范围：`reading-notes` 新增恰 3 个提交（在 NC-005 四个之后），`git show --name-only` 逐一核对只含各 ACT WRITE_NEW；TDD 命令 7 的 diff 为空；`pubspec.yaml`/`pubspec.lock` 零变化；`note_editor_page_test.dart` 的 diff 只涉及一个测试（`testWidgets(` 计数不变，删除行含 `no shortcuts registered by page`，新增行含 `shortcuts and actions wrap only the body field`）。
3. 重跑 TDD §1 全部 10 条命令并记录退出码：`flutter test` `+110: All tests passed!`；`nc006_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时测试文件，不入库）：① 间隔恰 `undoMergeMaxGapMs` 毫秒开新单元、少 1 毫秒并入；② 第 `undoMergeMaxChars` 个 code point 并入、下一个开新单元，混入一个 4 字节 emoji 仍按 code point 计；③ 全角空格 U+3000 与制表符 `\t` 作为片段自成封闭单元（`\s` 语义）；④ 页面上 Ctrl+Z 一次后用 `TextEditingController` 监听计数与 `undoCount` 双重断言不双撤销，且 Android 平台（`debugDefaultTargetPlatformOverride = android`）Ctrl+Z 同样生效；⑤ 组合中收到 `undo()`：契约未定义时按「组合中 undo 为 no-op」验证 adapter 不抛异常并把结果写入决定登记；⑥ 撤销后 2000 ms 自动保存的快照文本与撤销后 `TextEditingController.text` 相同。
5. 作弊扫描：adapter 无 `DateTime.now(`/`Timer(`/`Stopwatch(`/字面量 500、20；`lib/src/editor/` 无 `UndoHistoryController`；`Shortcuts(` 恰在页面出现 1 次；测试无 `skip`、`expect(true`。
6. 流程核对：每个提交同时含测试与实现；报告给出真实 Red 原文；act/02 一开始即绿的测试有解释。
7. 通过后只验收 NC-006；D-NC006-06（iOS 原生 UndoManager）登记到 NC-024 的设备级验收清单，不在本包关闭。

证据记录格式：commit；实际文件；每条 command/exit_code/原始摘要；Red 原文；盲测输出；跳过项与剩余阻塞。

## 验收记录 R1（主 Agent，2026-09-11）：act/01～03 通过，追加 act/04 返工

- 提交：reading-notes `afbe3a0`（A）、`bc6435b`（B）、`4966924`（C），恰 3 个；保护文件 diff 为空；`pubspec` 零变化；`note_editor_page_test.dart` 只改指定的一个测试（`testWidgets(` 仍 6）；控制器只改 `applySnapshot`（报告 2.3 节写明原语义与新语义）。
- 守卫 `nc006_guard.sh --require-impl`（当时版本）K01～K05 全 PASS：analyze 0，`flutter test +110`，adapter 无字面量/裸时间，`Shortcuts(` 恰 1，无 `UndoHistoryController`，作弊模式无。
- 报告：三步 Red 原文齐全；act/02 8 个测试中 7 个一开始即绿并逐个解释（栈不受控制器保存路径影响），唯一红的是撤销后自动保存（`applySnapshot` 原先不进入 `dirty`）。
- 源码核对：分类与归组五条规则、含空白封闭、重做清空、`_applying` 守卫、`recordCommand` 校验、`clear` 均按契约；页面 `Shortcuts`（仅非 Apple Ctrl+Y）→`Actions`→正文 `TextField`，按钮与按键同一入口，`dispose` 清栈；`undoController` 参数保留但类型改为 `Object?` 且不再传给 `TextField`（为通过守卫扫描，接受）。
- 盲测（临时文件，已删除）：① 间隔恰 `undoMergeMaxGapMs` 开新单元、少 1 ms 并入；② 第 20 个 code point（emoji）并入、第 21 个开新；③ U+3000 与 `\t` 自成封闭单元；④ Windows 与 Android 下一次 Ctrl+Z：`undoCount` 恰 +1、`TextEditingController` 回调恰 1 次、文本恰回退一个单元；⑥ 撤销后 2000 ms 自动保存快照文本与输入框相同、`canUndo=false/canRedo=true`。
- **⑤ 组合中撤销**：adapter 不抛异常，但会清空正文且控制器仍停在 `imeComposing`——裁定为 D-NC006-14：组合中 `undo/redo` no-op。
- **⑦ 页面层输入法组合（缺口）**：页面从未按 `TextEditingValue.composing` 调用 `onComposingChanged`，`updateEditingValue` 注入 `xn`/`xni`（composing）后 `state=dirty`、组合中 `pastUnits` 由 1 增到 2，提交后 3；PRD §4「组合过程作为整体」在页面层不成立。根因：NC-005 act/04 与 NC-006 act/03 都未把该接线列入 ACT（主 Agent 契约疏漏），不是执行方错误。处理：契约 §5.1 追加 D-NC006-13（接线顺序）与 D-NC006-14，新增 `act/04.yaml`（3 测试，全量 `+113`），守卫 K05 在 `--require-impl` 下要求页面含 `onComposingChanged` 且测试 ≥113。
- 判定：act/01～03 `ACCEPTED`；NC-006 总状态 `REWORK_ACT04`，act/04 通过后复跑本文第 4 条 ⑦ 与 ⑤ 再关闭。

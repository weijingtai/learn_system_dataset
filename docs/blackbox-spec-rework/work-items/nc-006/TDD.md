# NC-006 验证计划

所有命令在 `export PATH=/Users/jingtaiwei/flutter/bin:$PATH` 下运行；仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`。

## 1. 命令

| # | 命令 | 期望 |
|---|---|---|
| 1 | `flutter analyze` | 0 issues |
| 2 | `flutter test test/editor/editor_history_test.dart`（act/01 后） | `+17` |
| 3 | `flutter test test/editor/editor_history_test.dart`（act/02 后） | `+25` |
| 4 | `flutter test test/editor/editor_shortcuts_test.dart` | `+10` |
| 5 | `flutter test test/editor/note_editor_page_test.dart` | `+6`（B36 改名后计数不变） |
| 6 | `flutter test` | `+110: All tests passed!` |
| 7 | `git diff <NC-005 末提交> HEAD --stat -- pubspec.yaml pubspec.lock lib/src/domain lib/src/persistence test/persistence test/contracts lib/src/editor/save_status.dart lib/src/editor/markdown_preview.dart test/editor/save_status_test.dart test/editor/markdown_preview_test.dart test/editor/note_editor_test.dart` | 空 |
| 8 | `grep -nE '\b500\b|\b20\b|DateTime\.now\(|Timer\(|Stopwatch\(' lib/src/editor/editor_history_adapter.dart` | 无输出 |
| 9 | `test "$(grep -c 'Shortcuts(' lib/src/editor/note_editor_page.dart)" = 1`；另跑 `[ -z "$(grep -rl 'UndoHistoryController' lib/src/editor/)" ]` | 两条退出码均 0（恰 1 处；无匹配文件） |
| 10 | `bash docs/blackbox-spec-rework/reviews/nc006_guard.sh --require-impl` | 0 |

## 2. act/01：adapter 分类、归组、IME、栈规则（契约 §3、§4）

文件：`lib/src/editor/editor_history_adapter.dart`（`HistoryUnitKind`、`HistoryValue`、`EditorHistoryAdapter extends ValueNotifier<HistoryValue>`）、`test/editor/editor_history_test.dart`。测试构造：`NoteEditorController` 用 NC-005 `FakeNoteRepository` 与永不触发的 `TimerFactory`（返回 `Timer` 替身且 `cancel` 无效果，用 NC-005 `test/support` 已有设施或本文件内私有类）；adapter 的 `now` 用可变 `DateTime` 变量。输入用辅助函数 `type(String fragment)`：以 `controller.snapshot` 为 before，构造 after（文本插入在选区处、选区后移），先 `controller.onTextChanged(...)` 再 `adapter.recordTextChange(before, after)`。

17 个测试（名称逐字，对应 BDD）：`abc at 100 ms merges into one unit and undo empties`（B01）、`gap 499 merges and gap 500 opens new unit`（B02，阈值取 `undoMergeMaxGapMs - 1` 与 `undoMergeMaxGapMs`）、`twenty code points merge and the twenty first opens new unit`（B03，用 `undoMergeMaxChars`）、`emoji counts as one code point`（B04）、`whitespace fragment is its own sealed unit`（B05，空格与换行两轮）、`multi code point insertion is paste and sealed`（B06）、`replace is a sealed unit`（B07）、`deletes group separately from inserts`（B08）、`caret move seals the current unit`（B09）、`non contiguous insert opens new unit`（B10）、`ime composition commits as one unit`（B11）、`ime cancel produces no unit`（B12）、`command kinds are sealed and text kinds rejected`（B13）、`new unit clears redo and empty redo is noop`（B14）、`undo and redo restore selection and attachment refs`（B15）、`clear resets stacks and counters`（B16）、`undo and redo never call repository`（B17）。

Red：先写 17 个测试与仅含类型骨架、方法抛 `UnimplementedError` 的 adapter，运行命令 2 取得失败原文。

## 3. act/02：adapter × 控制器与自动保存（契约 §4.4；editor.md §2）

文件：追加到 `test/editor/editor_history_test.dart`（`group('autosave interplay')`，用 `FakeAsync` 与 NC-005 的真实 `TimerFactory` 注入方式）；如 NC-005 的 `applySnapshot` 不满足「进入 `dirty` 并启动去抖、保留 title/changeSummary」，仅修改 `note_editor_controller.dart` 的该方法。

8 个测试：`undo marks dirty and autosaves undone text`（B18）、`autosave success keeps stack`（B19）、`save failed keeps stack`（B20）、`unchanged save keeps stack`（B21）、`apply guard does not create units`（B22）、`reopen gives empty history but revisions remain`（B23）、`title and summary are not part of history`（B24）、`history flow only calls save snapshot`（B25）。

Red：先写 8 个测试，运行命令 3 取得失败原文（若 NC-005 的 `applySnapshot` 已满足，B18～B25 中至少 B22/B23/B24 会因 adapter 行为而红；报告如实写明哪些一开始就绿及原因）。

## 4. act/03：页面接线、按键、按钮、焦点（契约 §5、§6）

文件：`lib/src/editor/note_editor_page.dart`（`history` 可选参数、`Shortcuts`→`Actions`→正文 `TextField` 三层、按钮接线、`TextEditingController` 监听调用 `recordTextChange`、`applySnapshot` 后回写 value、dispose）、`test/editor/editor_shortcuts_test.dart`、`test/editor/note_editor_page_test.dart`（仅 B36 一个测试改名与改断言）。

10 个测试：`ctrl z undoes on windows and linux`（B26）、`ctrl shift z and ctrl y redo on windows and linux`（B27）、`meta z and meta shift z on macos`（B28）、`ctrl y does nothing on macos`（B29）、`single ctrl z steps exactly one unit and one text change`（B30）、`buttons and keys produce identical state`（B31）、`focus elsewhere does not respond`（B32）、`buttons enable with history and keep labels`（B33）、`body field has null undo controller and single wrappers`（B34）、`page disposes injected adapter`（B35）。B36 在 NC-005 文件内改名为 `shortcuts and actions wrap only the body field`。

按键：`await tester.sendKeyDownEvent(LogicalKeyboardKey.controlLeft); await tester.sendKeyEvent(LogicalKeyboardKey.keyZ); await tester.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);`；macOS 用 `metaLeft`；每个测试末尾把 `debugDefaultTargetPlatformOverride` 置回 `null`。输入用 `tester.enterText(正文, 'a')`、`'ab'`、`'abc'` 并在每次之间推进注入 `now` 100 ms。

Red：先写 10 个测试与 B36 改动，运行命令 4、5 取得失败原文。

## 5. Red→Green 与禁止

- 每步先测试后实现；报告贴 Red 原文。
- 禁止：`skip`、永真断言、修改 NC-004 文件、修改 NC-005 白名单外文件、`UndoHistoryController` 驱动撤销、adapter 内 `DateTime.now()`/`Timer(`/`Stopwatch(`/字面量 500 与 20、登记 Ctrl+Y 之外任何新键、把「取消发布」放进撤销、新增依赖。
- 命令 6 最终 `+110`。

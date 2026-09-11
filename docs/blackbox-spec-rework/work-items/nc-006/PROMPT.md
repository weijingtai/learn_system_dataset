# NC-006 执行提示

发送前提：wjt-react 四查判定 READY；**NC-005 已 ACCEPTED**；README「Dependencies / Baseline」已填 NC-005 末提交 hash（`8b05a68`）；主线程已在 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 登记。满足后，把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-006：在已存在的 Flutter 包 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 Git 仓库，NC-004/NC-005 已建立）内实现撤销/重做栈 adapter、输入法组合单元与编辑页的按键、按钮、焦点接线。`xuan-migration` 父目录不是 Git 仓库，绝不在父目录执行 git；learn_system 仓库只读。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读（按顺序）**：`/Users/jingtaiwei/Git/Public/learn_system/AGENTS.md`；`docs/blackbox-spec-rework/work-items/nc-006/` 下的 README.md、BDD.md、TDD.md、ACT.yaml、act/01～03.yaml、ACCEPTANCE.md；`openspec/annotation-community/contracts/editor_history.md`（全文）、`editor.md` §2/§4；`reading-notes/lib/src/editor/`（NC-005 产物）与 `lib/src/domain/limits.dart`、`editor_snapshot.dart`、`note_revision.dart`（只读）。可查看 Flutter SDK `widgets/undo_history.dart` 与 `default_text_editing_shortcuts.dart` 核对契约 §2 的平台事实，但不得复制其代码。

**先写测试再改实现**：每步先写本步测试并取得真实 Red 原文（贴入报告），再实现。先实现后补测试即违反流程，须如实写明；act/02 若有测试一开始即绿，逐个说明原因。

**只允许写**：各 ACT 的 WRITE_NEW 清单（新建 `lib/src/editor/editor_history_adapter.dart`、`test/editor/editor_history_test.dart`、`test/editor/editor_shortcuts_test.dart`；局部修改 `note_editor_page.dart`、`note_editor_controller.dart` 仅 `applySnapshot`、`note_editor_page_test.dart` 仅一个测试；`lib/reading_notes.dart` 导出）。禁止：learn_system 任何写入；改 NC-004 文件；改 NC-005 的 `save_status.dart`、`markdown_preview.dart`、`note_editor_test.dart` 与它们的测试；改 `pubspec.yaml`/`pubspec.lock`；用 `UndoHistoryController` 驱动撤销；adapter 内 `DateTime.now()`、`Timer(`、`Stopwatch(`、数字字面量 500 与 20（只引用 `limits.dart` 常量）；登记 Ctrl+Y 之外任何新键；`skip`、永真断言。

**判据来源**：分类、归组、键表、Widget 树位置只来自 `editor_history.md`；期望值只来自 TDD。契约有两种以上解释、NC-005 的 `applySnapshot` 不存在、页面构造无法增加 `history` 参数、`Action.overridable` 覆盖在 `flutter test` 下未生效（Ctrl+Z 仍弹平台栈）、需要改 NC-004 文件或新增依赖：立即停止并原样报告，不自行裁定。

**提交**：三步各一个提交，在 `reading-notes` 仓库内，只 `git add` 本步文件，不 push。提交消息按各 ACT 的 COMMIT_MESSAGE，末尾另起两行加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。

**交付报告**（每步一节）：
1. commit 哈希与 `git show --stat` 原文；
2. Red：命令、退出码、失败原文；
3. Green：该 ACT VERIFICATION 每条命令的退出码与输出末 20 行；
4. act/02 另附 `applySnapshot` 是否改动及原语义；act/03 另附 `flutter test` 全量末 5 行（应 `+110: All tests passed!`）与 `nc006_guard.sh --require-impl` 退出码；
5. 跳过项、未运行项与剩余风险。

不要把本任务说成 NC-006 之外的任何任务完成：历史页与差异、iOS 原生撤销入口、图片清理、其他快捷键都在后续任务或已登记缺口。


# NC-006 act/04 返工执行提示（2026-09-11 验收后追加）

发送前提：act/01～03 已验收（reading-notes `afbe3a0`、`bc6435b`、`4966924`）。把分隔线以下全文原样发给执行 Agent。

---

你执行 NC-006 的返工步 act/04：在 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（独立 Git 仓库；`xuan-migration` 父目录不是 Git 仓库，绝不在父目录执行 git；learn_system 只读）以 `4966924` 为基线补两处：① 编辑页把输入法组合状态喂给控制器；② adapter 在组合中撤销/重做为 no-op。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。

**先读**：`docs/blackbox-spec-rework/work-items/nc-006/act/04.yaml`、`TDD.md` §4b、`BDD.md` B37～B39；`openspec/annotation-community/contracts/editor_history.md` §5.1 的「输入法组合接线（D-NC006-13）」与「组合中撤销/重做为 no-op（D-NC006-14）」两条（顺序逐字照做）；`reading-notes/lib/src/editor/note_editor_page.dart`、`editor_history_adapter.dart`、`note_editor_controller.dart`（`onComposingChanged` 只读）。

**先写测试再改实现**：先在 `test/editor/editor_shortcuts_test.dart` 追加 3 个测试（名称逐字取 TDD §4b），运行 `flutter test test/editor/editor_shortcuts_test.dart` 取得真实 Red 原文，再实现。

**只允许写**：`lib/src/editor/note_editor_page.dart`、`lib/src/editor/editor_history_adapter.dart`、`test/editor/editor_shortcuts_test.dart`。禁止：其他任何文件；新增依赖；改控制器；改既有测试期望；`skip`、永真断言。

**判据**：契约 §5.1 两条与 TDD §4b。若 `tester.testTextInput.updateEditingValue` 注入的 composing 未到达 `TextEditingController.value.composing`、或按契约顺序调用后 B37 仍无法得到恰一个单元，立即停止并原样报告。

**提交**：一个提交，只 `git add` 上述三个文件，不 push；提交消息 `fix: 页面输入法组合接线与组合中撤销 no-op（NC-006-D）`，末尾另起两行加 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`。

**交付报告**：commit 哈希与 `git show --stat`；Red 命令/退出码/原文；`flutter analyze`、`flutter test test/editor/editor_shortcuts_test.dart`（期望 `+13`）、`flutter test`（期望 `+113`）、`bash /Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/reviews/nc006_guard.sh --require-impl`（期望 0）各自退出码与末 20 行；`git status --short` 为空。

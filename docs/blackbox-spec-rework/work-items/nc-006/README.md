# NC-006：撤销、重做与输入法

状态：`REWORK_ACT04`（2026-09-11 验收：act/01～03 通过，盲测 ⑦ 发现页面未接入输入法组合、⑤ 组合中撤销需裁定；追加 act/04，D-NC006-13/14）。原状态 `READY`（2026-09-11 wjt-react R1：忠实性/覆盖性/独立性通过，可执行性 1 项返工——act/03 校验命令退出码语义——已由主 Agent 落实并空跑复核；记录见 `reviews/NC-006-REVIEW-R1.md`）。派发前置：**NC-005 ACCEPTED**（reading-notes 含 NC-005 四个提交、`flutter test +75`）。执行由用户交外部 Agent，PROMPT.md 原样发送。task_id：`NC-006`。权威需求来源：TASKS NC-006；DESIGN §3「撤销栈归属」、§3.1；PRD §4、§4.1 A11Y-05；契约 `openspec/annotation-community/contracts/editor_history.md`（本任务专属，主 Agent 编写）、`editor.md` §2/§4；NC-004 `limits.dart` 常量。

## 主 Agent 已核定的平台事实（执行者不再调研）

Flutter 3.44.6 源码：`EditableText` 无条件内嵌平台 `UndoHistory` 栈且不可关闭；`TextField.undoController` 的 `undo()` 会弹平台栈；`UndoHistory` 的撤销/重做动作是 `Action.overridable`，祖先 `Actions` 同类 Intent 即覆盖；默认键表无 Ctrl+Y。由此裁定 D-NC006-01：撤销经 `Actions` 覆盖 `UndoTextIntent/RedoTextIntent`，页面 `undoController` 保持 `null`，Ctrl+Y 由 `Shortcuts` 补映射（仅非 Apple 平台）。iOS 原生 UndoManager 入口不封闭（D-NC006-06，设备级缺口，登记 NC-024）。

## Goal

在 `reading_notes` 包内实现 `EditorHistoryAdapter`（唯一真源栈、可判定归组、IME 一次组合一个单元、撤销/重做恢复文本+光标+引用、自动保存不清栈、重开清栈）、页面接线（Intent 覆盖、Ctrl+Y、按钮与按键同一入口、焦点边界、A11Y-05 按钮启停）。执行者不做设计：分类规则、阈值来源、键表、Widget 树位置全部来自契约。

## Scope

- 允许写：仅 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes/` 内：新建 `lib/src/editor/editor_history_adapter.dart`、`test/editor/editor_history_test.dart`、`test/editor/editor_shortcuts_test.dart`；局部修改 `lib/src/editor/note_editor_page.dart`（契约 §5）、`lib/src/editor/note_editor_controller.dart`（仅 `applySnapshot` 方法，且仅当其语义与契约 §4.4 不符）、`test/editor/note_editor_page_test.dart`（仅契约 §5.4 指定的一个测试）、`lib/reading_notes.dart`（追加导出）。
- 只读：NC-004、NC-005 其余文件；契约；DESIGN/PRD/TASKS；Flutter SDK `widgets/undo_history.dart`、`editable_text.dart`、`default_text_editing_shortcuts.dart`（只看不复制）。
- 禁止：写入 learn_system；改 NC-004 文件；改 NC-005 的 `save_status.dart`、`markdown_preview.dart` 及其测试与 `note_editor_test.dart`；新增依赖；`UndoHistoryController` 驱动撤销；adapter 内 `DateTime.now()`/`Timer(`/`Stopwatch(`/数字字面量 500 与 20；登记 F-01 范围的其他快捷键；把「取消发布」放进撤销；`skip`、永真断言；先实现后补测试。

## Inputs

契约 `editor_history.md` §2（平台事实）、§3（接口）、§4（分类与归组）、§5（页面接线与 NC-005 测试唯一改动）、§6（焦点与平台）、§7（可观察断言）、§8（决定 D-NC006-01～12）。

## Dependencies / Baseline

- **NC-005 ACCEPTED**：NC-005 末提交 hash：`8b05a68`（2026-09-11 ACCEPTED）；`flutter test +75`；`analyze` 0。
- 零新依赖；`pubspec.yaml`/`pubspec.lock` 不得变化。
- 共享守卫：唯一 learn_system 侧命令 `bash docs/blackbox-spec-rework/reviews/nc006_guard.sh --require-impl`（只读）；K01 失败判外部失败，K02 及以后按本任务失败停工。

## Stop Conditions

契约有两种以上解释；NC-005 交付的 `NoteEditorController.applySnapshot` 不存在或页面构造签名无法按契约 §5.1 增加 `history` 参数；需要写白名单外文件；需要新依赖；`Action.overridable` 覆盖在 `flutter test` 下未生效（Ctrl+Z 仍弹平台栈）；NC-005 未 ACCEPTED。遇到即停，原样报告。

## 执行顺序

返工：`act/04`（页面 `composing` 接线 + adapter 组合中 no-op，3 测试，全量 `+113`），以 `4966924` 为基线。首轮：`act/01`（adapter：分类、归组、IME、栈规则）→ `act/02`（adapter × 控制器：applySnapshot、自动保存不清栈、重开、调用集合）→ `act/03`（页面接线：Intent 覆盖、Ctrl+Y、按钮、焦点、NC-005 测试唯一改动）。每步一个提交在 `reading-notes` 仓库。

## 一次性交付与阅读顺序

1. 本 README；2. `contracts/editor_history.md`；3. [BDD](BDD.md)、[TDD](TDD.md)；4. [ACT](ACT.yaml) 与 act/01～03；5. [ACCEPTANCE](ACCEPTANCE.md)；6. [PROMPT](PROMPT.md)。

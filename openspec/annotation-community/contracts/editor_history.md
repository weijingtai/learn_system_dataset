# 撤销/重做与输入法契约：唯一真源栈、归组、按键映射与焦点边界（NC-006）

状态：`FROZEN_FOR_NC-006`（2026-09-11；同日验收后追加 D-NC006-13/14 与 §5.1 两条，供 act/04 消费）。权威来源：[DESIGN](../DESIGN.md) §3「撤销栈归属」与 §3.1；[PRD](../PRD.md) §4、§4.1 A11Y-05；[TASKS](../TASKS.md) NC-006；[editor.md](editor.md) §2、§4（NC-005 裁定方案 b）；[community-models](community-models.md) §1.3 常量；NC-004 `limits.dart`。本文把已定设计落到 adapter 接口、归组判定、按键接线与测试判据，供执行者照抄；与上游冲突以上游为准并回报主 Agent。

## 1. 位置、依赖与不变式

- 新文件：`lib/src/editor/editor_history_adapter.dart`；测试 `test/editor/editor_history_test.dart`、`test/editor/editor_shortcuts_test.dart`。
- 局部改动（TASKS NC-006 明示允许）：`lib/src/editor/note_editor_page.dart`（接线，见 §5）、`lib/src/editor/note_editor_controller.dart`（仅当 `applySnapshot` 语义与 §4 不符时，改动限于该方法）、`test/editor/note_editor_page_test.dart`（仅 §5.4 指定的一个测试）、`lib/reading_notes.dart`（导出）。
- 零新依赖。归组常量只引用 `limits.dart` 的 `undoMergeMaxGapMs`（500）与 `undoMergeMaxChars`（20），adapter 源码不得出现这两个数字字面量。
- 不变式：adapter 不调用 `NoteRepository` 的任何方法、不持有任何发布/远端接口；撤销产生的保存仍只经 `NoteEditorController` 的自动保存路径（editor.md §2）。

## 2. 平台事实（Flutter 3.44.6，已核源码）

| 事实 | 出处 | 对本契约的后果 |
|---|---|---|
| `EditableText` 无条件内嵌 `UndoHistory<TextEditingValue>`，维护自己的栈，监听 `TextEditingController` 每次变更（500 ms 节流）压栈 | `widgets/editable_text.dart` build → `UndoHistory(...)` | 平台栈**无法关闭**；「唯一真源」靠让平台栈永不被触发 |
| `TextField.undoController` 只是暴露平台栈：`UndoHistoryState` 覆写其 `value`，并监听其 `onUndo/onRedo` 去弹**平台栈** | `widgets/undo_history.dart` `_effectiveController` | **禁止**用 `UndoHistoryController.undo()/redo()` 驱动撤销；页面 `undoController` 参数保持 `null` |
| `UndoHistory.build` 注册 `UndoTextIntent`/`RedoTextIntent` 的动作为 `Action.overridable(context)`，覆盖动作从其祖先 `Actions` 查找 | `undo_history.dart` build；`actions.dart` `Actions.maybeFind<T>(context)` | 在正文 `TextField` 外层放 `Actions{UndoTextIntent, RedoTextIntent}` 即覆盖平台默认动作，键盘路径下平台栈永不弹出 |
| 默认键表：非 Apple 平台 Ctrl+Z→Undo、Ctrl+Shift+Z→Redo；macOS/iOS ⌘Z→Undo、⌘⇧Z→Redo；**没有 Ctrl+Y** | `widgets/default_text_editing_shortcuts.dart` `_commonShortcuts`/`_macShortcuts` | PRD §4 的 Ctrl+Y 由页面 `Shortcuts` 补映射为 `RedoTextIntent`，仅非 Apple 平台 |
| iOS 原生 `UndoManager`（摇动撤销、外接键盘工具条）经 `handlePlatformUndo` 直接弹平台栈，不经 Intent | `undo_history.dart` `handlePlatformUndo` | 本契约不承诺封闭该入口；登记为设备级验收缺口（D-NC006-06） |

## 3. adapter 接口

```dart
enum HistoryUnitKind { insert, delete, replace, paste, imeCommit, format, imageInsert, mentionInsert }

@immutable
class HistoryValue {
  final bool canUndo;     // pastUnits > 0
  final bool canRedo;     // futureUnits > 0
  final int undoCount;    // 会话内成功执行的 undo 次数（DESIGN §3 可观察断言用）
  final int redoCount;    // 会话内成功执行的 redo 次数
  final int pastUnits;    // 撤销栈深度
  final int futureUnits;  // 重做栈深度
}

class EditorHistoryAdapter extends ValueNotifier<HistoryValue> {
  EditorHistoryAdapter({required NoteEditorController controller, required DateTime Function() now});
  void recordTextChange(EditorSnapshot before, EditorSnapshot after); // 页面在每次 TextEditingController 变更后调用
  void recordCommand(HistoryUnitKind kind, EditorSnapshot before, EditorSnapshot after); // 仅 format / imageInsert / mentionInsert
  void undo(); // 不可撤销时 no-op，不抛
  void redo(); // 不可重做时 no-op，不抛
  void clear();
}
```

- `now` 是注入的时间源（D-NC006-08）；生产默认 `DateTime.now`，测试用可控函数。adapter 内禁止 `DateTime.now()`、`Timer(`、`Stopwatch(`。
- `recordTextChange` 是唯一的正文输入口；`recordCommand` 只接受三个命令类 kind，其余 kind 传入抛 `ArgumentError`。
- adapter 在 `undo()/redo()` 内调用 `controller.applySnapshot(target)`，并以 `_applying=true` 守卫使期间到达的 `recordTextChange` 被忽略（D-NC006-09）。

## 4. 单元、分类与归组（DESIGN §3.1 可判定化）

### 4.1 单元

一个 undo 单元 = `{kind, before: EditorSnapshot, after: EditorSnapshot, sealed: bool, lastAt: DateTime, runes: int, insertEnd: int}`。撤销应用 `before`，重做应用 `after`。历史只覆盖正文结构：`text / selectionBase / selectionExtent / attachmentRefs / mentionRefs`；`title` 与 `changeSummary` 不入栈，`applySnapshot` 时保留控制器当前值（D-NC006-05）。

### 4.2 `recordTextChange` 分类（按 `before.text` 与 `after.text` 的最长公共前缀 p、最长公共后缀 s 计算）

| 条件 | 分类 | 归组 |
|---|---|---|
| `after.composing == true` | 输入法组合中 | **不记录**；首次进入组合时记 `imeStart = before`（若尚未记） |
| `before.composing == true && after.composing == false` | `imeCommit` | 一个封闭单元 `imeStart → after`；若 `imeStart.text == after.text`（组合取消）则不产生单元；清 `imeStart` |
| 文本相同、选区不同 | 光标跳转 | 不产生单元；封闭栈顶单元（`sealed=true`） |
| 文本相同、选区相同 | 无变化 | 忽略 |
| 只有插入（removed 空、inserted 非空）且 inserted 的 code point 数 == 1 | `insert` | 按 §4.3 判定是否并入栈顶 |
| 只有插入且 code point 数 ≥ 2 | `paste` | 新单元并立即封闭（D-NC006-04） |
| 只有删除（inserted 空、removed 非空） | `delete` | 按 §4.3 判定（与 `insert` 单元不互并） |
| 既有删除又有插入 | `replace` | 新单元并立即封闭 |

其中 removed = `before.text[p : before.length - s]`，inserted = `after.text[p : after.length - s]`。删除分类不区分退格与前删。

### 4.3 归组判定（全部满足才并入栈顶，任一不满足即开新单元）

1. 栈顶存在且 `sealed == false` 且 `kind` 与本次相同（`insert` 对 `insert`、`delete` 对 `delete`）；
2. `now() - top.lastAt < Duration(milliseconds: undoMergeMaxGapMs)`（严格小于；相等即开新单元）；
3. 本次文本片段（inserted 或 removed）不含空白：`!RegExp(r'\s').hasMatch(fragment)`；含空白的片段自成一个**封闭**单元（D-NC006-02）；
4. `top.runes + fragment.runes.length <= undoMergeMaxChars`（按 code point 计，D-NC006-03）；
5. 连续性：`insert` 要求插入起点 p == `top.insertEnd`；`delete` 要求删除区间与栈顶删除区间相邻（p == top.insertEnd 或 p + removed.length == top.insertEnd）。

并入时更新 `top.after = after`、`top.lastAt = now()`、`top.runes += fragment.runes.length`、`top.insertEnd`（insert 为 p + inserted.length；delete 为 p）。`recordCommand` 三类与 `paste`/`replace`/`imeCommit` 单元创建即封闭，且创建前先封闭原栈顶。

### 4.4 栈规则

- 任何新单元创建（含并入失败开新单元）都清空重做栈（PRD §4「撤销后新增编辑清空原重做分支」）；并入栈顶不清重做栈（此时重做栈必为空）。
- `undo()`：弹栈顶到重做栈，`applySnapshot(unit.before)`，`undoCount += 1`；`redo()` 对称，`redoCount += 1`。
- 自动保存成功、`saveFailed`、`unchanged` 都不触碰栈；adapter 不监听控制器状态。
- `clear()` 清两栈与 `imeStart`，计数归零；页面 `dispose` 时调用；重开页面得到全新 adapter（PRD §4「不跨重启持久化撤销栈」）。
- `undo()` 应用的快照进入控制器后按 editor.md §2 的 `onTextChanged` 规则变 `dirty` 并启动去抖，照常自动保存为新修订（DESIGN §3.1）。
- 图片：撤销只把 `attachmentRefs` 恢复到 `before`，不调用任何删除接口（adapter 无仓储引用，测试用替身调用集合证明）。

## 5. 页面接线（`note_editor_page.dart` 局部改动）

### 5.1 构造与生命周期

- 页面新增可选参数 `EditorHistoryAdapter? history`；为 `null` 时页面 `initState` 以 `now: DateTime.now` 自建，并在 `dispose` 调用 `clear()` 与 `dispose()`。页面**不再**向 `TextField` 传 `undoController`（保持 `null`；NC-005 的参数位保留但页面内部不使用）。
- 正文 `TextField.onChanged` 之后（控制器已收到 `onTextChanged`/`onComposingChanged`）调用 `history.recordTextChange(before, after)`，`before` 为调用控制器前取到的 `controller.snapshot`。选区变化无文本变化时也调用（用 `TextEditingController` 监听器，而不只是 `onChanged`）。
- `applySnapshot` 后页面把 `TextEditingController.value` 设为 `(text, selection(base, extent), composing: empty)`；此赋值触发的监听回调因 `_applying` 守卫不产生单元。
- **输入法组合接线（D-NC006-13，NC-006 act/04 补齐）**：页面在同一监听器内按 `TextEditingController.value.composing.isValid` 驱动控制器：进入组合（上一值无效、本值有效）时，先取 `before = controller.snapshot`，再依次调用 `controller.onComposingChanged(true)`、`controller.onTextChanged(...)`，最后 `recordTextChange(before, after)`；组合中每次变更只调 `onTextChanged` 与 `recordTextChange`；退出组合（上一值有效、本值无效）时依次调用 `controller.onTextChanged(...)`、`controller.onComposingChanged(false)`，再 `recordTextChange(before, after)`。由此 adapter 在页面层看到的 `before.composing/after.composing` 与 §4.2 表一致：一次组合提交恰一个 `imeCommit` 单元，组合取消无单元。
- **组合中撤销/重做为 no-op（D-NC006-14）**：`controller.state == imeComposing` 时 `undo()`/`redo()` 直接返回，不改栈、不改计数；工具条按钮在组合中同样不触发。理由：PRD §4「不拦截输入法正在使用的按键」，且组合中替换正文会与输入法待提交文本冲突。

### 5.2 Intent 覆盖与按键

- 正文 `TextField` 外层（且只包正文，不包标题/说明输入框与工具条）依次为：`Shortcuts(shortcuts: {非 Apple 平台: SingleActivator(keyY, control: true) → RedoTextIntent(SelectionChangedCause.keyboard)})` → `Actions(actions: {UndoTextIntent: CallbackAction(onInvoke: (_) => history.undo()), RedoTextIntent: CallbackAction(onInvoke: (_) => history.redo())})` → `TextField`。
- 「非 Apple 平台」= `defaultTargetPlatform` ∉ {iOS, macOS}；Apple 平台 `Shortcuts` 映射表为空（Ctrl+Y 不生效）。其余按键全部依赖 Flutter 默认键表（§2 第四行），页面不重复登记 Ctrl+Z/Ctrl+Shift+Z/⌘Z/⌘⇧Z。
- 不注册 F-01 范围内任何其他快捷键；不禁用系统输入行为；输入法组合期间按键不被拦截（`Actions` 只在 Intent 被派发时响应，键盘事件先到 IME 是 Flutter 既有行为，无需额外代码）。

### 5.3 按钮

- 工具条撤销/重做按钮 `onPressed` 分别为 `history.undo`/`history.redo`，`enabled` 分别取 `history.value.canUndo/canRedo`（`ValueListenableBuilder`）；semantics label 仍为「撤销」/「重做」，无历史时 `isEnabled=false`（A11Y-05）。按钮与按键调用同一方法，不存在第二条路径。

### 5.4 对 NC-005 页面测试的唯一改动

`test/editor/note_editor_page_test.dart` 中测试 `no shortcuts registered by page` 改名为 `shortcuts and actions wrap only the body field`，断言改为：`Shortcuts` 恰 1 个、`Actions` 中含 `UndoTextIntent` 键的恰 1 个，二者的后代包含正文 `TextField`、不包含标题输入框；其余 NC-005 测试不得改动。

## 6. 焦点与平台边界

- 焦点不在正文 `TextField`（在标题框、其他按钮或页面外控件）时，Ctrl+Z 不改变正文、`undoCount` 不变（标题框自身的平台栈行为不在本契约内，保留系统行为）。
- 平台切换用 `debugDefaultTargetPlatformOverride`；按键用 `tester.sendKeyDownEvent/sendKeyUpEvent`（Ctrl = `controlLeft`，⌘ = `metaLeft`，Shift = `shiftLeft`）。
- Android Gboard 会把非 CJK 单词放入组合区（editable_text.dart 注释）：在该平台下一个拉丁单词按 `imeCommit` 成一个单元，属于契约 §4.2 的既定行为，不视为缺陷。

## 7. 可观察断言（供 BDD/TDD 逐字引用）

1. 空编辑器以 100 ms 间隔输入 `a`、`b`、`c`，按一次 Ctrl+Z → 文本 `""`，`canRedo=true`，`canUndo=false`，`undoCount=1`。
2. 不双撤销：任一状态按一次 Ctrl+Z → `undoCount` 恰增 1，`TextEditingController` 变更回调恰触发 1 次，文本恰回退一个单元。
3. 间隔 499 ms 并入、500 ms 开新单元；累计 20 code point 并入、第 21 个开新单元；片段 ` `（空格）或 `\n` 自成封闭单元。

## 8. 决定登记（NC-006，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC006-01 | 用 `Actions` 覆盖 `UndoTextIntent/RedoTextIntent`，不接管 `undoController`，Ctrl+Y 由 `Shortcuts` 补映射 | 平台栈不可关闭；`Action.overridable` 是 Flutter 提供的覆盖点；`UndoHistoryController.undo()` 会弹平台栈 |
| D-NC006-02 | 含空白片段自成封闭单元 | 「未跨越空白或换行」需要一个可判定的边界，且避免空白被并入前后任一单元造成不对称 |
| D-NC006-03 | 20 字符按 code point 计 | 与 community-models 的 `maxLength` 按 code point 一致 |
| D-NC006-04 | 单次变更插入 ≥ 2 code point 且非 IME 提交视为粘贴 | `TextField.onChanged` 不携带来源；按可判定的 diff 分类而非平台默认行为 |
| D-NC006-05 | 历史只覆盖正文结构，title/changeSummary 不入栈 | DESIGN §3.1「同时恢复文本、光标及结构化引用」未含标题；避免正文撤销改动标题 |
| D-NC006-06 | iOS 原生 UndoManager 入口不封闭，登记为设备级验收缺口 | 该入口绕过 Intent 直接弹平台栈，Widget 测试与 Actions 覆盖都够不到；封闭需要 fork `EditableText` |
| D-NC006-07 | `undoCount/redoCount` 为会话内执行次数，另暴露 `pastUnits/futureUnits` | DESIGN 原话「undoCount 增加 1」是执行计数；栈深供归组测试直接断言 |
| D-NC006-08 | 时间源注入 `DateTime Function() now` 而非 NC-004 `Clock`（字符串） | 归组只需毫秒差；避免解析 ISO 字符串 |
| D-NC006-09 | `applySnapshot` 触发的变更由 `_applying` 守卫排除，不入栈 | 否则撤销自身会生成新单元并清空重做栈 |
| D-NC006-10 | `Shortcuts/Actions` 只包正文输入框 | 焦点边界靠 Widget 树位置实现，无需焦点判断代码 |
| D-NC006-11 | 删除与插入独立归组、不互并；光标跳转与非连续位置封闭栈顶 | DESIGN §3.1「删除操作按同规则独立归组」「光标跳转无条件开新单元」 |
| D-NC006-13 | 页面按 `TextEditingValue.composing.isValid` 的进入/退出驱动 `onComposingChanged`，顺序见 §5.1 | 验收盲测发现 NC-005/NC-006 的 ACT 都未把该接线列入，页面层一次组合被记成多个单元；接线顺序决定 adapter 能否看到 `before.composing=true → after.composing=false` |
| D-NC006-14 | 组合中 `undo()/redo()` no-op | 验收盲测：组合中撤销会清空正文而输入法仍持有待提交文本；PRD §4 要求不干扰输入法 |
| D-NC006-12 | NC-005 守卫 `nc005_guard.sh` 的 `Shortcuts(` 扫描在 adapter 文件存在后自动跳过 | 该禁令只针对 NC-005 时段；NC-006 守卫改为断言 `Shortcuts` 只出现在页面且恰一次 |

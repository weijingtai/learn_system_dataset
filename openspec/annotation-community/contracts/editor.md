# 编辑器契约：编辑态状态机、自动保存、三态指示、撤销栈归属、预览安全（NC-005；NC-006 消费 §4）

状态：`FROZEN_FOR_NC-005`（2026-09-11）。权威来源：[DESIGN](../DESIGN.md) §3、§3.1、§5；[PRD](../PRD.md) §4、§4.1、§6.1、§6.2；[TASKS](../TASKS.md) NC-005/NC-006；[state-machines](state-machines.md) SM-1；[local-persistence](local-persistence.md) §3、§5；[community-models](community-models.md) §1.3。本文把已定设计落到控制器接口、状态映射、文案闭集与测试判据，供执行者照抄；与上游冲突以上游为准并回报主 Agent。

## 1. 包内位置与依赖

- 文件：`lib/src/editor/note_editor_controller.dart`、`note_editor_page.dart`、`markdown_preview.dart`、`save_status.dart`；测试 `test/editor/note_editor_test.dart`、`test/editor/markdown_preview_test.dart`、`test/editor/save_status_test.dart`。
- 新增依赖：`flutter_markdown_plus: 1.0.12`（精确锁定；NC-001 基线用户指定）及其传递依赖 `markdown`（版本由 lock 固定，README 登记实际值）。不新增其他依赖。
- 复用 NC-004：`NoteRepository`、`EditorSnapshot`、常量 `autosaveDebounceMs=2000`、错误类闭集；本任务不改 NC-004 文件。测试替身 `FakeNoteRepository` 用 Dart 隐式接口 `class FakeNoteRepository implements NoteRepository`（不调用其构造函数、不需要真实 `NoteDatabase`），只实现契约 §2 用到的方法，其余方法抛 `UnimplementedError`。
- 不变式：本包不存在任何发布/Publication/ContentAccess 接口；自动保存只经 `NoteRepository.saveSnapshot` 写私人 head，不可能改变已发布正文（TASKS NC-005「自动保存不改变已发布正文」），测试以替身记录的方法调用集合证明。

## 2. 编辑态状态机实现面（SM-1）

`NoteEditorController extends ChangeNotifier`：

| 成员 | 契约 |
|---|---|
| `EditorState get state` | 枚举 `clean / dirty / saving / saveFailed / imeComposing`，初态 `clean`（名称与 SM-1 一一对应，Dart 用 lowerCamel） |
| `bool get pendingDirty` | `saving` 期间收到 `onTextChanged` 置 true；本次保存完成后立即再触发一次保存并清 false |
| `EditorSnapshot get snapshot` | 当前缓冲；`saveFailed` 时不清空 |
| `bool get summaryTouched` | 初 false；`onSummaryChanged` 置 true；会话内不复位 |
| `Object? get lastError` | `saveFailed` 时为 NC-004 抛出的错误对象（`NoteSizeLimitExceeded` 等），供 UI 显示 |
| `void onTextChanged(String text, {required int selectionBase, required int selectionExtent})` | SM-1 边：clean→dirty（启动 2000 ms 去抖）；dirty→dirty（重置去抖）；saving→saving（pendingDirty=true）；saveFailed→saveFailed（内容更新，不自动重试）；imeComposing 下由 `onComposingChanged` 管理，本方法不改变状态 |
| `void onComposingChanged(bool composing)` | clean/dirty→imeComposing（composing=true，暂停去抖）；imeComposing→dirty（composing=false，视为一个编辑步骤，重启去抖） |
| `Future<void> flush({required FlushReason reason})` | `reason ∈ {debounce, blur, leave, retry}`；dirty→saving；saveFailed 且 reason∈{retry, blur, leave}→saving；clean 且 reason∈{debounce, retry}→抛 `IllegalEditorTransition`；saving→抛 `IllegalEditorTransition`（不可重入）；imeComposing 且 reason=debounce→抛 `IllegalEditorTransition`；imeComposing 且 reason=leave→保持 imeComposing 并把 `canLeave=false` 通知 UI |
| `bool get canLeave` | imeComposing 下为 false（保持编辑页与未保存提示）；其余 true |
| `void onSummaryChanged(String text)` | 更新 change_summary 缓冲并置 summaryTouched=true；同时按 `onTextChanged` 规则进入 dirty |
| `void copyAllText()` | saveFailed 下把全文放入剪贴板（用注入的 `ClipboardPort`）；状态保持 saveFailed，缓冲不丢 |

保存流程（`flush` 内）：`saving` → 调 `repository.saveSnapshot(noteId, snapshot, summaryTouched, expectedHeadId)`；成功（`saved` 或 `unchanged`）→ `clean`，更新 `expectedHeadId`（saved 时为新修订）；抛出任何异常 → `saveFailed`，`lastError` 置该异常，缓冲与 undo 栈都不清。`saving` 期间 `pendingDirty` 为 true 时，成功后立即再次 `flush(debounce)`。

时间：去抖与 400 ms 抑制一律经注入的 `TimerFactory`（`Timer Function(Duration, void Function())`）与 `Clock`；`lib/src/editor/` 内**禁止出现裸 `Timer(`/`Timer.periodic(`**（守卫扫描），测试用 `FakeAsync` 驱动；常量取 `limits.dart`。

## 3. 三态指示（PRD §6.1、§6.2；A11Y-04）

`save_status.dart` 定义三枚举与展示映射，文案闭集逐字如下（展示层只用本表词汇，测试逐字断言）：

| 枚举 | 值 → 文案 |
|---|---|
| `LocalSaveStatus` | `unsaved`→「未保存」；`saving`→「保存中」；`savedLocally`→「已保存本机」；`failed`→「保存失败」 |
| `DeviceSyncStatus` | `notEnabled`→「未开启」；`noOtherDevice`→「无其他设备」；`syncing(n,m)`→「同步中(n/m)」；`syncedTo(k)`→「已同步至 k 台」；`failed`→「同步失败」；`peerVersionPending`→「对方版本待处理」 |
| `CloudBackupStatus` | `notEnabled`→「未开启」；`queued`→「排队中」；`uploading(pct)`→「上传中(x%)」；`backedUpAt(time)`→「已备份至 <时间>」；`failed`→「备份失败」；`unknownOffline(lastKnown)`→「状态未知（离线），最后确认备份时间 YYYY-MM-DD HH:mm」；`disabledRetained`→「已关闭（存量保留）」 |

规则：
- 本地维度由控制器状态派生：`clean`→已保存本机（首次保存前为未保存）；`dirty`/`imeComposing`→未保存；`saving`→保存中；`saveFailed`→保存失败。
- **400 ms 抑制**：`saving` 持续不足 400 ms 时展示层不显示「保存中」，保持前一状态；用注入时钟测试。
- 设备同步与云备份维度本任务只实现枚举、文案与 semantics（NC-016/NC-018 提供真实值）；测试用注入值。断网时云备份为 `unknownOffline`，禁止显示「已备份」或空白；从未开启显示「未开启」且**不使用失败样式**（`isFailure=false`）。
- 失败态标记：图标 + 文字并存，semantics label 含状态文字（A11Y-04），不依赖颜色。
- 每个状态 Widget 暴露 `Semantics(label: <文案>)`，测试用 `tester.getSemantics` 断言。

## 4. 撤销栈归属（DESIGN §3 方案 b；NC-005 裁定，NC-006 直接消费）

- **唯一真源**：`editor_history_adapter`（NC-006 新建）持有撤销/重做栈；`NoteEditorPage` 的 `TextField` 传入自有 `UndoHistoryController`，并在其上拦截平台撤销：`TextField(undoController: adapterController)`，同时通过 `Shortcuts`/`Actions` 把 `UndoTextIntent`/`RedoTextIntent` 映射到 adapter，**不**让平台 `UndoHistory` 维护第二个栈。本任务（NC-005）只预留接线：`NoteEditorController` 暴露 `onHistoryStep(EditorSnapshot before, EditorSnapshot after)` 回调点与 `applySnapshot(EditorSnapshot)`；NC-006 实现 adapter 与归组。
- 归组常量：`undoMergeMaxGapMs=500`、`undoMergeMaxChars=20`（NC-004 `limits.dart`），NC-006 引用，不另写数字。
- 平台按键映射（PRD §4 表）由 NC-006 实现；NC-005 不注册任何快捷键，不禁用系统输入行为。
- 撤销不触发远端命令、不删除仍被历史引用的图片；自动保存成功不清栈；重开页面栈为空（持久历史在修订库）。
- 可观察断言（NC-006）：按一次 Ctrl+Z，`undoCount` 增 1 且文本仅回退一个 undo 单元；空编辑器以 100 ms 间隔输入 a、b、c 后 Ctrl+Z 一次 → 文本空串、canRedo=true、canUndo=false。
- NC-006 落地细则（adapter 接口、归组判定、Intent 覆盖、Ctrl+Y 补映射、焦点边界）见 [editor_history.md](editor_history.md)；本节「`TextField(undoController: adapterController)`」一句以该文 §2 第二行为准：页面 `undoController` 保持 `null`，撤销经 `Actions` 覆盖 `UndoTextIntent/RedoTextIntent`，不经 `UndoHistoryController`。

## 5. Markdown 预览与安全（DESIGN §5、TASKS NC-005 安全断言）

`MarkdownPreview` Widget（`markdown_preview.dart`）包装 `flutter_markdown_plus` 的渲染组件：

- 输入 `markdown: String`、`mode ∈ {privatePreview, publicView}`、`attachmentResolver: Future<Uint8List?> Function(String attachmentId)`、`onRequestExternalImage: void Function(Uri)`。
- **原始 HTML 不执行**：不启用任何 HTML 渲染扩展；内联 `<script>`/`<img onerror>` 等 HTML 按纯文本或被忽略处理，测试断言渲染树中不存在 `WebView`/`Html` 类型 Widget 且 `<script>` 文本不产生任何回调。
- **图片**：`attachment://<id>` 经 `attachmentResolver` 取字节渲染（`Image.memory`）；`http(s)://` 在 `privatePreview` 下**默认不发起网络请求**，渲染占位（「外部图片，点击加载」按钮），用户点击后调用 `onRequestExternalImage` 才加载；`publicView` 下按宿主策略（本任务同样默认不自动加载，NC-010 再定）。测试用可计数的 `HttpOverrides`/自定义 `ImageProvider` 断言构建预览后网络请求数为 0。
- 链接：`onTapLink` 只回调给宿主，不在包内打开 URL。
- 具体组件参数名以 §5.1 为准（由主 Agent 依 1.0.12 源码填写）。

### 5.1 flutter_markdown_plus 1.0.12 接线参数

依据 `~/.pub-cache/hosted/pub.dev/flutter_markdown_plus-1.0.12/`（2026-09-11 核对）：

| 事实 | 位置 | 接线要求 |
|---|---|---|
| 渲染组件 `MarkdownBody`（`shrinkWrap` 默认 true）与 `Markdown`（带滚动）；参数含 `data, selectable, styleSheet, onTapLink, onTapText, imageBuilder, checkboxBuilder, bulletBuilder, builders, extensionSet, blockSyntaxes, inlineSyntaxes, imageDirectory, softLineBreak` | `lib/src/widget.dart:206-229, :462, :517` | 预览用 `MarkdownBody`；`selectable: true` |
| `imageBuilder` 签名 `Widget Function(Uri uri, String? title, String? alt)` | `lib/src/widget.dart:37` | **必须提供**（见下一行原因）；按 `uri.scheme` 分派：`attachment` → `attachmentResolver` + `Image.memory`；`http`/`https` → 占位按钮，不构造 `Image.network`/`NetworkImage`；其他 scheme → 占位「不支持的图片来源」 |
| 默认图片处理：`imageBuilder == null` 时调用 `kDefaultImageBuilder`；`http/https` → `Image.network`；`data` → data URI；`resource` → `Image.asset`；**其余 scheme（含 `attachment://`）按 `imageDirectory` 拼接后走 `Image.file`** | `lib/src/builder.dart:616-643`；`lib/src/_functions_io.dart:19-68`（:25-31 network，:41-52 file） | 因此不提供 `imageBuilder` 会把 `attachment://` 当本地文件路径读取并把外部图片自动联网——两者都违反 §5，测试须证明 `imageBuilder` 被调用（对每个 img 节点计数） |
| 内联 HTML：包不支持渲染（README:83「doesn't support inline HTML」；`builder.dart` 无 html 处理） | `README.md:83` | 不传任何 `builders`/`extensionSet` 引入 HTML；测试仍断言 `<script>` 文本不产生 Widget 以外副作用 |
| 依赖 `markdown: ^7.3.1`（pub-cache 有 7.3.1）、`meta ^1.16.0`、`path ^1.9.1`；`environment: sdk ^3.4.0, flutter >=3.27.1` | `pubspec.yaml:11-19` | 与 reading_notes 的 Dart 3.12.2 / Flutter 3.44.6 兼容；lock 中 `markdown` 版本在 README 登记 |
| Flutter `UndoHistoryController extends ValueNotifier<UndoHistoryValue>`，方法 `undo()`/`redo()`，`onUndo`/`onRedo` 通知；`TextField.undoController` | `~/flutter/packages/flutter/lib/src/widgets/undo_history.dart:361-390`；`material/text_field.dart:255,887` | NC-006 接线依据；NC-005 只把 `undoController` 参数位留给 adapter |

## 6. 无障碍断言（PRD §4.1，本任务承接 A11Y-04/05/07）

| ID | 测试 |
|---|---|
| A11Y-04 | 三态指示的 semantics label 含状态文字；读屏树中无仅图标节点 |
| A11Y-05 | 撤销/重做按钮无历史时 `SemanticsFlag.isEnabled=false`，label 为「撤销」/「重做」，读屏朗读等价「撤销，已停用」；按钮常驻软键盘上方工具条（Widget 树位置断言） |
| A11Y-07 | 编辑页在 320 逻辑像素宽、`MediaQueryData(textScaler: TextScaler.linear(2.0))`（Flutter 3.12 起 `textScaleFactor` 已弃用，不得使用）下无 `RenderFlex overflow`、无横向滚动（`tester.takeException()` 为 null；`Scrollable` 轴向断言） |

## 7. 决定登记（NC-005，主 Agent 裁定，可推翻）

| 编号 | 决定 | 理由 |
|---|---|---|
| D-NC005-01 | `flush(reason)` 显式带原因，非法组合抛 `IllegalEditorTransition` | SM-1 的非法边需要可断言的触发点 |
| D-NC005-02 | 400 ms 抑制在展示层实现，控制器状态照常切换 | 状态机保持忠实，仅呈现节流 |
| D-NC005-03 | 设备同步/云备份两维度本任务只做枚举、文案、semantics，值由后续任务注入 | NC-016/018 未交付真实值，不造假 |
| D-NC005-04 | 外部图片在 privatePreview 与 publicView 下都默认不自动加载 | DESIGN §5「私密预览默认不自动请求」；公共视图策略留 NC-010，先取保守值 |
| D-NC005-05 | NC-005 只预留 undo 接线点，adapter 与快捷键全部归 NC-006 | TASKS 分工；避免两任务同写一个栈 |

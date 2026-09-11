# NC-005 验证计划

工作目录：`/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（NC-004 已建）。`export PATH=/Users/jingtaiwei/flutter/bin:$PATH`。判据只来自 `contracts/editor.md`（下称契约）与 NC-004 契约。

## 1. 命令

| # | 命令 | 期望 | 自哪一步起 |
|---|---|---|---|
| 1 | `flutter pub get` | 退出 0；`pubspec.lock` 含 `flutter_markdown_plus 1.0.12`、`markdown 7.3.1`；NC-004 九个版本不变 | act/01 |
| 2 | `flutter analyze` | `No issues found!` | 每步 |
| 3 | `flutter test test/editor/save_status_test.dart` | `+8` | act/01 |
| 4 | `flutter test test/editor/note_editor_test.dart` | `+18` | act/02 |
| 5 | `flutter test test/editor/markdown_preview_test.dart` | `+7` | act/03 |
| 6 | `flutter test test/editor/note_editor_page_test.dart` | `+6` | act/04 |
| 7 | `flutter test` | act/04 后 `+74: All tests passed!`（NC-004 的 35 + 8 + 18 + 7 + 6） | 每步 |
| 8 | `git -C <reading-notes> status --short` | 提交后为空 | 每步 |
| 9 | `cd /Users/jingtaiwei/Git/Public/learn_system && bash docs/blackbox-spec-rework/reviews/nc005_guard.sh --require-impl` | 0 | act/04 之后 |

## 2. act/01：三态保存指示（契约 §3）

文件：`lib/src/editor/save_status.dart`（`LocalSaveStatus`、`DeviceSyncStatus`、`CloudBackupStatus` 三个 sealed 类/枚举 + `label(String)`、`isFailure` + `SaveStatusIndicator` Widget（三行，各 `Semantics(label: <文案>)`，失败态含 `Icon` + `Text`）+ `SavingSuppressor`（400 ms 抑制，接受注入 `Clock`/`Ticker`）；`test/editor/save_status_test.dart`；`test/support/fake_clock.dart`。

| 测试名 | 断言 |
|---|---|
| `local labels are verbatim` | 四值 → 「未保存」「保存中」「已保存本机」「保存失败」 |
| `device sync labels are verbatim` | 六值 → 契约 §3 表；`syncing(2,5)`→「同步中(2/5)」；`syncedTo(3)`→「已同步至 3 台」 |
| `cloud backup labels are verbatim` | 七值 → 契约 §3 表；`uploading(42)`→「上传中(42%)」；`backedUpAt('2026-09-11 08:30')`→「已备份至 2026-09-11 08:30」；`unknownOffline('2026-09-11 08:30')`→「状态未知（离线），最后确认备份时间 2026-09-11 08:30」（B19） |
| `not enabled is not a failure` | `CloudBackupStatus.notEnabled.isFailure==false`、`DeviceSyncStatus.notEnabled.isFailure==false`；Widget 树无失败 Icon（B20） |
| `failure states render icon and text` | `failed` 三种各渲染 `Icon` + `Text`，semantics label 含文案（B21、A11Y-04） |
| `semantics labels contain status text` | 三行 `Semantics` 的 label 分别等于三段文案（B17） |
| `saving under 400ms is suppressed` | 注入时钟：`saving` 300 ms 后 `clean`，期间 `find.text('保存中')` 为 nothing（B18） |
| `saving over 400ms is shown` | 500 ms 后显示「保存中」 |

Red：先写 8 个测试与空壳（label 返回空串、Widget 返回 SizedBox），运行命令 3 取得失败原文。

## 3. act/02：控制器 SM-1 与自动保存（契约 §2）

文件：`lib/src/editor/note_editor_controller.dart`（含 `FlushReason` 枚举、`ClipboardPort` 接口、`TimerFactory` 注入）、`test/editor/note_editor_test.dart`、`test/support/fake_repository.dart`（实现 NC-004 `NoteRepository` 的同名方法签名的替身：可编程返回 saved/unchanged、抛指定异常、延迟）。

18 个测试（名称逐字，对应 BDD）：`clean to dirty starts debounce`（B01）、`debounce resets on further input`（B02）、`input during saving sets pending dirty and resaves`（B03）、`saved updates expected head`（B04）、`repository error moves to save failed and keeps buffer`（B05）、`save failed does not auto retry`（B06）、`retry blur leave from save failed start saving`（B07）、`copy all text uses clipboard port`（B08）、`composing pauses debounce`（B09）、`composing end returns to dirty and restarts debounce`（B10）、`leave while composing is refused`（B11）、`illegal flush transitions throw`（B12，四例 subTest 风格用循环）、`blur flushes dirty`（B13）、`unchanged result keeps head`（B14）、`summary change marks touched`（B15）、`editing without bindings works`（B16）、`unimplemented history hook is invoked once per save`（`onHistoryStep` 在每次 saved 后被调用一次，before/after 快照正确）、`last error is cleared after successful retry`。

Red：先写 18 个测试与只保存字段、方法抛 `UnimplementedError` 的控制器，运行命令 4 取得失败原文。

## 4. act/03：Markdown 预览与安全（契约 §5、§5.1）

文件：`lib/src/editor/markdown_preview.dart`（`MarkdownPreview` Widget：`MarkdownBody(data, selectable: true, imageBuilder: _buildImage, onTapLink: ...)`；`_buildImage` 按 scheme 分派；外部图片占位 `ElevatedButton`「外部图片，点击加载」）、`test/editor/markdown_preview_test.dart`、`test/support/counting_image_resolver.dart`（记录 `attachmentResolver` 调用次数；`HttpOverrides` 使任何 HTTP 请求抛异常并计数）。

| 测试名 | 断言 |
|---|---|
| `inline html is not executed` | B22：`find.byType(WebView)`/`Html` 为 nothing（用类型名字符串匹配 `runtimeType.toString()`）；渲染不抛；无回调 |
| `external image is not fetched in private preview` | B23：HTTP 计数 0；存在「外部图片，点击加载」；点击后回调收到 `https://example.com/x.png` |
| `attachment image goes through resolver` | B24：resolver 调用 1 次；`Image` 的 provider 为 `MemoryImage` |
| `unsupported scheme shows placeholder` | B25 |
| `image builder is invoked for every img node` | 三个 img 节点 → `imageBuilder` 计数 3（证明未落入默认 `kDefaultImageBuilder`） |
| `link tap only calls back` | B26 |
| `public view also does not autoload external images` | D-NC005-04 |

Red：先写 7 个测试与直接返回 `MarkdownBody(data)`（无 imageBuilder）的预览，运行命令 5：`image builder is invoked…` 与 `external image is not fetched…` 必须失败（默认实现会走 `Image.network`），保存原文。

## 5. act/04：编辑页整合与 A11Y（契约 §6）

文件：`lib/src/editor/note_editor_page.dart`（`TextField(undoController: widget.undoController)` 参数位透传、软键盘上方工具条含撤销/重做/格式按钮、`SaveStatusIndicator`、`saveFailed` 下「立即重试」「复制全文」按钮、`MarkdownPreview` 切换）、`test/editor/note_editor_page_test.dart`。

| 测试名 | 断言 |
|---|---|
| `undo redo buttons disabled without history and labelled` | B27：`SemanticsFlag.isEnabled=false`，label 「撤销」「重做」 |
| `toolbar sits above keyboard inset` | B27：工具条位于 `MediaQuery.viewInsets.bottom` 之上（用 `MediaQuery` 注入 300 底部 inset 断言工具条 `Rect.bottom <= 屏高-300`） |
| `no overflow at 320 width and 200 percent text` | B28：`tester.takeException()==null`；无横向 `Scrollable` |
| `save failed shows retry and copy actions` | B30 |
| `status indicator is wired to controller state` | 控制器进入 `saving`（>400 ms）后显示「保存中」，`clean` 后「已保存本机」 |
| `no shortcuts registered by page` | Widget 树中无 `Shortcuts`/`CallbackShortcuts`（NC-006 负责）；`Focus` 键盘事件不被拦截 |

Red：先写 6 个测试与只含空 Scaffold 的页面，运行命令 6 取得失败原文。

## 6. Red→Green 与禁止

- 每步先测试后实现；报告贴 Red 原文。
- 禁止：`skip`、永真断言、真实网络、修改 NC-004 文件、注册快捷键、实现 undo 栈、把「取消发布」放进撤销、新增契约外依赖。
- 命令 7 最终 `+74`。

# NC-006 可观察行为

「测试」指 `flutter test <文件>`；adapter 测试用注入的 `now` 函数推进时间；控制器用 NC-005 的 `FakeNoteRepository`，act/01 用不触发的 `TimerFactory`，act/02 用 `FakeAsync`；Widget 测试用 `debugDefaultTargetPlatformOverride` 切平台、`sendKeyDownEvent/sendKeyUpEvent` 发键。B01～B03 逐字对应契约 §7。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 空编辑器 | 以 100 ms 间隔 `recordTextChange` 输入 `a`、`b`、`c`，再 `undo()` | `pastUnits` 曾为 1；文本 `""`，`canRedo=true`，`canUndo=false`，`undoCount=1` |
| B02 | 已输入 `a` | 间隔 499 ms 输入 `b`；再间隔 500 ms 输入 `c` | 499 并入（`pastUnits=1`），500 开新单元（`pastUnits=2`） |
| B03 | 空编辑器 | 100 ms 间隔输入 20 个 `a`，再输入第 21 个 | 前 20 个一个单元，第 21 个 `pastUnits=2` |
| B04 | 空编辑器 | 输入一个四字节 emoji（1 code point）19 次后再输入 `a` | 仍一个单元（按 code point 计 20） |
| B05 | 空编辑器 | 输入 `a`、`b`、` `、`c`、`d`；另一轮用 `\n` 代替空格 | 三个单元：`ab`、空白、`cd`；`undo()` 一次后文本 `ab ` / `ab\n` |
| B06 | 空编辑器 | 单次插入 `hello`，100 ms 内再输入 `x` | `hello` 为 `paste` 封闭单元，`x` 开新单元，`pastUnits=2` |
| B07 | 文本 `abc`，选区 1..2 | 单次变更为 `aXc` | 一个 `replace` 封闭单元；随后 100 ms 内输入 `y` 开新单元 |
| B08 | 100 ms 内输入 `abc` | 100 ms 间隔退格三次 | `pastUnits=2`；`undo()` → `abc`；再 `undo()` → `""` |
| B09 | 输入 `ab` | 仅选区变化（文本不变）后输入 `c` | `pastUnits=2` |
| B10 | 输入 `ab`（光标末尾） | 100 ms 内在偏移 0 插入 `c` | `pastUnits=2`（非连续） |
| B11 | 文本 `x` | `composing=true` 依次变为 `xn`、`xni`、`xnih`，随后 `composing=false` 文本 `x你好` | 组合中 `pastUnits=0`；提交后 `pastUnits=1`，`undo()` → `x` |
| B12 | 文本 `x` | 组合中变为 `xn`，随后 `composing=false` 且文本回到 `x` | `pastUnits=0` |
| B13 | 任意 | `recordCommand(format/imageInsert/mentionInsert)` 各一次；`recordCommand(insert, …)` | 三个封闭单元（100 ms 内也不并）；`insert` 抛 `ArgumentError` |
| B14 | 输入 `a`、`undo()` | 输入 `b`；空重做栈上 `redo()` | `canRedo=false`；`redo()` 不抛且 `redoCount` 不变 |
| B15 | 文本 `ab` 选区 2..2 | `recordCommand(imageInsert, before, after含 1 个 attachmentRef 选区 3..3)`，`undo()`，`redo()` | undo 后 refs 空、选区 2..2；redo 后 refs 1 个、选区 3..3 |
| B16 | 有历史与重做 | `clear()` | `pastUnits=futureUnits=undoCount=redoCount=0`，`canUndo=canRedo=false` |
| B17 | 有历史 | `undo()`、`redo()` | `FakeNoteRepository.calls` 为空（adapter 不调用仓储，不删除图片） |
| B18 | 控制器 `clean`，历史一单元 | `undo()`，`FakeAsync` 推进 2000 ms | 控制器经 `dirty` 进入保存；`saveSnapshot` 收到的快照文本为撤销后文本 |
| B19 | 输入后 `FakeAsync` 推进 2000 ms（saved） | 查询 adapter；`undo()` | `canUndo` 仍 true；撤销成功 |
| B20 | 仓储抛 `NoteSizeLimitExceeded` 进入 `saveFailed` | 查询 adapter | 栈不变，`canUndo=true` |
| B21 | 相同内容再次保存返回 `unchanged` | 查询 adapter | 栈不变 |
| B22 | 历史两单元 | `undo()` 一次 | `pastUnits=1`，`futureUnits=1`（apply 期间不生成新单元） |
| B23 | 输入并保存后 | 用同一替身新建控制器与 adapter（模拟重开） | 新 adapter `canUndo=false`；替身记录的 `saveSnapshot` 调用仍在 |
| B24 | 标题 `T`、`onSummaryChanged("S")`、正文一单元 | `undo()` | 控制器 `snapshot.title=="T"`、`changeSummary=="S"` 不变 |
| B25 | 全流程（输入、撤销、重做、保存、失败重试） | 收集替身调用名 | 去重集合 ⊆ {createNote, saveSnapshot} |
| B26 | 页面正文有历史，平台 windows / linux | Ctrl+Z | 正文回退一个单元，`undoCount=1` |
| B27 | 撤销一次后，平台 windows / linux | Ctrl+Shift+Z；另一轮 Ctrl+Y | 各自重做一次，`redoCount=1` |
| B28 | 平台 macOS | ⌘Z；⌘⇧Z | 撤销一次；重做一次 |
| B29 | 撤销一次后，平台 macOS | Ctrl+Y | 文本不变，`redoCount=0` |
| B30 | 页面正文 `ab`、` `、`cd` 三单元，监听 `TextEditingController` | 一次 Ctrl+Z | `undoCount` 恰 +1；监听回调恰 1 次；文本 `ab ` |
| B31 | 两个相同页面实例，同一输入序列 | 一个用按钮撤销/重做，一个用按键 | 文本、选区、refs、`canUndo/canRedo` 逐项相等 |
| B32 | 焦点在标题输入框，正文有历史 | Ctrl+Z | 正文不变，`undoCount=0` |
| B33 | 页面无历史 → 输入 → 撤销 | 观察按钮 | 初始撤销/重做均 `isEnabled=false`、label 「撤销」「重做」；输入后撤销启用；撤销后重做启用 |
| B34 | 页面渲染 | 取正文 `TextField` | `undoController == null`；`Shortcuts` 恰 1 个、含 `UndoTextIntent` 的 `Actions` 恰 1 个，后代含正文不含标题框 |
| B35 | 注入的 adapter 有历史 | 页面被替换为空 Widget（dispose） | adapter `pastUnits=0` |
| B37 | 页面正文 `x`（一单元） | 用 `tester.testTextInput.updateEditingValue` 依次送 `xn`（composing 1..2）、`xni`（composing 1..3）、`x你`（composing 空） | 组合中控制器 `state=imeComposing`、`canLeave=false`、`pastUnits` 仍 1；提交后 `pastUnits=2`、`state=dirty`；`undo()` 一次 → 文本 `x` |
| B38 | 页面正文 `x` | 送 `xn`（composing 1..2）后送 `x`（composing 空） | `pastUnits` 仍 1（组合取消无单元），`state=dirty` |
| B39 | 页面正文有历史，正在组合（送 `xn` composing 1..2 后不提交） | Ctrl+Z；点击撤销按钮 | 文本仍 `xn`，`undoCount=0`，`pastUnits` 不变 |
| B36 | NC-005 页面测试 | `no shortcuts registered by page` 改名为 `shortcuts and actions wrap only the body field` | 断言同 B34 树结构；NC-005 其余测试与 `+75` 计数不变 |

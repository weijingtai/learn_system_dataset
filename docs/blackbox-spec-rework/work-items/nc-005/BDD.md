# NC-005 可观察行为

「测试」指 `flutter test <文件>`；控制器测试用 `FakeAsync` 推进虚拟时间；仓储用 `FakeNoteRepository`（可注入成功/异常/延迟）。

| ID | Given | When | Then |
|---|---|---|---|
| B01 | 控制器 `clean` | `onTextChanged` | 状态 `dirty`；虚拟时间推进 1999 ms 不调用仓储，2000 ms 调用一次 `saveSnapshot` 并进入 `saving` |
| B02 | `dirty` 且去抖未到 | 再次 `onTextChanged` | 去抖重置：从最后一次输入起 2000 ms 才保存 |
| B03 | `saving`（仓储延迟 500 ms） | `onTextChanged` | 状态仍 `saving`，`pendingDirty=true`；首次保存完成后立即再保存一次，最终 `clean` 且仓储被调用 2 次 |
| B04 | `saving` | 仓储返回 saved | `clean`；`expectedHeadId` 更新为新修订 |
| B05 | `saving` | 仓储抛 `NoteSizeLimitExceeded` | `saveFailed`；`lastError` 为该异常；缓冲文本不变 |
| B06 | `saveFailed` | `onTextChanged` | 仍 `saveFailed`，缓冲更新，虚拟时间推进 10 s 仓储不被调用（不自动重试） |
| B07 | `saveFailed` | `flush(retry)` / `flush(blur)` / `flush(leave)` | 进入 `saving` 并调用仓储 |
| B08 | `saveFailed` | `copyAllText` | 剪贴板端口收到全文；状态不变 |
| B09 | `clean` 或 `dirty` | `onComposingChanged(true)` | `imeComposing`；去抖暂停（推进 5 s 不保存） |
| B10 | `imeComposing` | `onComposingChanged(false)` | `dirty`，去抖重启 |
| B11 | `imeComposing` | `flush(leave)` | 状态不变，`canLeave=false` |
| B12 | `clean` | `flush(debounce)` 或 `flush(retry)`；`saving` 下 `flush(retry)`/`flush(blur)`/`flush(leave)`；`imeComposing` 下 `flush(debounce)` | 抛 `IllegalEditorTransition`，状态不变 |
| B13 | `dirty` | `flush(blur)` | `saving`（失焦 flush） |
| B14 | 相同内容再次保存 | 去抖到期 | 仓储返回 `unchanged`，状态 `clean`，不产生新 head |
| B15 | `onSummaryChanged("Y")` | 去抖到期 | 调用仓储时 `summaryTouched=true`、快照 changeSummary=Y |
| B16 | 无书籍上下文（`bindings` 空） | 全流程 | 一切照常（无书籍也能编辑） |
| B17 | 三态枚举全部取值 | 渲染 | 文案与契约 §3 表逐字相等；semantics label 含该文案 |
| B18 | `saving` 持续 300 ms 后 `clean` | 渲染 | 期间从未显示「保存中」；持续 500 ms 则显示 |
| B19 | 云备份 `unknownOffline(lastKnown)` | 渲染 | 文案 `状态未知（离线），最后确认备份时间 2026-09-11 08:30`；不显示「已备份」 |
| B20 | 云备份 `notEnabled` | 渲染 | 「未开启」且 `isFailure=false`（无失败图标/样式） |
| B21 | 任一维度失败态 | 渲染 | 存在失败图标 + 文字两者；semantics 含文字 |
| B22 | Markdown 含 `<script>alert(1)</script><img src=x onerror=alert(2)>` | 预览 | 无 WebView/Html Widget；文本按普通字符或忽略处理；无任何回调触发 |
| B23 | Markdown 含 `![a](https://example.com/x.png)`，`privatePreview` | 预览 | 网络图片请求计数 0；出现「外部图片，点击加载」按钮；点击后 `onRequestExternalImage` 收到该 Uri |
| B24 | Markdown 含 `![b](attachment://img-a1)` | 预览 | `attachmentResolver('img-a1')` 被调用 1 次，渲染 `Image.memory` |
| B25 | Markdown 含 `![c](ftp://h/x.png)` | 预览 | 占位「不支持的图片来源」，无网络请求 |
| B26 | 预览含链接 | 点击 | `onTapLink` 回调收到 href；包内不调用 `launchUrl` |
| B27 | 编辑页，无历史 | 渲染 | 撤销/重做按钮 `isEnabled=false`，semantics label 「撤销」/「重做」；按钮位于软键盘上方工具条 |
| B28 | 320 逻辑像素宽 × `MediaQueryData(textScaler: TextScaler.linear(2.0))` | 渲染编辑页 | 无 overflow 异常；无横向 `Scrollable`；`flutter analyze` 无 deprecated 提示 |
| B29 | `pubspec.yaml` | 读取 | 仅新增 `flutter_markdown_plus: 1.0.12`；NC-004 九个版本不变 |
| B30 | 编辑页在 `saveFailed` | 渲染 | 显示「保存失败」及「立即重试」「复制全文」两个按钮 |
| B31 | 全流程自动保存（新建、三次编辑、失败重试） | 记录替身收到的方法调用 | 只调用了 `saveSnapshot`（与 `createNote`）；替身的其他方法零调用；包内不存在发布接口（自动保存不改变已发布正文） |

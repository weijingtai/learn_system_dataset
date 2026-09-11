# NC-005 独立验收

当前：NOT_EXECUTED。派发前置：NC-004 ACCEPTED。

1. ACT 审查：未参与编写者做 wjt-react 四查；本文不自签 READY。
2. 范围：`reading-notes` 新增恰 4 个提交（在 NC-004 五个之后），`git show --name-only` 逐一核对只含各 ACT WRITE_NEW；`git diff <NC-004 末提交> HEAD -- lib/src/domain lib/src/persistence test/persistence test/contracts` 为空；`pubspec.yaml` 相对 NC-004 只多一行。
3. 重跑 TDD §1 全部 9 条命令并记录退出码：`flutter analyze` 0；`flutter test` `+75: All tests passed!`；lock 含 `flutter_markdown_plus 1.0.12`、`markdown 7.3.1`；`nc005_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时测试文件，不入库）：① 去抖边界 1999/2000/2001 ms；② `saving` 恰 400 ms 的抑制边界（≤400 不显示、>400 显示，按契约「不足 400 ms 不显示」取闭区间：400 ms 仍不显示）；③ Markdown 含 `<iframe src=javascript:...>` 与 `![x](HTTPS://EXAMPLE.COM/A.PNG)`（大写 scheme）——后者也必须走占位、不联网；④ 三态文案与 PRD §6.1 表逐字 diff（用脚本从 PRD 抽表比对）。
5. 作弊扫描：测试无 `skip`、`expect(true`；预览实现无 `Image.network`/`NetworkImage` 字面量；页面无 `Shortcuts(`/`CallbackShortcuts(`；控制器无 `Timer(`（必须经注入的 TimerFactory）。
6. 流程核对：每个提交同时含测试与实现；报告给出真实 Red 原文。
7. 通过后只验收 NC-005；NC-006 以本包 README 的撤销栈裁定为输入。

证据记录格式：commit；实际文件；每条 command/exit_code/原始摘要；Red 原文；盲测输出；跳过项与剩余阻塞。

## 验收记录（主 Agent，2026-09-11）：ACCEPTED

- 提交：reading-notes `10ef174`（A）、`9e6ea2b`（B）、`4c8440a`（C）、`8b05a68`（D），恰 4 个，位于 NC-004 `957536c` 之后；工作树除未跟踪 `DELIVERY_REPORT.md` 外干净。
- 范围：`git diff 957536c HEAD --stat -- lib/src/domain lib/src/persistence test/persistence test/contracts` 为空；`pubspec.yaml` 只多 `flutter_markdown_plus: 1.0.12` 一行；lock 中 `flutter_markdown_plus 1.0.12`、`markdown 7.3.1`、`drift 2.31.0`。
- **偏离一处（已裁定接受）**：act/04 提交额外改了 `lib/src/editor/save_status.dart` 3 行——把私有方法 `_startSavingTimer` 改名为 `_startSuppressSchedule`，无行为变化。起因是守卫 K05 用子串 `Timer(` 扫描，把 `_startSavingTimer(` 误判为裸构造；执行方按流程停手，用户当场裁定改名。报告在 4.1 节如实写明。根因在主 Agent 的守卫，已把 `nc005_guard.sh`、`nc006_guard.sh` 的该项改为只匹配裸 `Timer(`（前面不是标识符字符）。
- 守卫：`nc005_guard.sh --require-impl` K01～K05 全 PASS（analyze 0，`flutter test +75`，无 `Image.network`/`Shortcuts(`/`textScaleFactor`/作弊模式，NC-004 文件未触碰）。
- 报告：四步均附真实 Red 原文（act/01 三处 `Semantics` 断言失败、act/02 `UnimplementedError`、act/03、act/04 编译期与断言失败）与 Green 命令退出码；未运行项无；DEFERRED 五条与 ACT.yaml 一致，未把 NC-006/007/010/016/018 说成完成。
- 盲测（临时文件，已删除）：① 去抖 1999 ms 不保存、2000 ms 恰一次、2001 ms 仍一次，`expectedHeadId` 更新；② `SavingSuppressor` 注入时钟：399/400 ms 抑制（闭区间）、401 ms 显示「保存中」，100 ms 内转失败从未显示中间态；③ Markdown 含 `<iframe src=javascript:>`、`<script>`、`![x](HTTPS://EXAMPLE.COM/A.PNG)`、`![y](Attachment://img-9)`、`![z](FTP://h/x.png)`：`HttpOverrides` 计数 0，外部图片显示「外部图片，点击加载」且点击只回调不联网，附件解析器恰调用 1 次，FTP 显示「不支持的图片来源」；④ 文案：PRD §6.1 三行 17 个取值与 Dart 文案（占位符归一后）双向差集为空，离线文案为「状态未知（离线），最后确认备份时间 <值>」；⑤ 控制器：保存失败后 30 s 不自动重试、缓冲保留、`retry` 后 `clean` 且 `lastError` 清空，IME 组合中 `leave` 拒绝、`debounce` 抛 `IllegalEditorTransition`，组合结束后 2000 ms 照常保存。
- 源码核对：`applySnapshot` 目前只替换缓冲不进入 `dirty`（NC-006 act/02 已预留改动权）；`SavingSuppressor` 无时钟时回退 `DateTime.now()`（生产默认，测试注入）；页面用 `TextEditingController` 监听器而非 `onChanged`（与 NC-006 契约 §5.1 一致）；撤销/重做按钮 `Semantics(enabled:false)` + `onPressed:null`。
- 判定：**ACCEPTED**。NC-006 派发前置满足；NC-006 README 基线回填 `8b05a68`。

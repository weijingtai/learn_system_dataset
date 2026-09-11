# NC-005 独立验收

当前：NOT_EXECUTED。派发前置：NC-004 ACCEPTED。

1. ACT 审查：未参与编写者做 wjt-react 四查；本文不自签 READY。
2. 范围：`reading-notes` 新增恰 4 个提交（在 NC-004 五个之后），`git show --name-only` 逐一核对只含各 ACT WRITE_NEW；`git diff <NC-004 末提交> HEAD -- lib/src/domain lib/src/persistence test/persistence test/contracts` 为空；`pubspec.yaml` 相对 NC-004 只多一行。
3. 重跑 TDD §1 全部 9 条命令并记录退出码：`flutter analyze` 0；`flutter test` `+74: All tests passed!`；lock 含 `flutter_markdown_plus 1.0.12`、`markdown 7.3.1`；`nc005_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时测试文件，不入库）：① 去抖边界 1999/2000/2001 ms；② `saving` 恰 400 ms 的抑制边界（≤400 不显示、>400 显示，按契约「不足 400 ms 不显示」取闭区间：400 ms 仍不显示）；③ Markdown 含 `<iframe src=javascript:...>` 与 `![x](HTTPS://EXAMPLE.COM/A.PNG)`（大写 scheme）——后者也必须走占位、不联网；④ 三态文案与 PRD §6.1 表逐字 diff（用脚本从 PRD 抽表比对）。
5. 作弊扫描：测试无 `skip`、`expect(true`；预览实现无 `Image.network`/`NetworkImage` 字面量；页面无 `Shortcuts(`/`CallbackShortcuts(`；控制器无 `Timer(`（必须经注入的 TimerFactory）。
6. 流程核对：每个提交同时含测试与实现；报告给出真实 Red 原文。
7. 通过后只验收 NC-005；NC-006 以本包 README 的撤销栈裁定为输入。

证据记录格式：commit；实际文件；每条 command/exit_code/原始摘要；Red 原文；盲测输出；跳过项与剩余阻塞。

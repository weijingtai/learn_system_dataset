# NC-006 独立验收

当前：NOT_EXECUTED。派发前置：NC-005 ACCEPTED。

1. ACT 审查：未参与编写者做 wjt-react 四查；本文不自签 READY。
2. 范围：`reading-notes` 新增恰 3 个提交（在 NC-005 四个之后），`git show --name-only` 逐一核对只含各 ACT WRITE_NEW；TDD 命令 7 的 diff 为空；`pubspec.yaml`/`pubspec.lock` 零变化；`note_editor_page_test.dart` 的 diff 只涉及一个测试（`testWidgets(` 计数不变，删除行含 `no shortcuts registered by page`，新增行含 `shortcuts and actions wrap only the body field`）。
3. 重跑 TDD §1 全部 10 条命令并记录退出码：`flutter test` `+110: All tests passed!`；`nc006_guard.sh --require-impl` 0。
4. 主 Agent 盲测（临时测试文件，不入库）：① 间隔恰 `undoMergeMaxGapMs` 毫秒开新单元、少 1 毫秒并入；② 第 `undoMergeMaxChars` 个 code point 并入、下一个开新单元，混入一个 4 字节 emoji 仍按 code point 计；③ 全角空格 U+3000 与制表符 `\t` 作为片段自成封闭单元（`\s` 语义）；④ 页面上 Ctrl+Z 一次后用 `TextEditingController` 监听计数与 `undoCount` 双重断言不双撤销，且 Android 平台（`debugDefaultTargetPlatformOverride = android`）Ctrl+Z 同样生效；⑤ 组合中收到 `undo()`：契约未定义时按「组合中 undo 为 no-op」验证 adapter 不抛异常并把结果写入决定登记；⑥ 撤销后 2000 ms 自动保存的快照文本与撤销后 `TextEditingController.text` 相同。
5. 作弊扫描：adapter 无 `DateTime.now(`/`Timer(`/`Stopwatch(`/字面量 500、20；`lib/src/editor/` 无 `UndoHistoryController`；`Shortcuts(` 恰在页面出现 1 次；测试无 `skip`、`expect(true`。
6. 流程核对：每个提交同时含测试与实现；报告给出真实 Red 原文；act/02 一开始即绿的测试有解释。
7. 通过后只验收 NC-006；D-NC006-06（iOS 原生 UndoManager）登记到 NC-024 的设备级验收清单，不在本包关闭。

证据记录格式：commit；实际文件；每条 command/exit_code/原始摘要；Red 原文；盲测输出；跳过项与剩余阻塞。

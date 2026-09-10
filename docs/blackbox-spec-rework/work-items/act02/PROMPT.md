# ACT 02 执行 Agent Prompt

你是 ACT 02 执行 Agent。仓库是 `/Users/jingtaiwei/Git/Public/learn_system`。只在当前分支和 worktree 工作，禁止切换分支。

先完整阅读：
- `docs/blackbox-spec-rework/work-items/act02/README.md`
- `docs/blackbox-spec-rework/work-items/act02/BDD.md`
- `docs/blackbox-spec-rework/work-items/act02/TDD.md`
- `docs/blackbox-spec-rework/work-items/act02/ACT.yaml`

【执行铁律】：
1. 必须执行真实 TDD 仪式（分步双提交）：
   - 先编写 `pattern_knowledge_workbench/test/verified_gate_test.dart`；
   - 运行测试证明其在当前代码下失败（Red）；
   - 提交红灯测试：`test(workbench): 保存不得自动置 verified(红) ｜ TASK_ID workbench-r0/02`；
   - 再修改 `pattern_knowledge_workbench/lib/pages/rule_list_page.dart`：
     - 位置 1（约 1178 行，人工保存）：删除 `isVerified: const Value(true),`；
     - 位置 2（约 1778 行，AI保存）：将 `isVerified: const Value(true),` 改为 `isVerified: const Value(false),`；
   - 运行测试证明其转绿（Green）；
   - 运行代码检查确认 `grep -c 'isVerified: const Value(true)'` 为 0；
   - 运行 `flutter analyze --no-fatal-infos`（必须 0 warning，退出 0）与 `flutter test`（退出 0）；
   - 运行全局回归脚本 `bash docs/blackbox-spec-rework/verify-T.sh` 确认退出码 17；
   - 确认 `git diff --check` 通过；
   - 提交绿灯实现：`fix(workbench): 保存与 AI 产物不再自动置 verified ｜ TASK_ID workbench-r0/02`。
2. 严禁改动 `tables.dart`、`drift_database.dart` 或 `assets/`；保留显式勾选通道不变。
3. 遇到任何未预期的分析器报错或测试阻断，严禁自己做决定，必须立即停止并向上汇报！

最终报告必须包含：两个 commit hash（Red 和 Green）、修改文件清单、Red 阶段失败输出、Green 阶段成功输出、静态分析与全套测试运行结果、全局 T 脚本对比及剩余风险。

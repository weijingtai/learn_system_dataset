# ACT 01 执行 Agent Prompt

你是 ACT 01 执行 Agent。仓库是 `/Users/jingtaiwei/Git/Public/learn_system`。只在当前分支和 worktree 工作，禁止切换分支。

先完整阅读：
- `docs/blackbox-spec-rework/work-items/act01/README.md`
- `docs/blackbox-spec-rework/work-items/act01/BDD.md`
- `docs/blackbox-spec-rework/work-items/act01/TDD.md`
- `docs/blackbox-spec-rework/work-items/act01/ACT.yaml`

【执行铁律】：
1. 必须执行真实 TDD 仪式：
   - 先编写 `pattern_knowledge_workbench/test/database_persistence_test.dart`；
   - 运行测试证明其在当前代码下失败（Red）；
   - 提交红灯测试：`test(workbench): 本地库不得被启动覆盖(红) ｜ TASK_ID workbench-r0/01`；
   - 再修改 `pattern_knowledge_workbench/lib/database/drift_database.dart`，加入 `if (!await dbFile.exists())` 判断；
   - 运行测试证明其转绿（Green）；
   - 运行 `flutter analyze --no-fatal-infos`（必须 0 warning，退出 0）与 `flutter test`（退出 0）；
   - 提交绿灯实现：`fix(workbench): 本地库改为仅在缺失时播种，不再启动覆盖 ｜ TASK_ID workbench-r0/01`。
2. 严禁修改 `assets/ge_ju_database.sqlite`、`tables.dart` 或 `lib/pages/`。
3. 遇到任何未预期的分析器报错或测试阻断，严禁自己做决定，必须立即停止并向上汇报！

最终报告必须包含：两个 commit hash（Red 和 Green）、修改文件清单、Red 阶段失败输出、Green 阶段成功输出、静态分析与全套测试运行结果、全局 T 脚本对比及剩余风险。

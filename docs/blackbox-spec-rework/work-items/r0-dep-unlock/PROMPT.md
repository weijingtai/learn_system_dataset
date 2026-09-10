# R0 依赖解锁执行 Agent Prompt

你是 R0 依赖解锁执行 Agent。仓库是 `/Users/jingtaiwei/Git/Public/learn_system`。只在当前分支和 worktree 工作，禁止切换分支。

先完整阅读：
- `docs/blackbox-spec-rework/work-items/r0-dep-unlock/README.md`
- `docs/blackbox-spec-rework/work-items/r0-dep-unlock/BDD.md`
- `docs/blackbox-spec-rework/work-items/r0-dep-unlock/TDD.md`
- `docs/blackbox-spec-rework/work-items/r0-dep-unlock/ACT.yaml`
- `docs/blackbox-spec-rework/work-items/r0-dep-unlock/act/01.yaml`
- `docs/blackbox-spec-rework/work-items/r0-dep-unlock/act/02.yaml`

必须严格按 `workbench-r0/03 → workbench-r0/04` 顺序执行，不得并行或合并提交。

【执行铁律】：
1. 严禁引入任何第三方私有镜像、替代包、临时 Mock，严禁把 192.168 改为其他内网地址。
2. 严禁修改 `pattern_knowledge_workbench/lib/database/` 或 `assets/`。
3. 遇到任何未预期的分析器报错或环境阻断，严禁自己做决定，必须立即停止并向上汇报！
4. 子 ACT 1（`workbench-r0/03`）：在 `pubspec.yaml` 中仅删除 `enumeration` 声明，运行 ACT 01 门禁通过后提交，提交消息：`chore(workbench): 删除零引用的内网依赖 enumeration ｜ TASK_ID workbench-r0/03`。
5. 子 ACT 2（`workbench-r0/04`）：
   - 删除 `pubspec.yaml` 中两处 `ai_core`，清理 `chat_page.dart`、`ai_chat_controller.dart`、`rule_list_page.dart`、`main.dart` 中的 `package:ai_core` 引用并替换为无依赖安全占位（确保 `ai_recognition_dialog.dart` 等调用方编译安全）；
   - 【用户正式授权的最小范围扩展】：在 `main_page.dart` 中仅删除 3 处 unused_import（provider, drift_database, rule_provider）；在 `db_provider.dart` 中仅删除 1 处 unused_import（drift/drift.dart）。严禁修改这两个文件的任何其他内容，不碰现有 11 条 info 级 avoid_print 提示；
   - 运行 `flutter pub get`、`flutter analyze --no-fatal-infos`（必须 0 warning，退出码 0）与 `flutter test`（退出码 0）；
   - 将 `pub get` 自动更新的 `pubspec.lock` 与各平台 generated plugin 文件纳入提交（并在报告中证明它们完全由依赖移除自动产生，无人工手改）；
   - 门禁全绿后提交，提交消息：`refactor(workbench): 剥离 ai_core 聊天旁路与内网依赖 ｜ TASK_ID workbench-r0/04`。

最终报告必须包含：两个 commit hash、每个 commit 的修改文件清单（含自动生成的 lock/registrant 文件及无手改证明）、Red baseline 记录、`pub get`/`analyze`/`test` 运行原始输出摘要、全局 T 脚本前后状态与剩余风险。


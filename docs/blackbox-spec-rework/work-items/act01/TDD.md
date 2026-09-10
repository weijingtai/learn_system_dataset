# ACT 01 TDD 门禁与用例

## 1. Red 门禁步骤与仪式

1. 先在 `pattern_knowledge_workbench/test/database_persistence_test.dart` 编写测试：
   - 模拟或验证 `databaseDirectory` 回调逻辑；
   - 断言：当 `dbFile.exists()` 为 true 时，不调用 `writeAsBytes`，且现有文件内容不被覆盖；
   - 针对当前代码运行 `cd pattern_knowledge_workbench && flutter test test/database_persistence_test.dart`，期望失败（Red）。
2. 保存并提交红灯测试：
   - 提交消息：`test(workbench): 本地库不得被启动覆盖(红) ｜ TASK_ID workbench-r0/01`

## 2. Green 实现与门禁

1. 在 `pattern_knowledge_workbench/lib/database/drift_database.dart` 中加入 `if (!await dbFile.exists())` 存在性判断。
2. 运行 `cd pattern_knowledge_workbench && flutter test test/database_persistence_test.dart`，期望转绿（Green）。
3. 运行代码检查命令：
   - `grep -c "await dbFile.writeAsBytes" pattern_knowledge_workbench/lib/database/drift_database.dart`（期望 1）
   - `grep -A2 'if (!await dbFile.exists())' pattern_knowledge_workbench/lib/database/drift_database.dart | grep -q 'rootBundle.load'`（期望退出 0）
4. 运行全套工作台分析与测试：
   - `cd pattern_knowledge_workbench && flutter analyze --no-fatal-infos`（期望退出 0）
   - `cd pattern_knowledge_workbench && flutter test`（期望退出 0）
5. 运行全局回归验证：
   - `bash docs/blackbox-spec-rework/verify-T.sh`（期望退出码 17）
6. 检查 `git diff --check`（无格式空白问题）。
7. 提交绿灯实现：
   - 提交消息：`fix(workbench): 本地库改为仅在缺失时播种，不再启动覆盖 ｜ TASK_ID workbench-r0/01`

## 3. 防假绿要求

- 测试必须真实检验目标文件已存在时 `writeAsBytes` 是否被跳过，不得写空断言；
- 严禁删除 migration 或改动 schemaVersion。

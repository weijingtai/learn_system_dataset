# ACT 02 TDD 门禁与用例

## 1. Red 门禁步骤与仪式

1. 在 `pattern_knowledge_workbench/test/verified_gate_test.dart` 编写测试用例：
   - 用例 1：验证对未核验规则执行人工编辑保存后，`isVerified` 不得变为 `true`（当前在 `isVerified: const Value(true)` 下必定失败）；
   - 用例 2：验证对已核验（`isVerified == true`）的规则保存 AI 条件后，`isVerified` 必须回落为 `false`（当前在 `isVerified: const Value(true)` 下必定失败）；
   - 用例 3：验证显式勾选通道依然能够将规则置为 `true`。
2. 针对当前未修改代码运行：
   ```bash
   cd pattern_knowledge_workbench && flutter test test/verified_gate_test.dart
   ```
   期望退出码为 1（Red）。
3. 提交红灯测试：
   - 提交消息：`test(workbench): 保存不得自动置 verified(红) ｜ TASK_ID workbench-r0/02`

## 2. Green 实现与门禁

1. 在 `pattern_knowledge_workbench/lib/pages/rule_list_page.dart` 中：
   - 位置 1（约 1178 行）：删除 `isVerified: const Value(true),`；
   - 位置 2（约 1778 行）：修改为 `isVerified: const Value(false),`。
2. 运行单元测试验证转绿：
   ```bash
   cd pattern_knowledge_workbench && flutter test test/verified_gate_test.dart
   ```
   期望退出码为 0（Green）。
3. 运行代码检查命令：
   - `test $(grep -c 'isVerified: const Value(true)' pattern_knowledge_workbench/lib/pages/rule_list_page.dart) -eq 0`（期望为 0）
   - `test $(grep -c 'isVerified' pattern_knowledge_workbench/lib/pages/rule_list_page.dart) -ge 3`（期望 >=3）
4. 运行全套工作台分析与测试：
   - `cd pattern_knowledge_workbench && flutter analyze --no-fatal-infos`（期望退出 0，0 error, 0 warning）
   - `cd pattern_knowledge_workbench && flutter test`（期望退出 0，全部测试通过）
5. 运行全局回归验证：
   - `bash docs/blackbox-spec-rework/verify-T.sh`（期望退出码 17）
6. 检查 `git diff --check`（无格式空白问题）。
7. 提交绿灯实现：
   - 提交消息：`fix(workbench): 保存与 AI 产物不再自动置 verified ｜ TASK_ID workbench-r0/02`

## 3. 防假绿要求

- 测试必须直接验证保存逻辑对 `isVerified` 列的真实影响；
- `isVerified: const Value(true)` 必须在 `rule_list_page.dart` 中完全清除。

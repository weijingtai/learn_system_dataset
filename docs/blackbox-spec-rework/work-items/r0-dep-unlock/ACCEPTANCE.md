# R0 依赖解锁主 Agent 验收清单

状态：`ACCEPTED`（2026-09-09）

## 1. Scope and Commits

- [x] ACT 01 与 ACT 02 独立提交且顺序严格：`workbench-r0/03` (`ffda853`) 先于 `workbench-r0/04` (`2e11932`)
- [x] 提交修改文件严格限定在各自的 `scope.write` 内（含正式授权的 main_page/db_provider 4 处 unused_import 修复及 pub get 自动生成的 lock/registrant 文件，无其他越界）
- [x] 证明各平台 generated plugin 文件与 `pubspec.lock` 完全由依赖移除自动产生，无人工手改
- [x] 未修改工作台数据库结构、migration、`tables.dart` 或 `assets/`
- [x] 未修改架构规格、其他工作包或 `verify-T.sh`

## 2. Red-Green Evidence

- [x] 执行前记录了 `192.168` 计数为 3，`ai_core` 引用为 3，且 `flutter pub get` 报错（退出码 1）
- [x] ACT 01 提交后 `enumeration.git` 归零，`192.168` 降为 2
- [x] ACT 02 提交后 `192.168` 严格为 0
- [x] 源码中 `package:ai_core` 导入计数严格为 0
- [x] `cd pattern_knowledge_workbench && flutter pub get` 成功退出 0
- [x] `cd pattern_knowledge_workbench && flutter analyze --no-fatal-infos` 成功退出 0（0 errors, 0 warnings）
- [x] `cd pattern_knowledge_workbench && flutter test` 执行并通过（`All tests passed!`）

## 3. Anti-Fake-Green Review

- [x] 未引入任何临时 Mock 包或替代内网 Git 地址
- [x] 未使用 `|| true` 掩盖 `pub get` 或 `analyze` 失败
- [x] 确实在真实干净环境下完成依赖求解

## 4. Regression and Review

- [x] `git diff --check` 通过
- [x] 全局 T 失败数不高于 17（实测保持 17 FAIL / 2 PASS）
- [x] 规格符合性审查通过（符合 2026-09-08 剥离 AI 聊天旁路决议）
- [x] 质量审查通过
- [x] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`ACCEPTED`。内网私有依赖彻底解除，工作台构建、分析与测试环境完全恢复，ACT 01 与 ACT 02 的前置死锁已彻底消除。


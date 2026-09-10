# R0 依赖解锁 BDD 场景

## B1 零引用依赖清除（enumeration）

Given `pattern_knowledge_workbench` 的 `*.dart` 文件对 `enumeration` 引用数为 0，
When 执行者从 `pubspec.yaml` 中删除 `enumeration` 的 git 依赖配置，
Then `pubspec.yaml` 中不再包含 `enumeration.git`，且全仓 Dart 文件无任何断链引用。

## B2 私有内网依赖彻底剥离（ai_core）

Given `pubspec.yaml` 在 `dependencies` 与 `dependency_overrides` 中引用了 `http://192.168.0.165:3000` 的 `ai_core`，
When 执行者完成 ACT 02 剥离工作，
Then `pubspec.yaml` 中 `grep -c '192.168'` 严格为 0，工作台不再依赖任何内网 Git 服务。

## B3 源码中私有包导入归零

Given `lib/pages/chat_page.dart`、`lib/providers/ai_chat_controller.dart` 与 `lib/pages/rule_list_page.dart` 中存在 `package:ai_core` 导入，
When 执行者完成代码改造与剥离，
Then `grep -rc 'package:ai_core' lib/` 严格为 0，不再引用任何私有库类型与组件。

## B4 依赖求解与环境恢复

Given 之前因 `ai_core` 传递依赖冲突导致 `flutter pub get` 无法求解（`version solving failed`），
When 移除了 `enumeration` 与 `ai_core` 两个内网依赖后，
Then 再次执行 `flutter pub get` 能够在无私有内网网络的情况下快速成功解析全部公开依赖，退出码为 0。

## B5 静态分析全绿无语法错误

Given 移除了 AI 聊天相关页面组件与私有依赖，
When 执行 `flutter analyze --no-fatal-infos`，
Then 分析器报告 0 错误（`No issues found!`），无任何类型未定义、缺失导入或方法调用异常。

## B6 已有测试持续通过

Given 工作台已有单元测试套件，
When 运行 `flutter test`，
Then 已有测试全部通过，未因本次依赖剥离引入任何回归失败。

## B7 架构边界符合性

Given 2026-09-08 架构决议明确：Review Console 仅审核版本化 Candidate，模型调用归 M4 Model Adapter，禁止前端直连模型旁路写库，
When 执行本次剥离后，
Then 工作台内消除了直接调用大模型并保存核验数据的旁路通道。

# R0 依赖解锁工作包：清除内网私有依赖并剥离 AI 聊天旁路

状态：`READY`（按 2026-09-09 用户决策制定，通过 ACT 审查）

## 1. Goal

彻底解除 `pattern_knowledge_workbench` 对私有内网 Git（`http://192.168.0.165:3000`）的全部依赖（`enumeration` 与 `ai_core`），消除版本求解死锁；同步剥离工作台内的直连 AI 聊天旁路 UI、Controller 与 Provider 挂载，使工作台恢复纯公开依赖构建与测试能力，为后续 ACT 01 与 ACT 02 的真实测试解锁。

## 2. Authority and Background

- `PLAN.md` R0 第 3 条
- `docs/blackbox-spec-rework/act/03.yaml`（删除零引用 enumeration）
- `docs/blackbox-spec-rework/act/04.yaml`（剥离 ai_core 聊天旁路）
- 2026-09-08 用户批准决议：工作台 AI 聊天从 Review Console 剥离；未来模型能力仅通过 M4 Model Adapter 接入
- 2026-09-09 用户调度决策：采用方案 A（ACT 03 → ACT 04 → ACT 01 → ACT 02），ACT 03 与 ACT 04 合并为本依赖解锁工作包，内部顺序执行、独立提交，严禁假 Mock 与内网恢复

## 3. Sub-ACT Breakdown

本工作包分为两个不可并行的连续子 ACT，必须顺序执行并分别提交：

| 子 ACT | 任务 ID | 内容 | 目标文件 | 提交消息 |
|---|---|---|---|---|
| ACT 01 | `workbench-r0/03` | 删除零引用的内网依赖 enumeration | `pattern_knowledge_workbench/pubspec.yaml` | `chore(workbench): 删除零引用的内网依赖 enumeration ｜ TASK_ID workbench-r0/03` |
| ACT 02 | `workbench-r0/04` | 剥离 ai_core 聊天旁路与内网依赖 | 见下方 Scope | `refactor(workbench): 剥离 ai_core 聊天旁路与内网依赖 ｜ TASK_ID workbench-r0/04` |

## 4. Scope

### ACT 01 (workbench-r0/03)
- WRITE:
  - `pattern_knowledge_workbench/pubspec.yaml`
- READ:
  - `pattern_knowledge_workbench/pubspec.yaml`

### ACT 02 (workbench-r0/04)
- WRITE:
  - `pattern_knowledge_workbench/lib/pages/chat_page.dart`
  - `pattern_knowledge_workbench/lib/providers/ai_chat_controller.dart`
  - `pattern_knowledge_workbench/lib/pages/rule_list_page.dart`
  - `pattern_knowledge_workbench/lib/main.dart`
  - `pattern_knowledge_workbench/pubspec.yaml`
  # 用户 2026-09-09 正式授权的最小范围扩展（仅清理 4 处 unused_import 以满足 0 warning 门禁）：
  - `pattern_knowledge_workbench/lib/pages/main_page.dart`
  - `pattern_knowledge_workbench/lib/providers/db_provider.dart`
  # flutter pub get 自动更新/生成的锁文件与平台插件注册文件（证明无人工修改）：
  - `pattern_knowledge_workbench/pubspec.lock`
  - `pattern_knowledge_workbench/macos/Flutter/GeneratedPluginRegistrant.swift`
  - `pattern_knowledge_workbench/linux/flutter/generated_plugin_registrant.cc`
  - `pattern_knowledge_workbench/linux/flutter/generated_plugins.cmake`
  - `pattern_knowledge_workbench/windows/flutter/generated_plugin_registrant.cc`
  - `pattern_knowledge_workbench/windows/flutter/generated_plugins.cmake`
- READ:
  - 上述写入文件
  - `pattern_knowledge_workbench/lib/pages/dialogs/ai_recognition_dialog.dart`


## 5. Implementation Strategy

1. **ACT 01（删除 enumeration）**：
   - 确认全仓 `*.dart` 无 `enumeration` 引用；
   - 在 `pubspec.yaml` 中仅删除 `enumeration` 的 4 行 Git 依赖声明，其余保持不变；
   - 独立提交 commit 1。
2. **ACT 02（剥离 ai_core 与聊天）**：
   - `pubspec.yaml`：删除 `ai_core` 在 `dependencies`（4 行）与 `dependency_overrides`（4 行）的两处声明；
   - `chat_page.dart`：移除 `package:ai_core` 导入与 `AiChatView` 使用，替换为说明页面（提示 AI 对话功能已剥离，模型能力经 M4 流水线接入）；
   - `ai_chat_controller.dart`：移除全部 `package:ai_core` 导入；保留纯 Dart 控制器骨架（实现 `isInitialized` 与 `recognizeCondition` 降级占位），供已有 UI 对话框类型推断与编译安全使用，不产生编译报错；
   - `rule_list_page.dart`：移除 `package:ai_core` 导入与 Drawer 中的 `AiChatView` 嵌入，替换为功能剥离说明或保留空面板；
   - `main.dart`：移除或保留无害化的控制器挂载；
   - 独立提交 commit 2。
3. **完成统一验证**：
   - `cd pattern_knowledge_workbench && flutter pub get`；
   - `cd pattern_knowledge_workbench && flutter analyze --no-fatal-infos`；
   - `cd pattern_knowledge_workbench && flutter test`。

## 6. Forbidden

- 严禁引入任何第三方未批准 pub 依赖、临时 Mock 包或恢复内网 Git 地址；
- 严禁修改 `pattern_knowledge_workbench/lib/database/` 或 `assets/`；
- 严禁合并为一个提交；
- 严禁修改 `openspec/` 下已冻结的架构与 Schema 文件；
- 严禁修改 `docs/blackbox-spec-rework/verify-T.sh`。

## 7. Stop Conditions

- 若在 ACT 01 前全仓检索发现 `enumeration` 引用大于 0，立即停止；
- 若无法离线消除 `ai_core` 的引用或 `flutter analyze` 出现未预期的深层类型依赖，立即停止；
- 遇到任何阻断或歧义，严禁自行裁决，必须立即停手上报。

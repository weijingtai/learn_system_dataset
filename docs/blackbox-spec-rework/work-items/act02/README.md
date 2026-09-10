# ACT 02 消除「保存即 verified」执行工作包

状态：`READY`（ACT 01 已 ACCEPTED，测试与构建环境畅通；通过 ACT 审查）

## 1. Goal

消除 `pattern_knowledge_workbench` 中规则保存与 AI 识别产物保存时自动将 `isVerified` 置为 `true` 的严重设计缺陷。改为：
1. 人工保存时不再写 `isVerified`，保持原状态/默认 false；
2. AI 生成条件保存后，强制回落/保持为 `isVerified = false`（模型输出不可绕过人工审核直接成为正式核验数据）；
3. 保留列表中唯一的显式核验勾选通道作为合法置 true 的入口，确保符合黑箱架构规格 §2 原则 10 与 §14。

## 2. Authority and Background

- `PLAN.md` R0 第 2 条
- `docs/blackbox-spec-rework/act/02.yaml`
- `openspec/learn-system-blackbox-architecture.md` §2 原则 10、§14
- 前置依赖：`workbench-r0-dep-unlock` 已 `ACCEPTED`，`workbench-r0/01` 已 `ACCEPTED`

## 3. Scope

- WRITE:
  - `pattern_knowledge_workbench/lib/pages/rule_list_page.dart`
  - `pattern_knowledge_workbench/test/verified_gate_test.dart`（新建测试）
- READ:
  - `pattern_knowledge_workbench/lib/database/tables.dart`（确认第 61 行 isVerified 默认即为 false）
  - `pattern_knowledge_workbench/lib/pages/rule_list_page.dart`（当前保存点与显式勾选通道）
  - `pattern_knowledge_workbench/GAP_ANALYSIS.md`
  - `openspec/learn-system-blackbox-architecture.md` §2 原则 10

## 4. Implementation Strategy

1. **位置 1（人工编辑保存，当前约 1178 行）**：
   删除 `isVerified: const Value(true),`。其余字段与 `updatedAt` 保持不变。
2. **位置 2（AI 条件保存，当前约 1778 行）**：
   把 `isVerified: const Value(true),` 改为 `isVerified: const Value(false),`。即使该规则此前已被核验过，经 AI 修改后也必须显式降级为未核验。
3. **保留显式勾选通道（当前约 1362/1366 行）**：
   保留 `GeJuRulesCompanion(isVerified: Value(v))` 显式切换通道，不得改动。

## 5. Forbidden

- 严禁改动 `tables.dart` 或任何 drift 表定义（列默认值已正确）；
- 严禁删除或破坏显式勾选通道；
- 严禁把 `isVerified` 改成 nullable 或引入新的枚举字段；
- 严禁顺手修改与 `isVerified` 无关的其他 UI 逻辑；
- 严禁修改 `pattern_knowledge_workbench/lib/database/` 或 `assets/`。

## 6. Stop Conditions

- 若在单元测试中无法构建 UI 上下文或状态机验证异常；
- 遇到任何阻断或歧义，严禁自行裁决，必须停手汇报。

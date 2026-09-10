# ACT 01 消除「启动覆盖本地库」执行工作包

状态：`READY`（依赖解锁完成；通过 ACT 审查，等待执行）

## 1. Goal

消除 `pattern_knowledge_workbench` 每次启动时无条件从 `assets/ge_ju_database.sqlite` 覆盖用户本地 SQLite 数据库的高风险缺陷。改为「仅当目标数据库文件不存在时才播种」，已存在则原样使用，确保人工校订、审核决定与版本历史不会被静默销毁，符合黑箱架构规格 §20 第 2 条与第 3 条。

## 2. Authority and Background

- `PLAN.md` R0 第 1 条
- `docs/blackbox-spec-rework/act/01.yaml`
- `openspec/learn-system-blackbox-architecture.md` §20 第 2、3 条
- 前置依赖：`workbench-r0-dep-unlock` 已 `ACCEPTED`（构建与测试环境已恢复）

## 3. Scope

- WRITE:
  - `pattern_knowledge_workbench/lib/database/drift_database.dart`
  - `pattern_knowledge_workbench/test/database_persistence_test.dart`（新建测试）
- READ:
  - `pattern_knowledge_workbench/lib/database/tables.dart`
  - `pattern_knowledge_workbench/lib/database/drift_database.dart`
  - `pattern_knowledge_workbench/GAP_ANALYSIS.md`
  - `openspec/learn-system-blackbox-architecture.md` §20

## 4. Implementation Details

在 `pattern_knowledge_workbench/lib/database/drift_database.dart` 的 `databaseDirectory` 回调中：
```dart
databaseDirectory: () async {
  final docsDir = await getApplicationDocumentsDirectory();
  final dbFile = File(p.join(docsDir.path, 'ge_ju_database.sqlite'));
  if (!await dbFile.exists()) {
    final data = await rootBundle.load('assets/ge_ju_database.sqlite');
    await dbFile.writeAsBytes(data.buffer.asUint8List());
  }
  return docsDir;
}
```

## 5. Forbidden

- 严禁删除或改写 migration / schemaVersion（值为 3）与 onUpgrade 内的任何 SQL；
- 严禁改动 `assets/ge_ju_database.sqlite` 文件本身；
- 严禁把播种逻辑挪到 main.dart 或 provider 里绕过本文件；
- 严禁修改 `pattern_knowledge_workbench/assets/` 或 `lib/pages/`。

## 6. Stop Conditions

- 若在实现或测试过程中遇到 drift 框架未定义的行为或无法在单元测试中模拟文件持久性；
- 遇到任何歧义或阻断，严禁自行裁决，必须停手汇报。

# T-08 验收报告（G3 R2 返工）

## 1. 基本信息

- 任务 ID：`blackbox-t08-tag-interfaces-fields`
- 状态：`IMPLEMENTED_AWAITING_REVIEW`（等待主 Agent 独立验收，未自行宣布通过）
- 关联规格：`openspec/learn-system-blackbox-architecture.md` §1、§16.3（只读，未修改）
- 关联缺陷台账：`docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md` T-08 节
- 提交：`fix: enforce T-08 ownership mappings`（hash 见最终执行报告）

## 2. 变更文件

- `docs/blackbox-spec-rework/verify-T.sh`（T-08 段改为精确归属与供给包校验）
- `docs/blackbox-spec-rework/work-items/t08/{README.md,BDD.md,TDD.md,ACT.yaml,PROMPT.md,ACCEPTANCE.md}`

规格正文未改动。

## 3. 检查清单

- [x] 仅修改授权文件，未触碰业务代码、JSON Schema、测试、数据库或并发中的注解系统文件
- [x] §1 与 §16.3 均清晰承接 Tag 三个接口，且供给子包在 §1 与 §16.3.1 两处同时精确正确
- [x] 概念字典明确声明「不含规则 DSL」
- [x] Tag 侧 G4 显式命名空间化为 `TAG_SYSTEM_DESIGN.md §12.2`
- [x] §16.3.2 表格五字段各恰好一次，生产 Module 与归属子包逐字段精确相等
- [x] 生产 Module 列不含 M5；M5 只校验口径在 README/BDD/TDD/ACT/Prompt 五处一致
- [x] 六件套已删除 M4/M5 共同生产、旧 7→5 FAIL 与旧提交指令
- [x] 独立提交完成
- [ ] 主 Agent 独立验收（未完成）

## 4. Red baseline（加固前，证明假绿）

```text
t08-1   exit=0   T-08 把 concept_id 改为 M2 / SourceAssetPack
t08-2   exit=0   T-08 只改错误 Module（omen_carrying M4→M2，Package 不变）
t08-3   exit=0   T-08 只改错误 Package（school_variance_display KnowledgeDataPack→RuleIndexPack，Module 不变）
t08-4   exit=0   T-08 将 EvidenceBundle 接口改为错误供给包
```

## 5. Green 证据（加固后，正常规格）

```text
退出码: 0
PASS  T-08s Tag interface present in §1 and §16.3: 最小盘面概念字典
PASS  T-08s Tag interface present in §1 and §16.3: MarkContentBinding
PASS  T-08s Tag interface present in §1 and §16.3: EvidenceBundle
PASS  T-08s concept dictionary preserves rule DSL restriction
PASS  T-08s interface supply package: 最小盘面概念字典 -> KnowledgeDataPack
PASS  T-08s interface supply package: MarkContentBinding -> KnowledgeDataPack与RuleIndexPack
PASS  T-08s interface supply package: EvidenceBundle -> EvidenceMapPack
PASS  T-08s Tag G4 namespaced to TAG_SYSTEM_DESIGN.md §12.2
PASS  T-08s §16.3 table 5 fields with exact producer ownership and no M5 producer
FAIL 合计: 0
```

## 6. 负向变异证据（加固后）

```text
=== t08-1 ===
FAIL  T-08s §16.3 table issue: concept_id实际[M2/SourceAssetPack|KnowledgeDataPack]，期望[M4|KnowledgeDataPack];
FAIL 合计: 1

=== t08-2 ===
FAIL  T-08s §16.3 table issue: omen_carrying实际[M2|KnowledgeDataPack]，期望[M4|KnowledgeDataPack];
FAIL 合计: 1

=== t08-3 ===
FAIL  T-08s §16.3 table issue: school_variance_display实际[M4/M6|RuleIndexPack]，期望[M4/M6|KnowledgeDataPack];
FAIL 合计: 1

=== t08-4 ===
FAIL  T-08s interface supply package mismatch: EvidenceBundle (期望 EvidenceMapPack)
FAIL 合计: 1
```

| 变异 | 加固前退出码 | 加固后退出码 |
|---|---|---|
| t08-1 concept_id → M2 / SourceAssetPack | 0（假绿） | 1 |
| t08-2 只改错误 Module | 0（假绿） | 1 |
| t08-3 只改错误 Package | 0（假绿） | 1 |
| t08-4 接口改为错误供给包 | 0（假绿） | 1 |

每次变异只触发 1 条 FAIL，无连带误报。

## 7. 恢复验证

恢复权威规格后重新运行门禁，退出码 0、`FAIL 合计: 0`；`git diff --check` 退出 0。

等待主 Agent 独立验收；未启动 G4。

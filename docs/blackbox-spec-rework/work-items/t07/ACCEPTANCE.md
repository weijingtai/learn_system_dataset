# T-07 验收报告（G3 R2 返工）

## 1. 基本信息

- 任务 ID：`blackbox-t07-knowledgepack-mapping`
- 状态：`REWORK_REQUIRED_R3`（指定变异已修；等价否定措辞仍可假绿）
- 关联规格：`openspec/learn-system-blackbox-architecture.md` §16.2（只读，未修改）
- 关联缺陷台账：`docs/blackbox-spec-rework/reviews/G3-REVIEW-R2.md` T-07 节
- 提交：`fix: enforce T-07 exact package mappings`（hash 见最终执行报告）

## 2. 变更文件

- `docs/blackbox-spec-rework/verify-T.sh`（T-07 段改为精确归属校验）
- `docs/blackbox-spec-rework/work-items/t07/{README.md,BDD.md,TDD.md,ACT.yaml,PROMPT.md,ACCEPTANCE.md}`

规格正文未改动。

## 3. 检查清单

- [x] 仅修改授权文件，未触碰业务代码、Schema、测试、数据库或并发中的注解系统文件
- [x] §16.2 含全部 15 个早期目录条目，数据行总数严格为 15，每项各出现且仅出现一次
- [x] `query-contract` 规范化后精确等于 `QueryContractPack（查询契约与接口定义）`，不得附加任何第二个子包
- [x] `optional-vector-index` 规范化后精确等于 `本期不产出（依据§21非目标）`
- [x] 取代声明为同行肯定语义（`PublicationPackage` / `KnowledgeDataPack` / `正式取代` / `KnowledgePack`），否定式被拒
- [x] 六件套已删除旧双 IndexPack 映射、旧 8→7 FAIL 口径与禁止修改门禁指令
- [x] 独立提交完成
- [ ] 主 Agent 独立验收（未完成）

## 4. Red baseline（加固前，证明假绿）

```text
t07-1   exit=0   T-07 给 query-contract 追加 EvidenceMapPack
t07-2   exit=0   T-07 给 optional-vector-index 追加「同时归入 SearchIndexPack」
t07-3   exit=0   T-07 把「正式取代」改成「不得取代」
```

## 5. Green 证据（加固后，正常规格）

```text
退出码: 0
PASS  T-07s §16.2 映射表15项唯一且query-contract正确归属QueryContractPack
PASS  T-07s §16.2 affirmative replacement statement with PublicationPackage and KnowledgeDataPack
FAIL 合计: 0
```

## 6. 负向变异证据（加固后）

```text
=== t07-1 ===
FAIL  T-07s §16.2 映射表不合规: query-contract归属[QueryContractPack（查询契约与接口定义）EvidenceMapPack]，期望[QueryContractPack（查询契约与接口定义）];
FAIL 合计: 1

=== t07-2 ===
FAIL  T-07s §16.2 映射表不合规: optional-vector-index归属[本期不产出（依据§21非目标）同时归入SearchIndexPack]，期望[本期不产出（依据§21非目标）];
FAIL 合计: 1

=== t07-3 ===
FAIL  T-07s §16.2 replacement statement missing or negated
FAIL 合计: 1
```

| 变异 | 加固前退出码 | 加固后退出码 |
|---|---|---|
| t07-1 query-contract 追加 EvidenceMapPack | 0（假绿） | 1 |
| t07-2 optional-vector-index 追加 SearchIndexPack | 0（假绿） | 1 |
| t07-3 正式取代 → 不得取代 | 0（假绿） | 1 |

每次变异只触发 1 条 FAIL，无连带误报。

## 7. 恢复验证

恢复权威规格后重新运行门禁，退出码 0、`FAIL 合计: 0`；`git diff --check` 退出 0。

R3 主 Agent 独立验收不通过：“并未正式取代”“不应正式取代”等等价否定仍可假绿。返工见 `../../reviews/G3-REVIEW-R3.md`；未启动 G4。

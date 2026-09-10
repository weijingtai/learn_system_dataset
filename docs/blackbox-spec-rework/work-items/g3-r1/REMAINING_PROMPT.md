# G3 R1 剩余返工接力 Prompt

你接手的是已经执行到 4/7 的 G3 R1 返工。不要重做 T-04、T-06、T-11、T-13；它们已经由主 Agent 独立验收通过。

工作区：`/Users/jingtaiwei/Git/Public/learn_system`

开始时依次完整阅读：

1. `AGENTS.md`
2. `HANDOFF.md`
3. `PLAN.md`
4. `docs/blackbox-spec-rework/work-items/g3-r1/README.md`
5. 同目录 `BDD.md`、`TDD.md`、`ACT.yaml`、`ACCEPTANCE.md`
6. `docs/blackbox-spec-rework/reviews/G3-REVIEW-R1.md`
7. `docs/blackbox-spec-rework/D-design.md` 的 D-07
8. T-07/T-08 各自六件套与权威来源

只执行剩余严格串行链：

```text
05 D-07 → 主 Agent 验收 → 06 T-07 → 主 Agent 验收 → 07 T-08 → 主 Agent 总验收
```

## 05 D-07

先创建 `docs/blackbox-spec-rework/work-items/d07/` 六件套并自审到 READY，再实现规格：

- `TechniqueProfilePack`：FactSet Profile、事实字段及枚举、operator 集合、规则 AST schema version。
- `QueryContractPack`：`getEntry`、`getSourceSpan`、`searchKnowledge`、`matchFacts` 和兼容声明。
- RuleIndexPack 每条规则声明 Profile version。
- 规则只允许结构化 AST/YAML/JSON，禁止可执行 Python。
- M5 只验证 FactSet 可执行性，不生产 Tag 字段。

必须先添加语义门禁并证明旧规格为红；删除任一接口、FactSet、AST version 或 Profile version 时必须失败。D-07 未被主 Agent 标记 ACCEPTED 时，不得开始 T-07。

## 06 T-07

只修 §16.2：15 个 KnowledgePack 目录各且仅出现一次；`query-contract` 只能归属 `QueryContractPack`，不得归入 IndexPack；保留 optional-vector-index 非目标和取代声明。解析表格做门禁，禁止全文关键词计数。

## 07 T-08

只修 §1/§16.3：逐行校验三个接口、五字段、生产 Module 与目标 Package。M5 不得出现在生产 Module 列，只能单列 Validator 职责。Tag 侧 G4 必须写作 `TAG_SYSTEM_DESIGN.md §12.2` 的 G4，不能与本规格 G4 内容分层门禁混同；保留“不含规则 DSL”。

## 通用铁律

- 每项先红后绿，并至少做一个临时副本负向变异。
- 每项独立提交，只改 ACT 白名单。
- 不修改业务代码、数据库、Schema、fixture、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`。
- 不回退其他 Agent 的并发改动。
- 每项完成后返回提交哈希、文件范围、Red/Green/mutation 原始摘要，等待主 Agent 验收。
- 全量 `verify-T.sh=0` 只是必要条件，不是充分条件。


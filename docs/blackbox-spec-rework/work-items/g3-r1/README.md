# G3 R1 返工工作包

状态：`READY`

## 目标

消除 `reviews/G3-REVIEW-R1.md` 发现的六项语义缺陷，并补齐 T-07/T-08 的前置 D-07。最终只有在语义门禁与负向变异均有效时，才允许把 G3 标记为完成。

## 串行顺序

```text
01 T-04 → 02 T-06 → 03 T-11 → 04 T-13 → 05 D-07 → 06 T-07 → 07 T-08 → 主 Agent 终验
```

所有任务会修改同一份规格或同一验收脚本，禁止并行。每项单独提交。

## 权威来源

- `docs/blackbox-spec-rework/reviews/G3-REVIEW-R1.md`
- `docs/blackbox-spec-rework/T-transcribe.md`
- `docs/blackbox-spec-rework/D-design.md`
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md`
- `LEARN_SYSTEM_TARGET.md`
- `tag_system/TAG_SYSTEM_DESIGN.md`

## 写入范围

- `openspec/learn-system-blackbox-architecture.md`
- 当前返工项自己的 `docs/blackbox-spec-rework/work-items/<task>/TDD.md`、`ACT.yaml`、`ACCEPTANCE.md`
- `docs/blackbox-spec-rework/verify-T.sh`

执行 Agent 不得修改 `PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`；这些由主 Agent 验收后更新。不得修改业务代码、Schema、数据库或 fixture。

## 共同准出条件

1. 先加固当前任务门禁，并证明未修规格时新门禁为红。
2. 再修改规格，并证明新门禁转绿。
3. 在临时副本中删除关键语义、交换顺序或恢复错误值，门禁必须重新变红。
4. `git diff --check` 与全量 `verify-T.sh` 通过。
5. 每项只提交本项授权文件，报告提交哈希和原始输出。


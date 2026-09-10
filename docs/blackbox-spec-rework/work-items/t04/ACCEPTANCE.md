# T-04 主 Agent 验收清单

状态：`ACCEPTED`（R1 返工，2026-09-10）

## 1. Scope and Commits

- [x] 提交只修改 `openspec/learn-system-blackbox-architecture.md`（提交 `968a65e`，+42, -1）
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未修改工作包文档、TODO.md、PLAN.md、HANDOFF.md 或 `verify-T.sh`
- [x] 提交消息严格为 `docs: connect consumption levels and G1-G7 gates`

## 2. G1–G7 Gates and Consumption Levels Verification

- [x] G1 至 G7 全部正确引入，全规格未自创新门禁代号
- [x] §13 M5 Validator 清单完整覆盖 G1 至 G6，且明确标注各自工位（G1–G5 在 M5，G6 在 M5+M8，G7 在 M8）
- [x] §16 M8 冻结项显式包含输入参数「消费级别（Consumption Level）」
- [x] 三级消费级别取值齐备（`INTERNAL_DEMO`, `DEV_SEARCH`, `PUBLIC_RELEASE`）
- [x] 包含「编译器必须显式接收目标级别，并以 fail-closed 方式拒绝不满足条件的数据」强声明
- [x] §16 包含三级准入状态门槛表，直接对接 G7

## 3. Evidence and Regression

- [x] `docs/blackbox-spec-rework/work-items/t04/TDD.md` 中的全部 Green checks 通过
- [x] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码由 13 严格降为 10
- [x] `T-04` 由 FAIL 转为 PASS
- [x] `T-04b` 由 FAIL 转为 PASS
- [x] `T-04c` 由 FAIL 转为 PASS
- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查通过
- [x] 主 Agent 质量审查通过
- [x] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`ACCEPTED`。G1–G7 强制语义已补齐；主 Agent 删除“风险簇全检”语义后门禁退出码为 1，全量规格门禁退出码为 0。

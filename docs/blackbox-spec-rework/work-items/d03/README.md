# D-03 StepRun 生命周期：追溯验收工作包

状态：`REVIEWING`

## Goal

按现行 Subagent 交付闸门，追溯验收提交 `b0022d4` 是否完整定义长时人工阶段、恢复、暂停、终态与重跑语义。该工作包只验收，不重新实现。

## Authority

- `docs/blackbox-spec-rework/D-design.md` 的 D-03
- `openspec/learn-system-blackbox-architecture.md` §5、§7.1、§8.2、§14、§17
- `openspec/subagent-delivery-gate.md`

## Scope

- READ：上述文件、`PLAN.md`、`HANDOFF.md`、提交 `b0022d4`
- WRITE：仅本工作包的 `ACCEPTANCE.md`、总监控表及交接文档
- BASELINE：提交只应改动 `PLAN.md`、`HANDOFF.md`、架构规格

## Forbidden

- 不改业务代码、Schema 或 OCR 实现。
- 不把 `resume_token` 解释为登录或鉴权。
- 不用轮询或读取“最新文件”代替不可变事件写回。
- 不因 deadline 自动失败、自动放行或丢弃人工队列。
- 不在验收中顺手修正文档；发现问题应记录返工项。

## Stop conditions

若真实提交越出三文件范围、状态迁移存在未定义分支、终态可被原地改写，或判据与规格互相矛盾，停止验收并标记 `BLOCKED`。


# Subagent 工作总监控表

状态：活动监控表
更新时间：2026-09-10
维护者：主 Agent；执行 Agent 不得自行勾选

## 勾选规则

- 大项只有在全部适用小项完成且主 Agent 独立验收后才能勾选。
- `BDD/TDD/ACT` 不适用时必须写明理由，不得空过。
- 任务状态使用：`BACKLOG / PREPARING / READY / DISPATCHED / REVIEWING / ACCEPTED / BLOCKED`。
- 标准工作包和验收规则见 `openspec/subagent-delivery-gate.md`。

## G0 工作包治理

- [x] G0：建立并启用 Subagent 准出制度（状态：`ACCEPTED`）
  - [x] 规定主 Agent 与执行 Agent 职责边界
  - [x] 规定标准工作包目录
  - [x] 规定 BDD、TDD、ACT、Prompt、Acceptance 六类文档
  - [x] 规定 READY 准出条件
  - [x] 规定执行后的两阶段审查
  - [x] 建立本监控表
  - [x] 用户复核书面规格（2026-09-09：确认）
  - [x] 将状态更新为 `ACCEPTED`

## G1 规格内核严格序列

- [x] D-01：拆分 `entity_id` 与 `artifact_revision_id`（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 需求与约束已确认
  - [x] 执行提交 `fdf1e07`
  - [x] 质量返工 `a30a709`、`fa2b220`
  - [x] 规格符合性审查通过
  - [x] 质量审查通过
  - [x] PLAN/HANDOFF 已同步

- [x] D-03：StepRun 生命周期状态机（状态：`ACCEPTED`）
  - [x] 执行提交 `b0022d4`
  - [x] 补制 BDD 验收场景
  - [x] 补制 TDD/机器判据
  - [x] 补制 ACT 范围对照
  - [x] 核对执行提交未越界
  - [x] 重跑全部判据
  - [x] 规格符合性审查
  - [x] 质量审查
  - [x] PLAN/HANDOFF 与证据归档
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] T-02：完整标识格式转录与新增前缀确认（状态：`ACCEPTED`）
  - [x] 权威照抄源已定位
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反判据（纯文档任务，无数据 fixture）
  - [x] ACT.yaml
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 四查判定 `READY`
  - [x] 用户确认新增对象 ID 前缀（2026-09-09）
  - [x] 用户已派发执行 Agent
  - [x] 执行 Agent 第一轮提交 `6e317cc` 与证据
  - [x] 修复 StagePackage 逻辑身份／物理 Revision 冲突（`376e78c`）
  - [x] 冻结 `<stage>` 为 `m1`–`m8` 闭集
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] D-02：冻结 L0 四个机器 Schema（状态：`ACCEPTED`）
  - [x] D-03 已 `ACCEPTED`
  - [x] T-02 已 `ACCEPTED`
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反 fixture 与 round-trip 门禁
  - [x] ACT 拆分及依赖顺序
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` R2 判定 `READY`
  - [x] 派发执行 Agent
  - [x] 执行 Agent 提交与证据（`08fe789` / `fa69901`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

## G2 R0 工作台数据安全 ACT

- [x] ACT-01：启动时不覆盖本地数据库（状态：`ACCEPTED`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`f7ffd2f` / `3d6cfd2`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`
- [x] ACT-02：保存与 AI 产物不再自动 verified（状态：`ACCEPTED`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`424dc9a` / `54c0497`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`
- [x] ACT-03：删除零引用 enumeration 依赖（状态：`ACCEPTED`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`ffda853`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] ACT-04：剥离 ai_core 聊天旁路（状态：`ACCEPTED`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`2e11932`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

## G3 其余 T 类转录任务

- [x] G3 R2 冷启动返工执行契约：`work-items/g3-r2/COLD_START_PROMPT.md`（含读集、写范围、顺序、10 个变异、停手条件和交付证据）

- [x] T-01：术语三层模型写入 M4（状态：`ACCEPTED`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`5b99fb1`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] T-03：状态枚举四表（状态：`ACCEPTED`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`f702e4d`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] T-04：三级消费级别与 G1–G7 门禁（状态：`ACCEPTED`；R1 返工验收 `b15c25d`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`968a65e`）
  - [x] R1 返工：补全 G1–G7 原规范语义并加固门禁
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] T-05：evidence_level 枚举（状态：`ACCEPTED`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`8720464`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] T-06：EvidenceMapPack 内容（状态：`ACCEPTED`；R1 返工 `3768064`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`1e52327`）
  - [x] R1 返工：恢复权威证据链顺序并加固门禁
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [ ] T-07：KnowledgePack 双向映射（状态：`REWORK_REQUIRED_R2`；唯一归属门禁假绿）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`4bda4a8`）
  - [x] 先完成 D-07，再按其冻结契约返工映射（`a62f225`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [ ] R2：精确校验唯一归属、非目标唯一语义与肯定取代声明
  - [ ] R2：同步 README/PROMPT/TDD/ACT/ACCEPTANCE
  - [ ] R2：主 Agent 复跑变异并标记 `ACCEPTED`

- [ ] T-08：Tag 三个接口承接（状态：`REWORK_REQUIRED_R2`；owner/package 门禁假绿）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`4e13439`）
  - [x] 先完成 D-07，再修正 M5/G4 接线并加固门禁（`045a0ab`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [ ] R2：精确校验五字段 owner/package 与三接口供给包
  - [ ] R2：同步 README/BDD/PROMPT/TDD/ACT/ACCEPTANCE
  - [ ] R2：主 Agent 复跑变异并标记 `ACCEPTED`

- [x] T-09：Orchestrator 查询契约（状态：`ACCEPTED`，提交 `d331ca4`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`d331ca4`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] T-10：异常页终态（状态：`ACCEPTED`，提交 `60ecad6`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`60ecad6`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] T-11：差距表事实修正（状态：`ACCEPTED`；R1 返工 `6f62189`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`4deb1ce`）
  - [x] R1 返工：更新路径、依赖与测试数量等现状事实
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] T-12：施工层级与拓扑（状态：`ACCEPTED`，提交 `5e83c64`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`5e83c64`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] T-13：章节状态标签（状态：`ACCEPTED`；R1 返工 `e3b1570`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`be2c6ce`）
  - [x] R1 返工：为 §16 建议语句增加局部“讨论候选”标签
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`


## G4 其余 D 类设计任务

- [x] D-04：Ledger 跨语言访问契约（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 已确认设计写入规格
  - [x] PLAN 已记录完成依据
  - [x] 既有交叉审查通过
  - [x] 无业务实现冒充规格完成

- [x] D-05：Pattern/Concept/KnowledgeEntry（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 已确认设计写入规格
  - [x] PLAN 已记录完成依据
  - [x] 既有交叉审查通过
  - [x] 无业务实现冒充规格完成

- [ ] D-06：Annotation 锚点迁移（状态：`BACKLOG`）
  - [ ] README/范围/依赖/禁止项
  - [ ] BDD 场景
  - [ ] TDD 正反用例与精确命令
  - [ ] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [ ] Executor Prompt
  - [ ] Acceptance 清单
  - [ ] `wjt-react` 判定 READY
  - [ ] 派发执行 Agent
  - [ ] 执行提交与原始证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

- [ ] D-07：TechniqueProfile 与 QueryContract（状态：`REWORK_REQUIRED_R2`；跨块关键词代偿）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据（`f6be483`）
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [ ] R2：按三个 Package 专属块解析，禁止跨块关键词代偿
  - [ ] R2：补齐事实字段/枚举与逐规则 Profile/AST 版本负向门禁
  - [ ] R2：主 Agent 复跑变异并标记 `ACCEPTED`

- [ ] D-08：SchoolView（状态：`BACKLOG`）
  - [ ] README/范围/依赖/禁止项
  - [ ] BDD 场景
  - [ ] TDD 正反用例与精确命令
  - [ ] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [ ] Executor Prompt
  - [ ] Acceptance 清单
  - [ ] `wjt-react` 判定 READY
  - [ ] 派发执行 Agent
  - [ ] 执行提交与原始证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

- [x] D-09：EditionPart Gate 口径（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 已确认设计写入规格
  - [x] PLAN 已记录完成依据
  - [x] 既有交叉审查通过
  - [x] 无业务实现冒充规格完成

- [ ] D-10：精确失效传播（状态：`BACKLOG`）
  - [ ] README/范围/依赖/禁止项
  - [ ] BDD 场景
  - [ ] TDD 正反用例与精确命令
  - [ ] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [ ] Executor Prompt
  - [ ] Acceptance 清单
  - [ ] `wjt-react` 判定 READY
  - [ ] 派发执行 Agent
  - [ ] 执行提交与原始证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

- [ ] D-11：StageCheckpoint（状态：`BACKLOG`）
  - [ ] README/范围/依赖/禁止项
  - [ ] BDD 场景
  - [ ] TDD 正反用例与精确命令
  - [ ] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [ ] Executor Prompt
  - [ ] Acceptance 清单
  - [ ] `wjt-react` 判定 READY
  - [ ] 派发执行 Agent
  - [ ] 执行提交与原始证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

- [x] D-12：跨阶段 Review Console（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 已确认设计写入规格
  - [x] PLAN 已记录完成依据
  - [x] 既有交叉审查通过
  - [x] 无业务实现冒充规格完成

- [ ] D-13：ReleaseRun 人工回路（状态：`BACKLOG`）
  - [ ] README/范围/依赖/禁止项
  - [ ] BDD 场景
  - [ ] TDD 正反用例与精确命令
  - [ ] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [ ] Executor Prompt
  - [ ] Acceptance 清单
  - [ ] `wjt-react` 判定 READY
  - [ ] 派发执行 Agent
  - [ ] 执行提交与原始证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

- [ ] D-14：实施分期与首纵切（状态：`BACKLOG`）
  - [ ] README/范围/依赖/禁止项
  - [ ] BDD 场景
  - [ ] TDD 正反用例与精确命令
  - [ ] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [ ] Executor Prompt
  - [ ] Acceptance 清单
  - [ ] `wjt-react` 判定 READY
  - [ ] 派发执行 Agent
  - [ ] 执行提交与原始证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

- [ ] D-15：最小可跑 fixture（状态：`BACKLOG`）
  - [ ] README/范围/依赖/禁止项
  - [ ] BDD 场景
  - [ ] TDD 正反用例与精确命令
  - [ ] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [ ] Executor Prompt
  - [ ] Acceptance 清单
  - [ ] `wjt-react` 判定 READY
  - [ ] 派发执行 Agent
  - [ ] 执行提交与原始证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

- [ ] D-16：PLAN 映射与唯一 owner（状态：`BACKLOG`）
  - [ ] README/范围/依赖/禁止项
  - [ ] BDD 场景
  - [ ] TDD 正反用例与精确命令
  - [ ] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [ ] Executor Prompt
  - [ ] Acceptance 清单
  - [ ] `wjt-react` 判定 READY
  - [ ] 派发执行 Agent
  - [ ] 执行提交与原始证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

- [x] D-17：旧存储处置（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 已确认设计写入规格
  - [x] PLAN 已记录完成依据
  - [x] 既有交叉审查通过
  - [x] 无业务实现冒充规格完成

- [ ] D-18：完成标准判据化（状态：`BACKLOG`）
  - [ ] README/范围/依赖/禁止项
  - [ ] BDD 场景
  - [ ] TDD 正反用例与精确命令
  - [ ] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [ ] Executor Prompt
  - [ ] Acceptance 清单
  - [ ] `wjt-react` 判定 READY
  - [ ] 派发执行 Agent
  - [ ] 执行提交与原始证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

- [x] D-19：版权与三层存储边界（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 已确认设计写入规格
  - [x] PLAN 已记录完成依据
  - [x] 既有交叉审查通过
  - [x] 无业务实现冒充规格完成


## G5 R1 总准出

- [ ] R1 架构规格达到下一阶段准出条件（状态：`BLOCKED`）
  - [ ] G1 规格内核全部 `ACCEPTED`
  - [ ] G2 R0 工作台数据安全全部 `ACCEPTED`
  - [ ] G3 T 类全部 `ACCEPTED`
  - [ ] G4 D 类全部 `ACCEPTED`
  - [ ] BDD 总验收包完整
  - [ ] TDD/机器门禁可执行
  - [ ] ACT 覆盖映射无遗漏
  - [ ] 所有 Executor Prompt 已归档
  - [ ] `verify-T.sh` 无假绿且全部应通过项 PASS
  - [ ] `openspec/acceptance/run_all.sh` 可运行并逐条报告
  - [ ] 最终规格符合性审查通过
  - [ ] 最终质量审查通过
  - [ ] PLAN/HANDOFF 已同步
  - [ ] 用户确认进入实现阶段


## G6 NC 注解社区线

任务定义源：`openspec/annotation-community/TASKS.md`；本表持有流转状态，两处不得并存第二套状态源。
需求与设计：`openspec/annotation-community/{PRD,DESIGN,PLANS}.md`；R1 审查登记：`openspec/annotation-community/REVIEW_R1.md`。
四份文档已通过 `bash openspec/annotation-community/verify.sh`（FAIL 0）；该脚本只证明文档一致性，不证明业务可用。

### 前置契约（可立即准备六件套）

- [ ] NC-001：客户端位置、宿主、端口装配、设备与后端清单、验证器选型（状态：`BACKLOG`）
- [ ] NC-002：非书籍模型、ID 前缀、状态机、限额、canonical 编码与 fixture（状态：`BACKLOG`；**须先取得用户对 Design §2.1 的 UGC ID 前缀确认，未确认前不得离开 `PREPARING`**）
- [ ] NC-003：公共 REST/OpenAPI/Swagger 契约与错误目录（状态：`BACKLOG`）
- [ ] NC-015：密钥恢复、设备授权与删除窗口协议（状态：`BACKLOG`；从零设计密码学协议，30–60 分钟 ACT 粒度不适用，须单独排期）
- [ ] NC-020a：消费端书籍契约核对清单（状态：`BACKLOG`）
- [ ] NC-025：生产 BlobGateway（公共 + 私有）（状态：`BACKLOG`；R1 新增，NC-008/017 的硬前置）

### 本地笔记与编辑器

- [ ] NC-004：Drift 修订与可靠保存（状态：`BACKLOG`）
- [ ] NC-005：Markdown 编辑预览、状态与撤销栈裁定（状态：`BACKLOG`）
- [ ] NC-006：Undo/Redo 与 IME/焦点（状态：`BACKLOG`）
- [ ] NC-007：历史、差异、恢复与冲突处理旅程（状态：`BACKLOG`）

### 图片与公开社区

- [ ] NC-008：本地图片与公共资源适配（状态：`BACKLOG`）
- [ ] NC-009：发布/更新/收回、权限事务与 ACL 全入口扫描（状态：`BACKLOG`）
- [ ] NC-010：笔记列表、公开详情与发布 UI（状态：`BACKLOG`）
- [ ] NC-011：两级评论/回复与编辑删除（状态：`BACKLOG`）
- [ ] NC-012：赞踩/收藏/分享/@/关系与举报（状态：`BACKLOG`）

### 通知

- [ ] NC-013：事务事件、投递、通知正文与补拉端点（状态：`BACKLOG`）
- [ ] NC-014：Notification 宿主适配、去重与导航（状态：`BACKLOG`）

### 私人同步、备份与删除

- [ ] NC-016：私人加密 mapper 与设备同步（状态：`BLOCKED`，等 NC-015）
- [ ] NC-017：生产密文网关与备份清单（状态：`BLOCKED`，等 NC-015/NC-025）
- [ ] NC-018：备份设置、进度与恢复（状态：`BLOCKED`，等 NC-015）
- [ ] NC-019：回收站、恢复、永久清理（状态：`BLOCKED`，等 NC-018；本地回收站子 ACT 可先准备）

### 书籍与真实 Tooltip

- [ ] NC-020b：上游书籍政策/Schema/D-06/样例冻结（状态：`BLOCKED`，等上游交付）
- [ ] NC-021：书籍上传、导入、激活与版本查询（状态：`BLOCKED`）
- [ ] NC-022：原书阅读、原句注解与锚点解析（状态：`BLOCKED`）
- [ ] NC-023：真实 Tooltip 原型与入口一致性（状态：`BLOCKED`）

### 总验收

- [ ] NC-024：跨模块真实验收与交接（状态：`BLOCKED`，等全部前置）
  - [ ] R-01～R-20 全部在 `SPEC/ANNOTATION_COMMUNITY_ACCEPTANCE.md` 有 commit/命令/证据三元组
  - [ ] 无障碍 A11Y-01～09 逐条给证据
  - [ ] E-BOOK/E-CRYPTO/E-WIRING/E-NOTIFIER/E-BLOB/E-DEDUP 六项外部依赖状态如实登记，未完成不隐藏
  - [ ] F-01～F-05 独立后续登记，不混入本期通过率

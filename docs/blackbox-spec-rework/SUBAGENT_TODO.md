# Subagent 工作总监控表

状态：活动监控表
更新时间：2026-09-09
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

- [ ] D-02：冻结 L0 四个机器 Schema（状态：`READY`；等待用户派发）
  - [x] D-03 已 `ACCEPTED`
  - [x] T-02 已 `ACCEPTED`
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反 fixture 与 round-trip 门禁
  - [x] ACT 拆分及依赖顺序
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` R2 判定 `READY`
  - [ ] 派发执行 Agent
  - [ ] 执行 Agent 提交与证据
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`

## G2 R0 工作台数据安全 ACT

- [ ] ACT-01：启动时不覆盖本地数据库（状态：`BACKLOG`）
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

- [ ] ACT-02：保存与 AI 产物不再自动 verified（状态：`BACKLOG`）
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

- [ ] ACT-03：删除零引用 enumeration 依赖（状态：`BACKLOG`）
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

- [ ] ACT-04：剥离 ai_core 聊天旁路（状态：`BACKLOG`，依赖 ACT-03）
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


## G3 其余 T 类转录任务

- [ ] T-01：术语三层模型写入 M4（状态：`BACKLOG`）
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

- [ ] T-03：状态枚举四表（状态：`BACKLOG`）
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

- [ ] T-04：三级消费级别与 G1–G7 门禁（状态：`BACKLOG`）
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

- [ ] T-05：evidence_level 枚举（状态：`BACKLOG`）
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

- [ ] T-06：EvidenceMapPack 内容（状态：`BACKLOG`）
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

- [ ] T-07：KnowledgePack 双向映射（状态：`BACKLOG`）
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

- [ ] T-08：Tag 三个接口承接（状态：`BACKLOG`）
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

- [ ] T-09：Orchestrator 查询契约（状态：`BACKLOG`）
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

- [ ] T-10：异常页终态（状态：`BACKLOG`）
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

- [ ] T-11：差距表事实修正（状态：`BACKLOG`）
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

- [ ] T-12：施工层级与拓扑（状态：`BACKLOG`）
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

- [ ] T-13：章节状态标签（状态：`BACKLOG`）
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

- [ ] D-07：TechniqueProfile 与 QueryContract（状态：`BACKLOG`）
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

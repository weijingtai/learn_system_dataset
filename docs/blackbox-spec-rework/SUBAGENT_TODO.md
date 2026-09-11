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
- [x] G3 R3/R4：精确结构门禁与永久变异套件（`1d4a6dc` → `ffe19df`，98 例）；`work-items/g3-r3/` 六件套草稿为 89 例旧版，已标 `SUPERSEDED`，只保留 `mutations.sh` 为现行文件
- [x] G3 R5 区域边界封闭六件套：`work-items/g3-r5/`（状态 `ACCEPTED`；先红 `5de99fa` 11 例，后绿 `241c38c`；矩阵 109/109，selftest 41/41）
- [x] 主 Agent 独立验收：正常规格 0 FAIL、13 例矩阵外盲测全部命中指定 FAIL ID、FAIL ID 超集测试通过、只读 Agent 复跑一致；证据见 `work-items/g3-r5/ACCEPTANCE.md`
- [x] 用户 2026-09-10 决定启动 G4；第一批 `work-items/g4-r1/`（D-13/D-10/D-11 ｜ D-06/D-08 ｜ D-14）三组并行派发；D-15/D-16/D-18 第二批
- [x] G4 第二批 `work-items/g4-r2/`（2026-09-11 派发并验收，全部 `ACCEPTED`）：D 组 = ACT 01 前缀登记 `851fa70` + ACT 02 D-15 fixture `6fc8536`；E 组 = ACT 03 D-18 `4884b6a` + 返工 `2978ad9`；三件裁定（哈希环、严格 offset、规范 verify.sh）记于 `g4-r2/ACCEPTANCE.md` §5.1；G4 仅剩 D-16
- [x] G4 第三批 `work-items/g4-r3/`（2026-09-11 派发并验收）：D-16 `76bc4b4`、`pat_`/`ent_` 登记 `e306258`，均 `ACCEPTED`；G4 D 类 D-01～D-19 全部 `ACCEPTED`；r3-03 检查脚本兼容已勾选行 `aa85430` `ACCEPTED`；下一步 G5 总准出

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

- [x] T-07：KnowledgePack 双向映射（状态：`ACCEPTED`；R4 `ffe19df` 精确 15 行字典 + R5 `241c38c` 表格 17 行封闭，t07 28/28）
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
  - [x] R2：精确校验唯一归属、非目标唯一语义与指定肯定取代变异
  - [x] R2：同步 README/PROMPT/TDD/ACT/ACCEPTANCE
  - [x] R2：主 Agent 复跑 3 个指定变异（均被拦截；R3 发现等价绕过）
  - [x] R3/R4：改用完整肯定句精确匹配并覆盖等价否定变异（`1d4a6dc`、`ffe19df`）
  - [x] R5：拒绝行尾额外列与任意非规范表行，主 Agent 验收 `ACCEPTED`（`work-items/g3-r5/ACCEPTANCE.md`）

- [x] T-08：Tag 三个接口承接（状态：`ACCEPTED`；R4 `ffe19df` 精确接口行与包多重集 + R5 `241c38c` §16.3.1 序列相等与标题唯一，t08 47/47）
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
  - [x] R2：精确校验五字段 owner/package 与三接口指定供给包变异
  - [x] R2：同步 README/BDD/PROMPT/TDD/ACT/ACCEPTANCE
  - [x] R2：主 Agent 复跑 4 个指定变异（均被拦截；R3 发现唯一性绕过）
  - [x] R3/R4：精确接口名、唯一供给行、拒绝额外 Package 后复验（`1d4a6dc`、`ffe19df`）
  - [x] R5：拒绝重复块标题与块外内容，主 Agent 验收 `ACCEPTED`（`work-items/g3-r5/ACCEPTANCE.md`）

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

- [x] D-06：Annotation 锚点迁移（状态：`ACCEPTED`；`e474ae4`，`work-items/g4-r1/act/d06.yaml`，验收见 `work-items/g4-r1/ACCEPTANCE.md`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] D-07：TechniqueProfile 与 QueryContract（状态：`ACCEPTED`；R4 `ffe19df` 三个封闭块 + R5 `241c38c` 三段区域到下一 START 封闭，d07 34/34）
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
  - [x] R2：按三个 Package 专属块解析，禁止跨块关键词代偿
  - [x] R2：补齐事实字段/枚举与逐规则 Profile/AST 版本负向门禁
  - [x] R2：主 Agent 复跑 3 个指定变异（均被拦截；R3 发现语义绕过）
  - [x] R3/R4：精确 Package 起始行与肯定兼容声明后复验（`1d4a6dc`、`ffe19df`）
  - [x] R5：三段区域到下一 START/§16.2 完整封闭，主 Agent 验收 `ACCEPTED`（`work-items/g3-r5/ACCEPTANCE.md`）

- [x] D-08：SchoolView（状态：`ACCEPTED`；`07f79dd`，`work-items/g4-r1/act/d08.yaml`；`school_id`/`school_view_id` 前缀待用户确认后登记 §8.1）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] D-09：EditionPart Gate 口径（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 已确认设计写入规格
  - [x] PLAN 已记录完成依据
  - [x] 既有交叉审查通过
  - [x] 无业务实现冒充规格完成

- [x] D-10：精确失效传播（状态：`ACCEPTED`；`015e34f`，`work-items/g4-r1/act/d10.yaml`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] D-11：StageCheckpoint（状态：`ACCEPTED`；`3598ea8`，`work-items/g4-r1/act/d11.yaml`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] D-12：跨阶段 Review Console（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 已确认设计写入规格
  - [x] PLAN 已记录完成依据
  - [x] 既有交叉审查通过
  - [x] 无业务实现冒充规格完成

- [x] D-13：ReleaseRun 人工回路（状态：`ACCEPTED`；`4086c2c`，`work-items/g4-r1/act/d13.yaml`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] D-14：实施分期与首纵切（状态：`ACCEPTED`；`d36a202`，`work-items/g4-r1/act/d14.yaml`；§22 分期用户 2026-09-10 确认，状态已改「已确认设计」）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY
  - [x] 派发执行 Agent
  - [x] 执行提交与原始证据
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] D-15：最小可跑 fixture（状态：`ACCEPTED`，`6fc8536`，工作包 `work-items/g4-r2/` ACT 02；主 Agent 验收见 `g4-r2/ACCEPTANCE.md` §5.3，含 8 例矩阵外篡改；前缀登记 ACT 01 同时 `ACCEPTED`，`851fa70`；用户 2026-09-10 裁定：《三辰通载》派生页图不进 Git，fixture 只含转录文本与锚点，页图走本地 Object Store 引用，缺图报 `BLOCKED_SOURCE_ASSET_MISSING`）
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

- [x] D-16：PLAN 映射与唯一 owner（状态：`ACCEPTED`；`76bc4b4` 映射表 + `e306258` `pat_`/`ent_` 登记；验收见 `work-items/g4-r3/ACCEPTANCE.md` §5；PLAN 21 条 superseded-by 已由主 Agent 勾选；r3-03 检查脚本兼容已勾选行 `aa85430` `ACCEPTED`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY（2026-09-11）
  - [x] 派发执行 Agent（2026-09-11，用户交外部 Agent）
  - [x] 执行提交与原始证据
  - [x] 主 Agent 规格审查
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步
  - [x] 主 Agent 标记 `ACCEPTED`

- [x] D-17：旧存储处置（状态：`ACCEPTED`；旧流程豁免补制标准工作包）
  - [x] 已确认设计写入规格
  - [x] PLAN 已记录完成依据
  - [x] 既有交叉审查通过
  - [x] 无业务实现冒充规格完成

- [x] D-18：完成标准判据化（状态：`ACCEPTED`，`4884b6a` + 返工 `2978ad9`；`openspec/acceptance/run_all.sh` 当前 `pass=0 fail=1 blocked=10`，20.7 因 `original_text` 全空为 FAIL 属预期；主 Agent 验收见 `g4-r2/ACCEPTANCE.md` §5.4–5.5）
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

- [x] R1 架构规格达到下一阶段准出条件（状态：`ACCEPTED`；14/14 条满足，g5-01 `70c05cd` 已验收，规格文档级状态 `R1_REWORK_CLOSED`，记录 `reviews/G5-EXIT-REVIEW.md`；待用户确认进入实现阶段后派发 `work-items/g5/PROMPT-G.md` 翻转文档级状态）
  - [x] G1 规格内核全部 `ACCEPTED`
  - [x] G2 R0 工作台数据安全全部 `ACCEPTED`
  - [x] G3 T 类全部 `ACCEPTED`（T-01～T-13；D-07/T-07/T-08 假绿经 R5 关闭，2026-09-10）
  - [x] G4 D 类全部 `ACCEPTED`
  - [x] BDD 总验收包完整
  - [x] TDD/机器门禁可执行
  - [x] ACT 覆盖映射无遗漏
  - [x] 所有 Executor Prompt 已归档（D-01/04/05/09/12/17/19 旧流程豁免登记，判据实跑见 G5-EXIT-REVIEW §2）
  - [x] `verify-T.sh` 无假绿且全部应通过项 PASS
  - [x] `openspec/acceptance/run_all.sh` 可运行并逐条报告
  - [x] 最终规格符合性审查通过
  - [x] 最终质量审查通过
  - [x] PLAN/HANDOFF 已同步
  - [x] 用户确认进入实现阶段（2026-09-11「确认可以进入。」；g5-01 已派发，翻转 `REVIEW_FAILED_R1` → `R1_REWORK_CLOSED` 后大项记 `ACCEPTED`）


## G7 首纵切实现（Dataset 会话；§22 顺序 Artifact Ledger → M3 → M5 → M8）

- [ ] impl-01：Artifact Ledger §17（状态：`DISPATCHED`，H1 `ACCEPTED`、H2 派发中；工作包 `work-items/impl-01-ledger/`，六个 ACT 分 H1（00–02）/H2（03–05）两轮派发；完成判据 `openspec/acceptance/run_all.sh` 20.2/20.3 由 BLOCKED 变 PASS，`SUMMARY pass=2 fail=1 blocked=8`）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt（H1、H2）
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY（2026-09-11）
  - [x] 派发 H1 执行 Agent（2026-09-11）
  - [x] H1 执行提交与原始证据（ACT 00/01/02：`ba9b68e`、`823bead`、`0dff35d`）
  - [x] 主 Agent 验收 H1（`impl-01-ledger/ACCEPTANCE.md` §5.1；三点裁定：16 表、from_status/to_status、insert_stage_package）
  - [x] 派发 H2 执行 Agent（2026-09-11）
  - [ ] H2 执行提交与原始证据（ACT 03/04/05）
  - [ ] 主 Agent 规格审查
  - [ ] 主 Agent 质量审查
  - [ ] PLAN/HANDOFF 同步
  - [ ] 主 Agent 标记 `ACCEPTED`
- [ ] impl-02：M3 Corpus Compilation（状态：`BACKLOG`；impl-01 后）
- [ ] impl-03：M5 Automatic Validation（状态：`BACKLOG`）
- [ ] impl-04：M8 Dataset Compilation（状态：`BACKLOG`）

## G6 NC 注解社区线

任务定义源：`openspec/annotation-community/TASKS.md`；本表持有流转状态，两处不得并存第二套状态源。
需求与设计：`openspec/annotation-community/{PRD,DESIGN,PLANS}.md`；R1 审查登记：`openspec/annotation-community/REVIEW_R1.md`。
四份文档已通过 `bash openspec/annotation-community/verify.sh`（FAIL 0）；该脚本只证明文档一致性，不证明业务可用。

### 前置契约（可立即准备六件套）

- [ ] NC-001：客户端位置、宿主、端口装配、设备与后端清单、验证器选型（总项状态：`PREPARING`；子项 NC-001-01 状态：`ACCEPTED`）
  - [x] R1 审查（`reviews/NC-001-REVIEW-R1.md`）返工落实：14 个文件一次提交 `aadd1fc`，`nc001_r1_guard.sh` 为 0
  - [x] R2/R3/R4 三轮 wjt-react 四查（`reviews/NC-001-REVIEW-R2.md`）：6 + 3 项返工全部关闭，R4 判定 READY；`nc001_r2_guard.sh` 为 0
  - [x] 用户决定（2026-09-10 托管主 Agent 代为拍板）：CLIENT 用独立 Git 仓库（`client.vcs=NEW_GIT_REPOSITORY`）
  - [x] 派发 NC-001-01 执行 Agent：`work-items/nc-001/PROMPT.md`，act/01 → act/02 → act/03 → act/04 四个提交
  - [x] 主 Agent 验收 NC-001-01：执行提交 `272fb60`→`11b4e46`→`d75afb1`→`11edbc7`；32 测试、local/integrated 与契约一致、`nc001_r2_guard.sh --require-impl` 0、3 个必做变异 + 17 个盲测全部符合；记录见 `work-items/nc-001/ACCEPTANCE.md`
  - [ ] NC-001-02 完整联调取证（设备、后端、Emulator、真实测试）另行准备工作包；Firebase 去留须在此之前由用户决定
- [x] NC-002：非书籍模型、ID 前缀、状态机、限额、canonical 编码与 fixture（状态：`ACCEPTED`，2026-09-11；DEFERRED：CLIENT Dart 一致性测试 → NC-004、CommandRecord 按操作成对 Schema → NC-003）
  - [x] DESIGN §2.1 十七个 UGC ID 前缀：2026-09-10 用户全权托管主 Agent，前缀整表采用并冻结（community-models.md §0.1）；READINESS_REVIEW §3 同步登记，两处结论一致
  - [x] 规格侧产物（主 Agent）：`contracts/community-models.md`、`contracts/state-machines.md`、`tools/nchash_reference.py`、`fixtures/community/` 9 个文件 196 项
  - [x] 六件套 `work-items/nc-002/`（act/01～05）与守卫 `reviews/nc002_guard.sh`
  - [x] wjt-react 四查：R1 REWORK 20 项、R2 REWORK 9 项、R3 READY（`reviews/NC-002-REVIEW-R1.md`）；守卫 `nc002_guard.sh` 0
  - [x] 外部执行 Agent 完成 act/01～06：learn_system `0d27ea8`→`7ee2c45`，SERVER `30a868c`；主 Agent 验收通过（守卫 `--require-impl` 0、61 PASS、198 项、7+8 测试、9 盲测快照/反例、12 Schema 盲测、3 校验器变异），记录见 `work-items/nc-002/ACCEPTANCE.md`
  - [x] CLIENT Dart 一致性测试推迟至 NC-004 第一条 ACT（已写入 nc-004/act/01）
- [ ] NC-003：公共 REST/OpenAPI/Swagger 契约与错误目录（状态：`DRAFT`，2026-09-11 六件套完成，待 wjt-react 四查；用户指示按 Firebase 方向、与 functions-py 统一）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/community_api.md`（functions-py 现状盘点与沿用表、20 端点目录、头参数与 ETag、错误目录与 L0 映射、Schema 字段表、分页与限流实值、命令账本结果白名单、D-NC003-01～11）；验证器 `openapi-spec-validator 0.9.0` 已装入 `.venv-openapi`，既有 REST 契约验证失败（`'headers' was unexpected`）作为 Red 基线
  - [x] 六件套 `work-items/nc-003/`（act/01 验证器接入与 35 处迁移、act/02 组件与内容端点、act/03 评论/互动/分享/举报/命令端点、act/04 示例校验与版本号）与守卫 `reviews/nc003_guard.sh`
  - [ ] wjt-react 四查
  - [ ] 用户派发外部执行 Agent（`work-items/nc-003/PROMPT.md`，四个提交在 repository-rest-adapter 仓库）；主 Agent 按 ACCEPTANCE.md 验收
- [ ] NC-015：密钥恢复、设备授权与删除窗口协议（状态：`BACKLOG`；从零设计密码学协议，30–60 分钟 ACT 粒度不适用，须单独排期）
- [ ] NC-020a：消费端书籍契约核对清单（状态：`BACKLOG`）
- [ ] NC-025：生产 BlobGateway（公共 + 私有）（状态：`BACKLOG`；R1 新增，NC-008/017 的硬前置）
- [ ] NC-026：行为事件数据源、假名化与私人笔记元数据上报（状态：`BACKLOG`；v1.5 新增）

### 本地笔记与编辑器

- [x] NC-004：Drift 修订与可靠保存（状态：`ACCEPTED`，2026-09-11；reading-notes `9ac96cc`→`957536c`）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/local-persistence.md`（包基线、4 表、outbox 外层信封 D-NC004-01、仓储八条保存规则、nchash Dart、决定 D-NC004-01～07）
  - [x] 六件套 `work-items/nc-004/`（act/01～04：建仓+nchash 一致性、模型+Drift 库、保存规则、恢复/回滚/会话隔离）与守卫 `reviews/nc004_guard.sh`
  - [x] wjt-react 四查：R1 REWORK 10 项 + 7 建议、R2 READY（`reviews/NC-004-REVIEW-R1.md`）；守卫 `nc004_guard.sh` 0
  - [x] 外部执行 Agent 完成 act/01～05（reading-notes 五个提交）；主 Agent 验收通过（守卫 `--require-impl` 0、analyze 0、35 测试、5 快照交叉复算、sqlite3 直查、note_heads 失败注入回滚），记录见 `work-items/nc-004/ACCEPTANCE.md`
- [x] NC-005：Markdown 编辑预览、状态与撤销栈裁定（状态：`ACCEPTED`，2026-09-11；reading-notes `10ef174`→`8b05a68`）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/editor.md`（控制器接口与 SM-1 边、三态文案闭集与 400 ms、撤销栈归属方案 b、`flutter_markdown_plus 1.0.12` 接线事实、A11Y-04/05/07、D-NC005-01～05）
  - [x] 六件套 `work-items/nc-005/`（act/01～04）与守卫 `reviews/nc005_guard.sh`
  - [x] wjt-react 四查：R1 REWORK 3 项 + 3 建议、R2 READY（`reviews/NC-005-REVIEW-R1.md`）；守卫 `nc005_guard.sh` 0
  - [x] 外部执行 Agent 完成 act/01～04（四个提交）；主 Agent 验收通过（守卫 `--require-impl` 0、analyze 0、75 测试、去抖/400 ms 边界、大写 scheme 零联网、PRD §6.1 文案双向差集为空），一处越界改名（守卫误判起因）裁定接受，记录见 `work-items/nc-005/ACCEPTANCE.md`
- [x] NC-006：Undo/Redo 与 IME/焦点（状态：`ACCEPTED`，2026-09-11；reading-notes `afbe3a0`→`00f6fc9`，act/01～04，113 测试）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/editor_history.md`（Flutter 3.44.6 平台事实：平台栈不可关闭、`Action.overridable` 覆盖、默认键表无 Ctrl+Y；adapter 接口、diff 分类与三条归组规则、IME 单元、页面接线、D-NC006-01～12）；`editor.md` §4 加指针
  - [x] 六件套 `work-items/nc-006/`（act/01 adapter、act/02 与控制器/自动保存交互、act/03 页面按键/按钮/焦点）与守卫 `reviews/nc006_guard.sh`；`nc005_guard.sh` 的 Shortcuts 扫描在 adapter 落地后自动跳过（D-NC006-12）
  - [x] wjt-react 四查：R1 返工 1 项（act/03 校验命令 `&&` 链退出码误判）+ 2 建议，主 Agent 落实后 READY（`reviews/NC-006-REVIEW-R1.md`）；守卫 `nc006_guard.sh` 0
  - [x] 外部执行 Agent 完成 act/01～03（三个提交）；主 Agent 验收：守卫 0、110 测试、六组盲测通过，⑦ 页面层 IME 组合缺口与 ⑤ 组合中撤销裁定为 D-NC006-13/14（`work-items/nc-006/ACCEPTANCE.md`）
  - [x] act/04 返工（页面 `composing` 接线 + adapter 组合中 no-op，3 测试，`+113`）：`00f6fc9`；主 Agent 复跑盲测 ⑦/⑤ 通过，守卫 `--require-impl` 0，NC-006 关闭（ACCEPTANCE.md R2）
- [x] NC-007：历史、差异、恢复与冲突处理旅程（状态：`ACCEPTED`，2026-09-11 R2；reading-notes `29f6065`→`9b35e97`，act/01～06，150 测试）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/revision_history.md`（纯本地长文差异、连续 3 行折叠、跳转导航、恢复旧版新建带 restored_from 修订、PRD 旅程 6 四选项闭集与非阻断横幅、D-NC007-01～05）
  - [x] 六件套 `work-items/nc-007/`（act/01 差异与折叠、act/02 历史列表与恢复、act/03 冲突控制器、act/04 横幅与手动合并工作区）与守卫 `reviews/nc007_guard.sh`
  - [x] 审查与门禁：守卫 `nc007_guard.sh` 0，BDD B01～B32 齐全，全量测试目标 +145
  - [x] 执行 Agent 完成 act/01～04（reading-notes 四个原子提交：`29f6065`、`033392d`、`5e970f8`、`8a910a2`）
  - [x] 形式门禁：`nc007_guard.sh --require-impl` 0、analyze 0、145 测试、零外部网络/零新依赖、保护文件未触碰
  - [x] 主 Agent 盲测：随机重组/折叠边界/真实 Drift 恢复与合并通过；① 20k 行改两处 → 变更行 39 962（D-NC007-06）；④ 合并工作区自动保存 → 真实库 `HeadConflictError`（D-NC007-07）；记录见 `work-items/nc-007/ACCEPTANCE.md` R1
  - [x] act/05（差异锚定递归，3 测试）与 act/06（合并工作区不自动保存，2 测试，全量 `+150`）：`5cdd344`、`9b35e97`；主 Agent 复跑盲测 ①④⑤ 通过（20k 行两处变更行 4、1 MiB 39 ms、跨阈值随机重组、工作区无自动保存、真实库合并），守卫 `--require-impl` 0，NC-007 关闭（ACCEPTANCE.md R2）

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
- [ ] NC-017：生产密文网关与备份清单（状态：`BLOCKED`，等 NC-015/NC-025/NC-009 命令恢复服务）
- [ ] NC-018：备份设置、进度与恢复（状态：`BLOCKED`，等 NC-015）
- [ ] NC-019：回收站、恢复、永久清理（状态：`BLOCKED`，等 NC-018；本地回收站子 ACT 可先准备）

### 书籍与真实 Tooltip

- [ ] NC-020b：上游书籍政策/Schema/D-06/样例冻结（状态：`BLOCKED`，等上游交付）
- [ ] NC-021：书籍上传、导入、激活与版本查询（状态：`BLOCKED`）
- [ ] NC-022：原书阅读、原句注解与锚点解析（状态：`BLOCKED`）
- [ ] NC-023：真实 Tooltip 原型与入口一致性（状态：`BLOCKED`）

### 总验收

- [ ] NC-024：跨模块真实验收与交接（状态：`BLOCKED`，等全部前置）
  - [ ] R-01～R-21 全部在 `SPEC/ANNOTATION_COMMUNITY_ACCEPTANCE.md` 有 commit/命令/证据三元组
  - [ ] 无障碍 A11Y-01～09 逐条给证据
  - [ ] E-BOOK/E-CRYPTO/E-WIRING/E-NOTIFIER/E-BLOB/E-DEDUP 六项外部依赖状态如实登记，未完成不隐藏
  - [ ] F-01～F-05 独立后续登记，不混入本期通过率

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

- [x] impl-01：Artifact Ledger §17（状态：`ACCEPTED` 2026-09-11；H1 `ba9b68e`/`823bead`/`0dff35d`，H2 `401b449`/`01d32ca`/`45d99a1`，返工 `c939575`；`run_all.sh` 20.2/20.3 PASS，`SUMMARY pass=2 fail=1 blocked=8`；验收 `work-items/impl-01-ledger/ACCEPTANCE.md` §5）
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
  - [x] H2 执行提交与原始证据（ACT 03/04/05：`401b449`、`01d32ca`、`45d99a1`）
  - [x] 主 Agent 规格审查（`impl-01-ledger/ACCEPTANCE.md` §5.2：签名 22/22、`run_all.sh` pass=2、8 例矩阵外篡改命中）
  - [x] 返工 ACT 06：宿主准备失败必须退出码 1（`c939575`）
  - [x] 主 Agent 质量审查
  - [x] PLAN/HANDOFF 同步（PLAN 节 C 勾选推迟到 impl-02 ACT 00 修 check_d16 R5 之后）
  - [x] 主 Agent 标记 `ACCEPTED`
- [x] impl-02：M3 Corpus Compilation 结构层（状态：`ACCEPTED` 2026-09-12；J1 `1bf6687`/`0911d14`/`00dfa9f`；J2 `f4f4682`/`ea9126d`；J3 返工 `c5f744c`；执行方提交 `ad20ed6` 自记 ACCEPTED 属越权，已更正；非阻断跟进 ACT 06 已派发；语义层未做，`m3-coverage.sh` exit 2；验收 `work-items/impl-02-corpus/ACCEPTANCE.md` §5.3）
  - [x] README/范围/依赖/禁止项
  - [x] BDD 场景
  - [x] TDD 正反用例与精确命令
  - [x] ACT.yaml（含 SCOPE、ON_FAIL、VERIFICATION）
  - [x] Executor Prompt（J1、J2）
  - [x] Acceptance 清单
  - [x] `wjt-react` 判定 READY（2026-09-11）
  - [x] 派发 J1 执行 Agent（2026-09-11，主 Agent 启动 Sonnet 子 Agent，用户指示）
  - [x] J1 执行提交与原始证据（ACT 00/01/02：`1bf6687`、`0911d14`、`00dfa9f`）
  - [x] 主 Agent 验收 J1（`impl-02-corpus/ACCEPTANCE.md` §5.1；12 例矩阵外篡改命中；PLAN 节 C「Artifact Ledger」已勾选附 `c939575`）
  - [x] 派发 J2 执行 Agent（2026-09-11，用户交外部 Agent；主 Agent 另派的 Sonnet 发现并发写入后按停手规则退出，未写文件）
  - [x] J2 执行提交与原始证据（ACT 03/04：`f4f4682`、`ea9126d`）
  - [x] 主 Agent 规格审查（`ACCEPTANCE.md` §5.2：5 处缺陷）
  - [x] 返工 ACT 05：冻结输入完整性、终态严格比对、begin 后异常封存、缺 fixture 退出码 3（`c5f744c`；tmux agy 额度耗尽零产出后改派 Sonnet 子 Agent）
  - [x] 主 Agent 质量审查（`ACCEPTANCE.md` §5.3：28 项矩阵外检查、测试断言审查、4 处取舍裁定、下游约束登记）
  - [x] PLAN/HANDOFF 同步（HANDOFF 已更新；语义层未做、`m3-coverage.sh` exit 2，PLAN 不勾选 M3）
  - [x] 主 Agent 标记 `ACCEPTED`
  - [x] 跟进 ACT 06：缺 PyYAML → exit 3；失败用例直查 Ledger 无 m3 包（`eee3c35`，`ACCEPTANCE.md` §5.4 `ACCEPTED`）
- 分波计划：`docs/blackbox-spec-rework/G7-PLAN.md`（W2 起执行器 tmux + `cmd --yolo` DeepSeek V4.1 Flash，审查用 GLM 5.3 Flash，同时最多 2～3 路）；裁决 `G7-RULINGS.md`（P1–P9、§9、§9.1、§9.2）；对账审查 `reviews/G7-DRAFTS-REVIEW-R1.md`/`R2.md`。
- [x] impl-00：跨模块接口总表（状态：首纵切部分 `ACCEPTED`——act/10 INTERFACES §4 闭集登记 `ea90ca8`，检查器 18 项；其余 ACT `DEFERRED` 纵切后；验收 `impl-00-interfaces/ACCEPTANCE.md` §5.1）；W4G 组：act/12（M4 闭集登记）`b8db05d` 主 Agent 验收通过（ACCEPTANCE §5.2，24 PASS）；act/05（m4 金标，合成人工事件）`7d805e6` 主 Agent 验收通过（ACCEPTANCE §5.3，verify.sh 11 PASS）；起草与审查 `6cd4379`/`3f32700`/`a42259f`、R1 `b401c61` → R2 READY `b7c3788`；W5H：act/13（M6 闭集登记）`573c3fb` 主 Agent 验收通过（ACCEPTANCE §5.4，29 PASS，三例篡改命中），起草 `950349b`/`af17496` → R2 READY `6f2d41e`；W7-7.1：act/14（M2 电子文本四类产物、`ss_` 偏移形态、`sem_` 前缀登记）`ec8c3a8` 主 Agent 验收通过（ACCEPTANCE §5.5，36 PASS，五组篡改命中；起草 `b90e3de` → 改正 `6e19b9b` → 执行 `c6bcd9f` → 返工 `ec8c3a8`）
- [x] impl-03：M5 Automatic Validation 首切片（状态：`ACCEPTED` 2026-09-12；定稿 `1a189ae`，四查 R1 REWORK → 返工 `06d7d08`/`881538d` → R2 READY `6b548c6`；K1 `25b2fcc`/`48ebbfb`/`1fab5b1`/`0a77975`；K2 `817cd64`/`9aaccf5`/`6e21038`；返工 `8367893`；`m5-evidence-gate.sh` 9 PASS + 5 BLOCKED exit 2；验收 `impl-03-validation/ACCEPTANCE.md` §5.1）
- [x] impl-04：M8 Dataset Compilation 首切片（状态：`ACCEPTED` 2026-09-12；定稿 `2e4f9a7`，四查 R1 READY `7f809ea`，整改 `8758a00`/`8554ced`；K1 `a64d0e9`/`000386e`/`4a79ef5`；K2 `7dcf032`/`5a54d42`/`f85471e`/`338c157`；K3 `c36d628`/`950b77b`；裁定 32/44；`m8-span-identity.sh` 7 PASS + 1 BLOCKED exit 2；验收 `impl-04-dataset/ACCEPTANCE.md` §5.1）——首纵切关键路径 Ledger→M3→M5→M8 跑通
- [x] impl-08：Local Orchestrator + Contract Registry 首切片（状态：`ACCEPTED` 2026-09-12；定稿 `cd6c7a6` → R1 REWORK `5ab873c` → 返工 `559a359` → R2 READY `d49094b`；K1 `8aa2ad6`/`772b44b`、K2 `8fb9189`/`0b2a947`/`74c4cbf`、K3 `1658a82`/`c72c90e`、K4 `59d5d73`/`8ca41e9`/`640ab4c`/`a8494a3`/`f79eafd`；裁定 45/46/56/57/59；orchestrator-gate.sh 5 PASS + 1 BLOCKED、contract-registry.sh 3 PASS + 2 BLOCKED；run_all 20.1/20.10 计算化仍 BLOCKED；act/10、act/11 DEFERRED；验收 `impl-08-orchestrator/ACCEPTANCE.md` §5.1）
- [x] impl-05：M4 Knowledge Extraction 最薄接入（状态：`ACCEPTED` 2026-09-12；定稿 `8cedae2` → R1 REWORK `1a7919e` → 返工 `d982dd6` → R2 READY `930c972`；K1 `fab45cb`/`5ba7049`/`d16eccf`、K2 `ca42ee9`/`2d46155`、K3 `03f7f90`/`32192dd`、K4 `a8172f8`/`06d1a28`；裁定 47–55、58、60；m4-stage-gate.sh 13 PASS + 3 BLOCKED exit 2；K5 可选未派发；用户待办：真实 expert_verified 签发决定表；验收 `impl-05-knowledge/ACCEPTANCE.md` §5.1）
- [x] impl-06：M6 Review & Curation 最薄接入（状态：`ACCEPTED` 2026-09-13；定稿 `981156c`，裁定 61/62 `1eca795`；四查 R1 REWORK `9c1d971`（裁定 67/68）→ 返工 `479d44e` → R2 REWORK `d77867e`（N1，裁定 69）→ 返工 `c740603` → R3 READY `4390b6c`（agy Gemini 3.1 Pro；主 Agent 复核阈值 23…129/138 与 carried 条件式属实）→ 实现中（agy，会话 `w5h1`，用户要求改用 Gemini 3.8 Flash Medium；K1/K2/K3 分组停下待验收）：K1 `bc75e87`/`6904e5a`/`4a5e86f` `ACCEPTED`（ACCEPTANCE §5.1，63 OK），K2 `811b137`/`27bcbf7`/`9c28d96`/`5f32628` 验收 107 OK 但真实 reviewed_edition/package 键不符 §5.3（主 Agent 端到端经 M7 校验发现）→ 裁定 72，返工 06a `3753034` `ACCEPTED`（ACCEPTANCE §5.3：109 OK，主 Agent 独立复现 Red，真实输出通过 M7 两个校验）；K3 由 cmd DeepSeek（会话 `w5h3`，agy 额度耗尽后用户决定换执行器）完成：ACT 08 `caf599e`、09a `cb6ea8e`（裁定 74）、ACT 09 `4e0cf93`、09b `feb99df`（裁定 75）、ACT 11 `b5be811` `ACCEPTED`（ACCEPTANCE §5.4：145 OK，m6-data-fields.sh 11 PASS + 3 BLOCKED exit 2，金标篡改命中）；前置 impl-00 act/13 已 `ACCEPTED`（`573c3fb`）；用户待办：真实 expert_verified 签发决定表）
- [ ] impl-07：M7 Incremental Assembly（状态：创世薄切片 G0 `READY`——定稿 `91e5348`、裁定 63–66 `78e21cc`、R1 REWORK `f63ca89` → 返工 `6e7f5f1` → R2 READY `e2c8d79`，S3 已修 `3d97bb2`；G0 实现中（agy Gemini 3.8 Flash High，会话 `w5g0`，逐 ACT 停下待验收）：G0-01 `c79b36a` `ACCEPTED`（ACCEPTANCE §5.1，30 OK，真实 m4 金标校验 PASS）；验收发现 id_range 键形两层 → 裁定 70；G0-02 停手上报补发号与活对象重叠 → 裁定 71，G0-01a `8f9917f` 与 G0-02 `749fc04` `ACCEPTED`（ACCEPTANCE §5.2，53 OK）；G0-03 `bcdfdc1`（66 OK，矩阵外 5 例篡改全拦）与 G0-04 `bc47036`（79 OK，拒绝零写入，裁定 73）`ACCEPTED`（ACCEPTANCE §5.3/§5.4）；G0-05 `a4a399f`（89 OK，m7-assembler 10 PASS + 6 BLOCKED exit 2，金标篡改命中）`ACCEPTED`（ACCEPTANCE §5.5）——**创世薄切片 G0 全部 ACCEPTED**，会话 `w5g0` 已关；完整增量汇编 DEFERRED，首纵切外）
- [x] impl-09：M1 电子文本入库 + M2 电子文本清洗（状态：**`ACCEPTED`** 2026-09-16，W7-7.2；阶段 A 起草四轮 `ae62250`→`7031e42`（裁定 85/86）；J1 `08b62fc` + J1a `c4723c8`（裁定 88 空转护栏）、J2 `744335c`、J3 `054b4e9`/`a9c3dcd`/`a61501c`/`1d190da` + J3a `7dcfb56`（裁定 90：12 类只实现 6 类）+ J3b `39694fd`（裁定 91：实现的不是 README §5 规则）+ J3c `fff092d`（裁定 92：形近表凑数）、J4 `2084e11`/`84845e6`（裁定 94 D1–D3）、返工 J1b `3e25993`（裁定 94 D4 追踪链闭合）；intake `Ran 35 OK`、digitization `Ran 67 OK`；`m1-intake.sh`/`m2-sanitization.sh` 宿主缺失时 exit 2；验收 `impl-09-intake/ACCEPTANCE.md` §3.1–§3.6）
- [x] impl-10：M3 偏移锚点 + 语义层（状态：**`ACCEPTED`** 2026-09-16，W7-7.3；阶段 A `fcf9458`→`3359e4b`（裁定 89）；L1 `0d50d29`/`1eab4be`；L2 `e5b07ed`/`6ec07c5`（裁定 93）；L3 `13ddfd1`/`e42c482`/`2d7b613` + `61070ad`；L4 `eff2305` + L4a `5b573e3`（裁定 97 恢复 OCR 防篡改护栏）；corpus 套 `Ran 156 OK`、semantic 套 `Ran 54 OK`；真实书源过 M3 验收脚本 4 PASS + 1 BLOCKED（缺 `recordings.yaml`）；验收 `impl-10-corpus-semantic/ACCEPTANCE.md` §3.1–§3.5）

### W8 真书全链（《乾元秘旨》电子文本 → M8，裁决 100–108；分波表 `G7-PLAN.md` §6）

- [x] 8.0 impl-09 J3f（`87ce16c`）+ J4b（`1406048`）：M1/M2 验收改为对宿主原文实跑并与独立期望比对；宿主与 `expected/` 入库（验收 `impl-09-intake/ACCEPTANCE.md` §3.9/§3.10）
- [x] 8.1 impl-01 R81a（`7bdaa9c`，`ids.py` 接受 `ss_`/`sem_` 偏移形态、唯一权威）+ impl-10 R81b（`08e3bba`，电子文本 M3 补 `coverage_report`/`corpus_package`/m3 结构层阶段包）；裁定 102（验收 `impl-10-corpus-semantic/ACCEPTANCE.md` §3.6）
- [x] 8.2 impl-05 R82a（`71c913f`，M4 按 `evidence_level` 分派、去 `page` 依赖）+ R82b（`7838d59`，真书 m4 宿主、协议 v2 两路提交件）；裁定 104；**用户 24 条分歧裁决已导入，M4 `srun_bafd7499…` 封存 `succeeded`**（验收 `impl-05-knowledge/ACCEPTANCE.md` §5.2/§5.3）
- [x] 8.4 impl-06 M6：R84（`4e16022`，证据偏移严格按 I-11）+ R84b（`cb96b94`，审核台 offset 锚点与 offset 上游桩）+ R84c（`e5c960a`，裁定 108 夹具更正）已验收（验收 `impl-06-review/ACCEPTANCE.md` §5.6）
- [x] 8.4b 跑 M6 到 `awaiting_human`（srun_3009b37a…）→ 主 Agent 已生成 M6 审核表模板 `var/ledgers/qianyuan_w8_review/m6_review_decisions_template.yaml` 交用户（已披露：26 条 assertion 无 `concept_refs`、2 条 a 路 assertion 被 G4 拒收）
- [ ] 8.5 impl-07 M7：Snapshot `editions[]` 补 `evidence_level`/`corpus_spans_revision_id`、证据偏移统一 I-11、修 `genesis_package.json` 级别与 ID 形态矛盾（裁定 106 D4，未派）
- [x] 8.6-A impl-04 设计草案（`fa3cc54`）+ 主 Agent 裁决与更正（裁定 107，README §11.11）
- [x] 8.6-ACT08 impl-00 登记（`ff21388`）：`graph_projection_pack`、`evidence_map_pack` offset 变体、M8 检查名闭集与 `not_applicable`、`entry_id_allocation`（验收 `impl-00-interfaces/ACCEPTANCE.md` §5.6）
- [x] 8.6-K1 impl-04 ACT 09（`fc31716` GraphProjectionPack 纯函数）+ ACT 10（`ce3ddab` `reference_and_hash_only` 与 offset 七段链）（验收 `impl-04-dataset/ACCEPTANCE.md` §5.2）
- [ ] 8.6-K2 impl-04 ACT 11（知识链前三段 + `ent_` 发号表）+ ACT 12（M8 Gate 闭集与实评）；派单 `~/tmux-agents/runs/prompts/agy-86d.txt`，未开工
- [ ] 8.6-K3 impl-04 ACT 13（改读 M7 Snapshot，须待 8.5）+ ACT 14（`m8-span-identity.sh` 电子文本路线）
- [ ] 8.7 impl-08 orchestrator 登记 m4/m6 与 m3 文本入口；各验收脚本电子文本路线；`run_all.sh` 20.4/20.6/20.8/20.9 按判定输出（P4 独占 ACT）
- 用户待办：M6 审核表（8.4b 后）；真实 `expert_verified` 签发决定表（裁定 80，不阻断 `INTERNAL_DEMO`）

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
- [x] NC-003：公共 REST/OpenAPI/Swagger 契约与错误目录（状态：`ACCEPTED`，2026-09-11 R2；REST 仓 `67910c3`→`5730ed9`，act/01～06，69 测试；R1 验收发现可空字段 3.0 写法、遗留错误体被改、字节上限三处缺陷，act/06 修复并合入 NC-009 前置补丁 P1/P2）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/community_api.md`（functions-py 现状盘点与沿用表、20 端点目录、头参数与 ETag、错误目录与 L0 映射、Schema 字段表、分页与限流实值、命令账本结果白名单、D-NC003-01～11）；验证器 `openapi-spec-validator 0.9.0` 已装入 `.venv-openapi`，既有 REST 契约验证失败（`'headers' was unexpected`）作为 Red 基线
  - [x] 六件套 `work-items/nc-003/`（act/01 验证器接入与 35 处迁移、act/02 组件与内容端点、act/03 评论/互动/分享/举报/命令端点、act/04 示例校验与版本号）与守卫 `reviews/nc003_guard.sh`
  - [x] wjt-react 四查：R1 返工 6 项 + R2 返工 1 根因（14 行断言实为 10 块/其余 9 个）均落实并自证，READY（`reviews/NC-003-REVIEW-R1.md`）；守卫 `nc003_guard.sh` 0
  - [ ] 用户派发外部执行 Agent（`work-items/nc-003/PROMPT.md`，五个提交在 repository-rest-adapter 仓库）；主 Agent 按 ACCEPTANCE.md 验收
- [x] NC-015：接入 S6——设备授权、传输一次一密与中转删除协议（状态：`ACCEPTED`，2026-09-11 验收 R1；learn_system `2d3a366`→`b39d4f6`；**v1.6 改为接入型**，2026-09-11 用户确认：私人数据保护走 xuan-storage S6 模型，无长期密钥、无恢复材料；契约 `contracts/private_sync.md` 与六件套 `work-items/nc-015/` READY（2026-09-11：R1 返工 5 项 + R2 返工 1 项落实），守卫 `reviews/nc015_guard.sh` 0；PROMPT 已交用户派发）
  - [x] 规格侧契约（主 Agent）：`private_sync.md`（同步身份 app_user_id、授权记录与 guard 八步判定、直连 DTLS/中转双通道 notifier+Storage、X25519+HKDF 一次一密与 AAD、三层删除、七步验收、15 样例、检查器红条件、D-NC015-01～07）
  - [x] 六件套（act/01 样例、act/02 检查器）与守卫
  - [x] wjt-react 四查 + 十二攻击/故障场景审查：R1 返工 5 项（notifier TTL 冲突、会话公钥绑定、signed_fields、AAD 原因码、证书哈希定义）+ R2 返工 1 项（证书哈希公式复算），均落实（`reviews/NC-015-REVIEW-R1.md`）
  - [x] 执行（2 个提交）；主 Agent 验收 R1 ACCEPTED（V0～V8 原始输出、盲测 BT0～BT7 全 PASS、八场景攻击审查；修正契约 §5 第 95 行 TTL 文案）；解锁 NC-016
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
- [x] NC-009：公共发布事务、权限扫描与命令账本服务（状态：`ACCEPTED`，2026-09-11 R3；SERVER `c29a31a`→`df5c3da`、RULES `ea8c9b8`，act/01～06，全量 459/5/9、规则 65、守卫 0；R1 盲测三处缺陷由 act/05 修复，R2 发现快照补默认值与日志异常文本由 act/06 修复；act/06 经 tmux+agy 执行）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/community_server.md`（canonical SERVER 与 RULES 仓实值、六集合与文档、账本事务六步、W1～W6 前置顺序与写集、读路径与 ACL 18 条矩阵、规则 jest、测试名、D-NC009-01～08）
  - [x] 六件套 `work-items/nc-009/`（act/01 账本、act/02 发布/更新/收回、act/03 回收站/查询/精简、act/04 ACL/规则/可观测）与守卫 `reviews/nc009_guard.sh`
  - [x] 自审 5 项 + wjt-react R1 返工 3 项 + R2 返工 1 项，READY（`reviews/NC-009-REVIEW-R1.md`）
  - [x] 环境：磁盘清理后重建 `.venv`，基线 411 passed / 5 个既有失败（README 逐名登记）
  - [ ] 用户派发；主 Agent 按 ACCEPTANCE.md 验收
- [x] NC-010：客户端命令队列、公共 API 客户端、发布状态与页面（状态：`ACCEPTED`，2026-09-11 R2；reading-notes `bd894b4`→`4588f78`，act/01～06，flutter test +214、analyze 0、守卫 0；R1 盲测发现 payload_hash 无 If-Match 时省略键、键按 UTF-16 排序，act/06 修复；act/06 与验收命令经 tmux+agy 执行）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/community_client.md`（独立 CommunityDatabase、IdTokenProvider、API 客户端、命令队列状态机与 R5 对账、payload_hash 跨端参考值、作者视角八档文案、发布流程、四屏七状态、三个确认层、D-NC010-01～07）
  - [x] 六件套 `work-items/nc-010/`（act/01 API 客户端、act/02 数据库与队列、act/03 控制器、act/04 页面与确认层、act/05 七状态）与守卫 `reviews/nc010_guard.sh`
  - [x] wjt-react 四查：R1 返工 7 项 + 2 建议、R2 返工 2 项，READY（`reviews/NC-010-REVIEW-R1.md`）
  - [ ] 用户派发；主 Agent 按 ACCEPTANCE.md 验收
- [x] NC-011：两级评论/回复与编辑删除（状态：`ACCEPTED`，2026-09-12 R1；REST `4671c92`、SERVER `7d1163c`→`0fad16e`、RULES `dd3445f`、CLIENT `59cd50a`→`463835e`；守卫 `--require-impl all` 0，盲测 ①～⑧ 与 T31～T34 五轮全部通过）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/community_discussion.md`（集合与 Thread ID、W7～W9 判定顺序、R2 分页/游标/ETag、R2-05 受控屏障、客户端队列接入/控制器/面板/七状态、参考值、D-NC011-01～20）；`community_api.md` §11 补丁；DESIGN §7.1 mention 上限改 413
  - [x] 六件套 `work-items/nc-011/`（三线并行：REST act/01 ｜ SERVER act/02→03→04 ｜ CLIENT act/05→06）与守卫 `reviews/nc011_guard.sh`
  - [x] wjt-react 四查（agy）：R1 返工 4 项（游标写法、K11 可测性、ownerScope 来源、待发送跟踪集合），R2 READY（`reviews/NC-011-REVIEW-R1.md`）
  - [ ] 三线派发；主 Agent 按 ACCEPTANCE.md 验收
- [ ] NC-012：赞踩/收藏/分享/@/关系与举报（2026-09-12 拆分，D-NC012-01）
  - [x] NC-012a：赞踩、收藏、分享、举报与 mention 文本校验（状态：`ACCEPTED`，2026-09-12 R1：守卫 `--require-impl all` 0，盲测 ①～⑦ 通过；REST `cb686d0`、SERVER `db52847`→`8d22451`、RULES `4b81d8d`、CLIENT `e1655a4`→`107ec90`，已推送 Gitea；契约 `openspec/annotation-community/contracts/community_interactions.md`，`community_api.md` §12 补丁；六件套 `work-items/nc-012a/`，守卫 `reviews/nc012a_guard.sh`；三线：REST act/01 ｜ SERVER act/02→03 ｜ CLIENT act/04→05→06）
    - [x] 契约统一 reading-notes 两个同名 `MentionRef`（D-NC012-13，NC-011 验收遗留）
    - [x] wjt-react 四查（tmux + agy，会话 nc012r）：R1 READY、返工 0 项（`reviews/NC-012a-REVIEW-R1.md`）；主 Agent 采纳建议 1～3 写死 resource_ids 字典、refreshPending 防重入、I10 重试间隔
    - [x] 三线派发（tmux + agy：nc012a-rest ｜ nc012a-srv ｜ nc012a-cli）；REST 停手一次裁定 D-NC012-22；主 Agent 按 ACCEPTANCE.md 验收 R1 ACCEPTED
  - [ ] NC-012b：宿主社交注入、mention 候选与编辑器接线、三类依赖关系数据的无效 mention（状态：`BLOCKED`，等 NC-001-02）

### 通知

- [ ] NC-013：事务事件、投递、通知正文与补拉端点（状态：`BACKLOG`）
- [ ] NC-014：Notification 宿主适配、去重与导航（状态：`BACKLOG`）

### 私人同步、备份与删除

- [ ] NC-016：私人加密 mapper 与设备同步（2026-09-12 拆分，D-NC016-01）
  - [x] NC-016a：guard 补丁、AES-GCM AAD、一次一密信封与接收验收（状态：`ACCEPTED`，2026-09-12 R1：守卫 `--require-impl all` 0，盲测 ①～⑥ 通过（pyca 解多块信封、换序截断拒收、JSON 往返、旧会话零写入、200 组 guard 三方一致）；此前 `DISPATCHED`，四查 R1 返工 2 项、R2 READY（`reviews/NC-016a-REVIEW-R1.md`）；契约 `openspec/annotation-community/contracts/private_sync_impl.md`，六件套 `work-items/nc-016a/`，守卫 `reviews/nc016a_guard.sh`；两线：STORAGE act/01 ｜ CLIENT act/02→03）
    - [x] STORAGE act/01（NC-016a-A）：tmux + cmd 会话 nc016s；两次停手（worktree 建树超时、既有测试到期占位值 → D-NC016-14 `c791d94`）；xuan-storage 分支 `fix/nc016-guard-aad` `755a8fc`，main 仍 `8ddb877`；主 Agent 复跑守卫 `--require-impl storage` 为 0（K06 PASS）
    - [x] CLIENT act/02→03（NC-016a-B/C）：NC-011 验收后经 tmux + cmd（deepseek/deepseek-v4.1-flash）派发，会话 nc016c（2026-09-12）；`a9a9621`→`d80703b`，flutter test +270，无停手
  - [ ] NC-016b：两台真实设备 LAN/WebRTC 集成、中转上传与宿主装配（状态：`BLOCKED`，等 NC-001 设备表）
- [x] NC-017：口令加密导出文件格式与本机写入（v1.6；状态：`ACCEPTED`，2026-09-12 R1；reading-notes `e913b14`→`4a0d70a`，flutter test +253，Python 独立解码 28 项与盲测 ②～⑥ 全部通过）
  - [x] 规格侧契约（主 Agent）：`openspec/annotation-community/contracts/private_export.md`（容器/清单、Argon2id m65536 t3 p1 经 OpenSSL 交叉核对、带 AAD 分块 AES-GCM、统一失败、`.partial` 原子写入、参考值、D-NC017-01～11）
  - [x] 六件套 `work-items/nc-017/`（act/01 格式层、act/02 写入器）与守卫 `reviews/nc017_guard.sh`
  - [x] wjt-react 四查（agy）：R1 READY、返工 0 项，K/D/文件摘要经 OpenSSL 与 Python 独立复算吻合（`reviews/NC-017-REVIEW-R1.md`）
  - [x] 派发：NC-011 CLIENT 线 `463835e` 提交后经 tmux + cmd（deepseek/deepseek-v4.1-flash）派发，会话 nc017（2026-09-12）
  - [x] 主 Agent 按 ACCEPTANCE.md 验收 R1：ACCEPTED（守卫锁文件正则缺陷已修 `d848c56`）
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

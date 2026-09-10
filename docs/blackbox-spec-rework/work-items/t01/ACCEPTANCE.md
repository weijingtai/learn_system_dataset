# T-01 主 Agent 验收清单

状态：`ACCEPTED`（2026-09-09）

## 1. Scope and Commits

- [x] 提交只修改 `openspec/learn-system-blackbox-architecture.md`（提交 `5b99fb1`，+28, -1）
- [x] 未触碰任何代码、JSON Schema、测试用例或数据库文件
- [x] 未修改工作包文档、TODO.md、PLAN.md、HANDOFF.md 或 `verify-T.sh`
- [x] 提交消息严格为 `docs: integrate three-tier terminology model into M4`

## 2. Terminology 3-Tier Model Verification

- [x] L1 共享源数据层完整声明（路径 `schemas/shared/canon/`，ID `co_shared_<domain>_NN`）
- [x] 明确声明 L1 匹配为「确定性字典匹配路径，不调用大模型（免模型），零成本直接命中」
- [x] L2 同形异义层完整声明（路径 `schemas/shared/homographs/`，锚 `homograph_id=hg_<4位数字>`，各技法义项 `co_<technique>_<6位数字>`）
- [x] 明确声明 L2 命中时「必须按当前技法选择对应义项绑定带技法的 concept_id，绝对禁止裸绑字面」
- [x] L3 技法独有层完整声明（ID `co_<technique>_<6位数字>`，新词进候选）
- [x] §5 基础设施 Contract Registry 明确追加 `schemas/shared/canon` 与 `schemas/shared/homographs` 冻结输入

## 3. Evidence and Regression

- [x] `docs/blackbox-spec-rework/work-items/t01/TDD.md` 中的全部 Green checks 通过
- [x] `bash docs/blackbox-spec-rework/verify-T.sh` 退出码由 14 严格降为 13
- [x] `T-01` 由 FAIL 转为 PASS
- [x] `git diff --check` 通过
- [x] 主 Agent 规格审查通过
- [x] 主 Agent 质量审查通过
- [x] `SUBAGENT_TODO.md` 与 `PLAN.md` 对应项同步更新
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`ACCEPTED`。经主 Agent 独立核查代码 diff、全套自动化 checks 以及全局 verify-T.sh 脚本，三层术语规范与两处落点修改完整准确，符合全部准出条件。

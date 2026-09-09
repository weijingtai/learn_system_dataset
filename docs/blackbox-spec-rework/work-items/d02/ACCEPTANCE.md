# D-02 主 Agent 验收清单

状态：`ACCEPTED`（2026-09-09）

## Scope and commits

- [x] ACT01、ACT02 各自独立提交且顺序正确（`08fe789` -> `fa69901`）
- [x] 修改文件全部属于对应 `scope.write`
- [x] 未修改工作包、现有全局门禁或真实 qtbj manifest
- [x] 只有四份顶层 `*.schema.json`

## Red-Green evidence

- [x] 使用仓库 `.venv`，未修改系统、用户或 Homebrew Python 环境
- [x] ACT01 Schema 缺失时门禁先失败，随后通过
- [x] ACT02 Schema 缺失时门禁先失败，随后通过
- [x] invalid fixture 真正返回非零，未被 `|| true` 假吞
- [x] YAML→JSON 后实际再次通过 StagePackage Schema
- [x] fixture 的 `source_id` 实际读取并匹配真实 qtbj manifest

## Contract semantics

- [x] ArtifactRef 两分支互斥，均携带 `artifact_revision_id`
- [x] StagePackage 六段齐全，stage 与 pkg 前缀一致
- [x] Lineage 含可重放的 transformation 最小结构
- [x] StepRequest 保留 §7 五字段，M1 空输入合法，latest 非法，重跑关联明确
- [x] StepResult 六状态齐全，人工 token 与失败证据条件有效
- [x] 四 Schema 均 `additionalProperties:false`，状态/minimum/唯一性结构断言通过，且离线 `$ref` 可解析
- [x] Schema version 与 content Revision 未混用

## Gates and review

- [x] `bash openspec/schemas/verify.sh` 全部 PASS、退出 0
- [x] 全局 T 失败数不高于 17（实测 17 FAIL / 2 PASS）
- [x] `git diff --check` 通过
- [x] 检查空断言、永真条件、跳过分支和只验证 fixture 自身的假绿
- [x] 规格符合性审查通过
- [x] 质量审查通过
- [x] PLAN/HANDOFF/TODO 与证据归档
- [x] 主 Agent 标记 `ACCEPTED`

最终结论：`ACCEPTED`。四份 L0 机器 Schema 契约冻结完成，支持离线本地引用与元校验。

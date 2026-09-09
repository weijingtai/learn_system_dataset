# D-02 主 Agent 验收清单

状态：等待执行

## Scope and commits

- [ ] ACT01、ACT02 各自独立提交且顺序正确
- [ ] 修改文件全部属于对应 `scope.write`
- [ ] 未修改工作包、现有全局门禁或真实 qtbj manifest
- [ ] 只有四份顶层 `*.schema.json`

## Red-Green evidence

- [ ] 使用仓库 `.venv`，未修改系统、用户或 Homebrew Python 环境
- [ ] ACT01 Schema 缺失时门禁先失败，随后通过
- [ ] ACT02 Schema 缺失时门禁先失败，随后通过
- [ ] invalid fixture 真正返回非零，未被 `|| true` 假吞
- [ ] YAML→JSON 后实际再次通过 StagePackage Schema
- [ ] fixture 的 `source_id` 实际读取并匹配真实 qtbj manifest

## Contract semantics

- [ ] ArtifactRef 两分支互斥，均携带 `artifact_revision_id`
- [ ] StagePackage 六段齐全，stage 与 pkg 前缀一致
- [ ] Lineage 含可重放的 transformation 最小结构
- [ ] StepRequest 保留 §7 五字段，M1 空输入合法，latest 非法，重跑关联明确
- [ ] StepResult 六状态齐全，人工 token 与失败证据条件有效
- [ ] 四 Schema 均 `additionalProperties:false`，状态/minimum/唯一性结构断言通过，且离线 `$ref` 可解析
- [ ] Schema version 与 content Revision 未混用

## Gates and review

- [ ] `bash openspec/schemas/verify.sh` 全部 PASS、退出 0
- [ ] 全局 T 失败数不高于 17
- [ ] `git diff --check` 通过
- [ ] 检查空断言、永真条件、跳过分支和只验证 fixture 自身的假绿
- [ ] 规格符合性审查通过
- [ ] 质量审查通过
- [ ] PLAN/HANDOFF/TODO 与证据归档
- [ ] 主 Agent 标记 `ACCEPTED`

最终结论：待定。执行 Agent 完成不等于验收完成。

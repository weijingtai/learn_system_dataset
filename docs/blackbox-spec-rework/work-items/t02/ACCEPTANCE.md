# T-02 主 Agent 验收清单

状态：等待执行

## Scope

- [ ] 提交只改 `openspec/learn-system-blackbox-architecture.md`
- [ ] 未修改工作包、门禁、Schema、代码或依赖

## Frozen IDs

- [ ] `src_<work>_ed<NN>`
- [ ] `ss_<work>_ed<NN>_p<NNNN>_s<NN>`
- [ ] `ku_<technique>_<6位数字>`
- [ ] `as_<technique>_<6位数字>`
- [ ] `pr_<technique>_<6位数字>`
- [ ] `co_shared_<domain>_NN`
- [ ] `co_<technique>_<6位数字>`
- [ ] `hg_<4位数字>`

## Proposal and semantics

- [ ] 六类新格式全部标为待用户确认
- [ ] ProcessingRun 未复用 `pr_`
- [ ] Artifact logical ID 与 Revision ID 分离
- [ ] Schema version 与 content Revision 分离
- [ ] 未引入身份系统或第三方依赖

## Evidence

- [ ] TDD Green checks 通过
- [ ] T-02b 从 FAIL 变为 PASS
- [ ] 无新增全局失败
- [ ] `git diff --check` 通过
- [ ] 规格符合性审查通过
- [ ] 质量审查通过
- [ ] 用户确认或修改六类新 ID 前缀

最终结论：待定。未获用户前缀确认时，D-02 保持 `BLOCKED`。

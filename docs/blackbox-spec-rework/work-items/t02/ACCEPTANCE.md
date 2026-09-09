# T-02 主 Agent 验收清单

状态：`BLOCKED`（返工提交 `376e78c` 已通过；仅待用户确认前缀）

## Scope

- [x] 提交只改 `openspec/learn-system-blackbox-architecture.md`
- [x] 未修改工作包、门禁、Schema、代码或依赖

## Frozen IDs

- [x] `src_<work>_ed<NN>`
- [x] `ss_<work>_ed<NN>_p<NNNN>_s<NN>`
- [x] `ku_<technique>_<6位数字>`
- [x] `as_<technique>_<6位数字>`
- [x] `pr_<technique>_<6位数字>`
- [x] `co_shared_<domain>_NN`
- [x] `co_<technique>_<6位数字>`
- [x] `hg_<4位数字>`

## Proposal and semantics

- [x] 六类新格式全部标为待用户确认
- [x] ProcessingRun 未复用 `pr_`
- [x] Artifact logical ID 与 Revision ID 分离
- [x] StagePackage logical ID 与 Revision ID 分离
- [x] `<stage>` 冻结为可生成正则的 `m1`–`m8` 闭集
- [x] Schema version 与 content Revision 分离
- [x] 未引入身份系统或第三方依赖

## Evidence

- [x] 第一轮原 TDD Green checks 通过
- [x] T-02b 从 FAIL 变为 PASS
- [x] 无新增全局失败（18 → 17）
- [x] `git diff --check` 通过
- [x] 补充语义门禁通过
- [x] 规格符合性审查通过
- [x] 质量审查通过
- [ ] 用户确认或修改六类新 ID 前缀

## 第一轮阻断发现

1. 架构规格 :210 要求 StagePackage 每个物理修订使用 `artifact_revision_id`，但 :249 与 :261 又把 `pkg_<stage>_<32hex>` 定义为物理修订，D-02 无法确定 StagePackage Schema。
2. `<stage>` 只举例 m1、m2，没有闭集或词法规则，D-02 无法生成确定性正则。

## 返工验收

- 返工提交：`376e78c docs: clarify stage package identity`
- 修改范围：仅 `openspec/learn-system-blackbox-architecture.md`
- StagePackage：`pkg_...` 为逻辑身份；每个物理修订另用 `rev_...`；ArtifactRef 同时携带两者。
- Stage：冻结为 `m1`–`m8` 闭集，其他值非法。
- 门禁：补充 Green checks 全通过；T-02/T-02b PASS；全局保持 17 FAIL，无新增失败；`git diff --check` 通过。
- 双轴独立复核：Standards `APPROVED`；Spec `APPROVED`。

最终结论：返工完成并通过技术验收。六类提案尚未获得用户确认，因此 T-02 暂不标记 `ACCEPTED`，D-02 继续 `BLOCKED`。

# T-02 主 Agent 验收清单

状态：`REWORK_REQUIRED`（第一轮提交 `6e317cc`）

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
- [ ] StagePackage logical ID 与 Revision ID 分离
- [ ] `<stage>` 冻结为可生成正则的闭集
- [x] Schema version 与 content Revision 分离
- [x] 未引入身份系统或第三方依赖

## Evidence

- [x] 第一轮原 TDD Green checks 通过
- [x] T-02b 从 FAIL 变为 PASS
- [x] 无新增全局失败（18 → 17）
- [x] `git diff --check` 通过
- [ ] 补充语义门禁通过
- [ ] 规格符合性审查通过
- [ ] 质量审查通过
- [ ] 用户确认或修改六类新 ID 前缀

## 第一轮阻断发现

1. 架构规格 :210 要求 StagePackage 每个物理修订使用 `artifact_revision_id`，但 :249 与 :261 又把 `pkg_<stage>_<32hex>` 定义为物理修订，D-02 无法确定 StagePackage Schema。
2. `<stage>` 只举例 m1、m2，没有闭集或词法规则，D-02 无法生成确定性正则。

最终结论：第一轮不通过，进入最小返工。D-02 保持 `BLOCKED`。

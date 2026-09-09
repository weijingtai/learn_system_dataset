# T-02 BDD 场景

## B1 冻结格式无损转录

Given 既有 Schema 与术语规范已冻结八类 ID，When 执行者读取架构 §8.1，Then 能逐项得到完全相同的格式、位数与权威来源，不出现重命名。

## B2 新对象前缀无冲突

Given Proposition 已使用 `pr_`，When 查看 ProcessingRun 提案，Then 其前缀为 `prun_`，不会产生对象类型歧义。

## B3 身份与 Revision 分离

Given 同一 Artifact 产生新版内容，When 表达两版数据，Then `artifact_id` 保持不变，每版拥有不同 `artifact_revision_id`，旧版仍可追溯。

## B4 版本轴分离

Given Schema 结构升级或内容被重新编译，Then Schema version 与 content Revision 可分别变化，不被要求同号。

## B5 非法格式可判定

Given 缺前缀、错误位数、大写十六进制或把 `pr_` 用作 ProcessingRun，Then消费者能根据文档明确判为不符合提案格式。

## B6 决策边界

Given 六类新 ID 尚未获用户确认，Then架构只把它们标为提案，不得声称冻结或最终规范；D-02 继续阻塞。

## B7 最小依赖

Given 单人单机目标，Then新稳定段可由语言标准库生成，不要求数据库服务、身份系统或新第三方包。

## B8 StagePackage 双标识

Given 同一个 StagePackage 被修正，When 表达修正前后的两个版本，Then `stage_package_id`（`pkg_...`）保持不变，每个版本分别取得新的 `artifact_revision_id`（`rev_...`），ArtifactRef 同时携带两者。

## B9 Stage 闭集

Given D-02 需要生成确定性 ID 正则，When 解析 `pkg_<stage>_<32hex>`，Then `<stage>` 只能取 `m1` 至 `m8`；其他值必须判为非法。

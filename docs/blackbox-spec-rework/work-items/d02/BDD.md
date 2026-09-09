# D-02 BDD 验收场景

## B1 精确修订引用

Given 一个 Artifact 有稳定逻辑 ID 和多个 Revision，When Module 收到 StepRequest，Then 请求只能包含明确的 `rev_...`，使用 `art_...` 或 `latest` 必须失败。

## B2 M1 空输入

Given M1 从外部 SourceSubmission 开始，When `input_artifact_ids` 是空数组但字段存在，Then StepRequest 有效；省略字段仍无效。

## B3 人工等待结果

Given StepResult 状态为 `awaiting_human`，Then 必须同时返回单次恢复 token 与非空待处理队列；缺任一项无效，其他状态携带陈旧 token 也无效。

## B4 明确失败

Given StepResult 状态为 `failed`，Then 至少引用一个失败 Artifact Revision；没有失败证据的 `failed` 结果无效。

## B5 StagePackage 完整信封

Given 一个阶段产出 Package，Then payload、manifest、validation、lineage、logs、failures 六段缺一不可，且所有跨对象引用使用 ArtifactRef。

`lineage.transformations` 必须能回答该输出由哪个 StepRun、哪份配置、哪些输入 Revision 经过什么操作生成；M1 可以没有输入 Artifact，但必须记录输出。

## B6 逻辑包与物理修订分离

Given 同一个 M1 StagePackage 被修正，Then保留 `pkg_m1_...`，新建 `rev_...`；ArtifactRef 同时携带二者，不得混入普通 `art_...`。

## B7 Stage 一致性

Given `stage=m3`，Then `stage_package_id` 必须以 `pkg_m3_` 开头；`pkg_m2_...` 或 `m9` 必须失败。

## B8 离线 round-trip

Given 《穷通宝鉴》现有 manifest 构造的 M1 YAML Package，When YAML 读入、转成 JSON、再按同一 Schema 校验，Then两种表示都通过且 `source_id` 未改变。

## B9 未知字段拒绝

Given L0 信封出现未声明字段，Then `additionalProperties:false` 使其失败，防止 Module 私自扩展核心契约。

## B10 重跑关联

Given 一个 StepRun 是对旧运行的重跑，When 创建 StepRequest，Then可用 `supersedes_step_run_id` 指向旧 `srun_...`；首次运行省略该字段，非法前缀必须失败。

## B11 回归隔离

Given 全局尚有其他 T 类失败，When D-02 门禁通过，Then既有失败数不得增加；不得为让 D-02 变绿而修改全局判据。

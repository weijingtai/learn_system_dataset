# T-01 BDD 验收场景

## B1 三层术语模型完整定义

Given 权威源 `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md §二` 确立了跨技法术语的三层划分，
When 执行者查看架构规格 §12，
Then 能完整找到 L1 共享源数据层（shared canon）、L2 同形异义层（homograph with per-technique senses）和 L3 技法独有层（technique-private）三层的定义、存放路径及对应 ID 规则，
And 三层名称与照抄源逐字一致，无删减或压缩。

## B2 L1 确定性闭集匹配免模型

Given L1 包含天干、地支、五行、八卦等穷尽闭集，
When M4 执行知识抽取前置处理时，
Then 规格正文明确规定：L1 匹配为确定性字典匹配路径，不调用大模型（免模型），直接命中并绑定 `co_shared_*`，保证零成本与 100% 准确率。

## B3 L2 必须绑定带技法义项（禁止裸绑字面）

Given L2 覆盖如“驿马”、“二十八宿”等字面相同但在各技法用法不同的词条，
When M4 处理命中的 homograph 字面时，
Then 规格明确规定：必须按当前技法选择对应义项并绑定带技法的 `concept_id`（如 `co_bazi_000042`），严禁裸绑字面；选不准则进入 uncertainties 待人工裁定，从源头杜绝跨技法串义。

## B4 M4 冻结输入 Artifact 声明

Given M4 判层依赖全局 canon 与 homographs 表，
When 执行者查看架构规格 §5 基础设施段的 Contract Registry，
Then 规格明确追加：`schemas/shared/canon` 与 `schemas/shared/homographs` 由 Contract Registry 登记并作为 M4 的冻结输入 Artifact。

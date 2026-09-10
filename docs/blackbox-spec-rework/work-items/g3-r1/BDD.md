# G3 R1 返工 BDD

## 场景 1：完整门禁不能被标题骗绿

Given 规格只保留 G1–G7 名称而删除强制语义，When 运行 T-04 门禁，Then 必须失败。

## 场景 2：证据链必须有序且完整

Given 链路遗漏 KnowledgeEntry 或写成 EvidenceLink → Assertion，When 运行 T-06 门禁，Then 必须失败。

## 场景 3：差距表必须描述当前仓库

Given §19 使用不存在的路径或把已经修复的问题写成当前缺口，When 运行 T-11 门禁，Then 必须失败。

## 场景 4：状态标签必须与章节语义一致

Given 任一章节状态错标、出现最终规范，或 §16 建议句没有局部讨论候选标签，When 运行 T-13 门禁，Then 必须失败。

## 场景 5：查询契约先定义再映射

Given D-07 尚未 ACCEPTED，When 尝试验收 T-07/T-08，Then 必须阻断。Given D-07 已冻结，Then query-contract 只能映射至 QueryContractPack。

## 场景 6：M5 只校验不生产

Given §16.3 把 M5 列为 Tag 内容字段生产者，When 运行 T-08 门禁，Then 必须失败；M5 作为 Validator 另列时才可通过。


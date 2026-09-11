# Pipeline 待办

本清单记录当前真实阻断项。完成标准以 [DATASET_ACCEPTANCE_STANDARD.md](DATASET_ACCEPTANCE_STANDARD.md) 为准；单个 validator 或 unit PASS 不代表整本数据集可用。

## P0：《穷通宝鉴》数据集假绿修复

- [ ] 修复 `tools/gen_outline.py` 对带正文二级章节的静默排除；验收：manifest、outline、batch 和 segment 使用同一字符口径，所有含正文 section 恰好覆盖一次，覆盖率 100%。
- [ ] 补编《论木》《论火》《论土》《论水》等当前遗漏正文；验收：新增 spans、assertions、paraphrases、units 与原书逐层对账，无重复覆盖。
- [ ] 把 PUA 勘误固化为可重放 source revision；验收：固定 raw 与转换版本可重建相同 transcript/task snapshot/hash。
- [ ] 修复八字 glossary 完整 span ID 到 RAG mentions 的映射；验收：八字 118 concepts、152 个声明引用逐项对账，禁止奇门 mentions 掩盖八字零命中。
- [ ] 收紧 RAG validator；验收：按 source/technique 独立检查，任一已确认概念零命中、跨书错命中或声明引用缺失均 FAIL。
- [ ] 增加 proposition 与 quote 的忠实性门禁；验收：改变含义的增删改写、跨 span 借用引文和错误 source anchor 均 FAIL。
- [ ] 分离命例、编者注文、通则与释义；验收：Case 不进入通则 assertion，editorial note 有独立层和来源。
- [ ] 结构化条件、加强条件、例外和反例；验收：不得仅靠 proposition 自由文本驱动 APP 匹配。

## P1：内容复核与确定性匹配

- [ ] 对现有 1,317 条八字 assertions 和 138 条 paraphrases 做分层盲审；验收：抽样规模、分层、随机种子、错误分类和专家仲裁满足验收标准，critical=0，并先修复已确认的漏主张、不忠实改写和命例误提。
- [ ] 定义 `BaziFactSet` 与 `ApplicabilityRule`；验收：`丙日干 + 亥月` 返回全部且仅返回适用的“十月丙火”规则，并说明缺失条件和已触发例外。
- [ ] 建立跨模型审核与领域专家签发状态机；验收：机器态内容不会进入公开消费查询。

## P2：发布与 APP 接入

- [ ] 实现 `KnowledgeReleaseCompiler`、ReleaseManifest 与 fail-closed validator（本条为 `KnowledgeReleaseCompiler` 唯一登记处，D-16 收敛 2026-09-11；规格 §16 M8）；验收：缺来源、证据、规则、审核、rights 或任一内容哈希时拒绝编译，重放产生相同发布哈希。
- [ ] 实现只读 App adapter；验收：客户端只接受带获批 release ID/hash 的 Bundle，直接读取 corpus、加工 units 或 dev RAG SQLite 必须失败。
- [ ] 接入 `pattern_knowledge_workbench`；验收：仅获批格局、流派观点、原文证据和规则可成为编译输入，工作台草稿、私人笔记和互动计数不得泄漏进知识发布包。
- [ ] Embedding 后置；验收：关闭向量能力时精确条件匹配、来源跳转、审核过滤和发布门禁仍完整通过，向量结果不能绕过任何硬门禁。

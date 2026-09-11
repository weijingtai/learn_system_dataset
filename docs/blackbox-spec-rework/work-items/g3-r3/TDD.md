# G3 R3 TDD 与变异矩阵

## 1. 永久测试入口

执行者新增：

```bash
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh d07
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t07
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t08
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all
```

脚本必须满足：

- 每例从权威规格复制新的 `/tmp` 文件，禁止变异叠加。
- 每例先断言替换或删除命中数等于预期；否则输出 `MUTATION_NOT_APPLIED` 并使整套失败。
- 用 `SPEC=<临时文件>` 调用 `verify-T.sh`。
- 错误规格返回 0 算测试失败；非零且出现该组目标 FAIL 标记才算通过。
- 最终输出 `MUTATIONS: <passed>/<total> rejected`；任一失败则脚本非零。
- 不引入第三方依赖，不修改权威规格，不把临时文件写入仓库。
- 期望常量来自本文件并硬编码在门禁/变异脚本中；严禁从当前 `$SPEC` 动态生成 expected 值，否则测试会与错误输入一起漂移。

## 2. 精确校验原语

门禁实现必须基于以下原语，而不是否定词枚举：

1. `exact_line(section, canonical)`：允许去除 Markdown 装饰和空白后比较完整行，匹配数必须为 1。
2. `exact_table(section, expected_map)`：表头一次、数据行数量等于字典大小、key 集合完全相等、每个 key 一次、每个 value 完全相等。
3. `exact_block(section, heading, claims)`：标题完整相等且一次；块截止到下一个同级标题；供给声明数量和内容完全相等。
4. `no_extra_pack(text, allowed_set)`：抽取全部以 `Pack` 结尾的标识，集合必须与期望集合相等。

稳定 oracle 只允许使用 `CASES.md` 冻结的 12 个完整 FAIL ID；case 通过必须出现其绑定的完整 ID，组前缀或同组其他 FAIL 不算命中。

`selftest` 必须内置两个最小 parser fixture：

- Normalize fixture：仅反引号、星号、空格、Tab、CR 的差异相等；改变一个标点、否定词或标识符必须不相等。
- Block fixture：包含三个编号块；精确标题各出现一次时通过，`EvidenceBundle` 改成 `WrongEvidenceBundle` 或同块出现两条供给声明时失败。编号块起止严格使用 `CANONICAL.md` 给出的正则。

## 3. D-07 规范常量与变异

三个专属块起始行必须分别完整等于当前规格中的：

- `` `TechniqueProfilePack` 承载各术数领域确定性事实结构与规则语法标准，消除跨技法匹配歧义：``
- `` `QueryContractPack` 规范发布包对外暴露的确定性只读查询契约与客户端调用接口，定义四个核心接口及兼容声明：``
- `` `RuleIndexPack` 承载确定性适用规则索引：``

向后兼容规范句必须恰好一次完整等于：

``- **向后兼容声明**：明确规定查询契约接口必须保持向后兼容演进，客户端只依赖稳定接口契约，不直接绑定底层文件存储形式。``

D-07 固定 25 例，逐例定义见 `CASES.md`。它覆盖全部 14 条 canonical、三块改名、四接口前缀污染、重复、删除和兼容否定；不得用“R2 原例”等历史指针代替。

## 4. T-07 完整映射字典与变异

§16.2 必须精确为下列 15 项，不允许只校验其中两项：

| key | 规范化后的唯一 value |
|---|---|
| release-manifest | ReleaseManifest（发布清单与元数据摘要） |
| schema | KnowledgeDataPack（及ContractRegistry对应模式定义） |
| concepts | KnowledgeDataPack（概念定义及术语体系） |
| entries | KnowledgeDataPack（知识条目KnowledgeEntry集合） |
| assertions | KnowledgeDataPack（结构化主张Assertion集合） |
| applicability-rules | RuleIndexPack（与KnowledgeDataPack中的适用规则） |
| school-views | KnowledgeDataPack（各流派分歧与立场视图） |
| evidence-links | EvidenceMapPack（证据链接与跨层关联） |
| source-spans | EvidenceMapPack（与KnowledgeDataPack中的原文片段引用） |
| source-anchors | EvidenceMapPack（底本物理位置证据锚点，必须随包发布） |
| scan-assets-or-references | SourceAssetPack（扫描图或受控引用） |
| exact-search-index | SearchIndexPack（精确检索索引） |
| fulltext-index | SearchIndexPack（全文检索索引） |
| optional-vector-index | 本期不产出（依据§21非目标） |
| query-contract | QueryContractPack（查询契约与接口定义） |

取代规范句必须恰好一次完整等于：

``黑箱架构规格以多子包组合的 `PublicationPackage`（特别是其中的结构化知识主体 `KnowledgeDataPack`）正式取代早期草案中单一扁平的 `KnowledgePack` 概念。``

T-07 固定 25 例，逐例定义见 `CASES.md`：15 个 key 各自错误右值、第二归属、取代句删除/重复/四类否定，以及指定 schema 删除和 query-contract 重复。

## 5. T-08 封闭结构与变异

§1 三个编号行必须各自完整匹配当前权威正文，编号 1–3 各一次；每行抽取出的 Package 集合分别严格为：

- 最小盘面概念字典：`{KnowledgeDataPack}`
- MarkContentBinding：`{KnowledgeDataPack, RuleIndexPack}`
- EvidenceBundle：`{EvidenceMapPack}`

§1 的三条规范行是：

```text
1. `最小盘面概念字典`：规模约 100–200 个概念，由 `KnowledgeDataPack` 供给，仅包含稳定 `concept_id` + 名称 + 基础类象，**严格声明不含规则 DSL**，用以解除 `TAG_SYSTEM_DESIGN.md §12.2` 的 G4 依赖倒挂问题；
2. `MarkContentBinding` 内容供给：由 `KnowledgeDataPack` 与 `RuleIndexPack` 供给，为 UI 标记提供内容与分歧数据；
3. `EvidenceBundle` 服务：由 `EvidenceMapPack` 供给，为解盘与证据高亮提供底层的无损证据链切片。
```

§16.3.1 必须恰有三个精确标题块：`最小盘面概念字典`、`MarkContentBinding 内容供给`、`EvidenceBundle 服务`。每块必须恰有一条“供给子包”行，Package 集合分别同上；同块内新增第二条供给声明必须失败。

§16.3.2 字段表必须恰有 5 行，精确映射：

| 字段 | Module | Package |
|---|---|---|
| omen_carrying | M4 | KnowledgeDataPack |
| condition_affordance | M4 | RuleIndexPack与KnowledgeDataPack |
| school_variance_display | M4/M6 | KnowledgeDataPack |
| concept_id | M4 | KnowledgeDataPack |
| 是否改变当前判断 | M4/M7/M6 | KnowledgeDataPack（MarkContentBinding） |

表格上方五条说明也必须各出现一次，并与表格 Module/Package 一致；M5 只能出现在 Validator 语义中。

T-08 固定 39 例，逐例定义见 `CASES.md`。它覆盖五字段表、五条说明、§1 三接口、§16.3.1 三块、错误/额外/重复供给、接口改名、M5 生产者，以及 §1 与 §16.3.1 两处各自独立的 DSL/G4 约束。

## 6. Red / Green

- Red：先提交或至少保存变异脚本，当前门禁运行 `all` 必须因 R3 的 7 个假绿而非零；输出要列出具体漏拦截案例。
- Green：D-07、T-07、T-08 分组依序转绿；最后必须精确输出 `MUTATIONS: 89/89 rejected`。
- 正常规格始终必须 `FAIL 合计: 0`。

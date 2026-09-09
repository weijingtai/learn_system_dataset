# Learn System 领域词汇

- **Work**：一部抽象著作；不代表某个具体刻本、抄本或电子来源。
- **Edition**：Work 的一个具体版本或传本，是 `EditionRun` 的归属范围；全部 EditionPart 通过后才标记完整。
- **EditionPart**：Edition 内可独立过阶段 Gate 的自然分部；优先按卷，无卷时使用连续页区间，不按单页或 SourceSpan 切分。
- **SourceAsset**：Edition 的原始 PDF、PNG、EPUB、TXT 或其他文件。
- **EditionRun**：一个 Edition 从 M1 到 M6 的阶段式加工运行。
- **ReleaseRun**：把新增 ReviewedEditionPackage 增量汇入既有规范知识并编译数据集的运行。
- **Artifact**：黑箱中需要永久留存、可按稳定 ID 引用的数据或执行证据。
- **Revision**：Artifact 或领域对象的一次不可变修订；新 Revision 不覆盖旧 Revision。
- **StagePackage**：一个阶段封存的 payload、manifest、validation、lineage、logs 和 failures 集合。
- **Concept**：可跨来源或术数对齐的规范术语身份；不要求一定具有机器识别规则。
- **Pattern（格局）**：Technique 范围内可由条件或规则识别的 Concept 子类型；聚合名称、规则、解释、来源和多条 Assertion。
- **KnowledgeEntry**：M8 面向 APP 编译的稳定产品词条，聚合一个 Concept 或 Pattern 的已发布主张、规则、流派视图和证据；它是发布视图，不是原始知识来源。
- **TechniqueProfile**：某一术数的事实字段、规则语义、校验约束和扩展契约。
- **KnowledgeGraph**：书籍、版本、格局、主张、规则、流派和证据之间的领域关系图。
- **LineageGraph**：Artifact、Revision、运行、工具、模型、校验和人工决定之间的生产溯源图。
- **PublicationPackage**：Learn System 黑箱的唯一对外输出，包含结构化数据、原始数据、二者关系及发布清单。

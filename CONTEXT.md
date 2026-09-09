# Learn System 领域词汇

- **Work**：一部抽象著作；不代表某个具体刻本、抄本或电子来源。
- **Edition**：Work 的一个具体版本或传本，是 `EditionRun` 的处理单位。
- **SourceAsset**：Edition 的原始 PDF、PNG、EPUB、TXT 或其他文件。
- **EditionRun**：一个 Edition 从 M1 到 M6 的阶段式加工运行。
- **ReleaseRun**：把新增 ReviewedEditionPackage 增量汇入既有规范知识并编译数据集的运行。
- **Artifact**：黑箱中需要永久留存、可按稳定 ID 引用的数据或执行证据。
- **Revision**：Artifact 或领域对象的一次不可变修订；新 Revision 不覆盖旧 Revision。
- **StagePackage**：一个阶段封存的 payload、manifest、validation、lineage、logs 和 failures 集合。
- **Pattern（格局）**：跨术数使用的产品级总称，包含稳定名称、识别规则、解释、来源和修订；这些部分可逐项补全。
- **TechniqueProfile**：某一术数的事实字段、规则语义、校验约束和扩展契约。
- **KnowledgeGraph**：书籍、版本、格局、主张、规则、流派和证据之间的领域关系图。
- **LineageGraph**：Artifact、Revision、运行、工具、模型、校验和人工决定之间的生产溯源图。
- **PublicationPackage**：Learn System 黑箱的唯一对外输出，包含结构化数据、原始数据、二者关系及发布清单。

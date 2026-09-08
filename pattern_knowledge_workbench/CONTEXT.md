# 领域词汇

本词汇表只定义领域对象及其边界；实现、数据库表、UI 和传输格式不在此处规定。

- **Technique**：一套可独立描述输入事实、条件语义、格局形态与论断传统的术数体系，例如七政四余、八字、紫微斗数、大六壬或奇门遁甲。
- **PatternShape**：可被识别或计算的格局形态；只描述结构，不自动携带某一流派的吉凶或解释。
- **PatternDoctrine**：某流派、著作或版本对 PatternShape 的解释性学说，包括论断、例外、优先级和争议。
- **School**：一套可标识的传承、流派或解释立场。用户选择的 School 构成主视图；其他 School 是可比较的不同观点。School 不是书籍、版本或出处。
- **Work**：有书名或稳定身份的知识作品/文献整体，可包含多 Edition。
- **Edition**：Work 的特定版本、刻本、整理本、数字副本或其他可辨别的文本实现。
- **SourceSpan**：Edition 内可被复查的连续来源位置，例如页、叶、卷、章、行、字符范围或图像区域。
- **Evidence**：支撑或反驳一项主张的可验证材料；必须能回指 SourceSpan 或其他明确来源，并保留完整性信息。
- **Assertion**：可审核、可被证据支撑或反驳的原子化知识主张；不是原文，也不是模型候选的同义词。
- **ApplicabilityRule**：声明 Assertion 在何种事实、上下文、例外和优先条件下适用的规则。
- **ReviewDecision**：对候选、主张、证据或发布内容做出的可追责决定，例如接受、驳回、退回补证或撤销。
- **ReleaseBundle**：由获批知识编译出的不可手工修改的发布集合，供消费端读取。
- **Annotation**：锚定到词条、主张、原句或扫描区域的附注；它具有作者、可见性、状态和修订语义，可为私人或公开。
- **MarkContentBinding**：把展示标记（Mark）与具体内容对象及其精确锚点绑定的关系；标记不替代内容、证据或审核决定。

这些对象必须保持分层：原文属于 SourceSpan，派生释义或论断属于 Assertion，支持关系属于 Evidence，适用边界属于 ApplicabilityRule，发布资格属于 ReviewDecision。旧原型中 `ge_ju_schools.type=book` 的记录必须迁为 Work/Edition 及其来源关系，不得继续作为目标 School；旧 `notes` 字段不等同于 Annotation 或 UserNote。

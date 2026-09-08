# 原型与发布级工作台的缺口分析

## 当前模型映射

| 原型对象 | 可保留的意图 | 发布级缺口 |
| --- | --- | --- |
| pattern | 可作为 PatternShape 候选标识 | 没有独立的形态、学说、Technique 与来源边界。 |
| rule | 可作为 Assertion / ApplicabilityRule 候选载体 | 一行混合条件、论断、解释、版本与审核状态，无法精确追溯。 |
| school | `type=school` 可映射为 School 候选 | 旧表混合 `book` 与 `school`；book 行必须迁为 Work/Edition 及来源关系，禁止把书籍继续当流派。还没有主视图、不同观点、可比条件和关键分歧规则。 |
| chapter / original_text | 可迁移为 SourceSpan 与来源文本候选 | chapter 不是可定位的来源索引；原文当前全空。 |
| conditions JSON | Condition DSL 的迁移输入 | 没有 profile、schema 版本、可重放语义或严格验证。 |
| ge_ju_versions | 版本审计的空壳 | 表中为 0，未形成可追责的修订历史。 |
| notes | 历史备注候选 | 不是 Annotation/UserNote，缺锚点、作者、可见性、审核和修订。 |

## 关键能力缺口

1. **来源与证据。** 没有 Work、Edition、可检索 SourceSpan 或原文索引；也没有 OCR PDF/PNG 的字符框、页图锚点、证据哈希和证据完整性校验。
2. **知识审核与发布。** Assertion、ApplicabilityRule、Evidence、ReviewDecision 与 ReleaseBundle 未分层；没有 KnowledgeReleaseCompiler 和 fail-closed 发布门禁。
3. **流派冲突。** 没有用户选定 School 的主视图机制，也没有在分歧改变本盘适用性/判断时优先提示关键分歧的规则。
4. **协作内容。** 缺少 Annotation、私人笔记、公开分享、BBS thread/comment/reply、like/dislike（或“彩”）及 moderation；同样缺少修订、撤销与离线同步模型。
5. **多术数边界。** 当前 schema 和页面均是七政四余单术数假设；没有 TechniqueProfile、FactSchema、profile validator、fixture 或 client projection 的扩展缝。
6. **书籍与流派身份。** 目标模型必须保证 School 不承载 Work/Edition；一本书可以记录其作者、注家或相关流派，但这些是显式关系，不是对象合并。

## 已验证的高风险行为

- 启动时会把 asset SQLite 覆盖应用文档目录，用户本地编辑可能丢失。
- 规则编辑保存及 AI 识别生成的 rule 使用 `isVerified=true`，即“保存即 verified”，绕过审核。
- `ge_ju_versions` 为 0，且没有不可抵赖的 version audit；覆盖初始化进一步破坏审计连续性。
- AI 输出直接形成可保存的候选/规则，而非先进入带来源、置信与审核状态的候选区。
- 存在静默默认值（如条件/枚举或判断回退）；无事实、无 School 或冲突未决时可能制造貌似确定的结果。
- 现有 496 条 rule 中 `original_text`、`assertion`、`brief`、`explanation`、旧 `notes` 全空，`verified=0`；仅 404 条有 conditions、486 条有 chapter，不能假设全覆盖。

## 治理结论

在 P0 完成前，此目录只能作迁移快照和探索性录入/浏览原型。任何“已验证”“可发布”“来源可查”或多术数产品声明都不成立。修复顺序必须先保护数据与来源，再建立审核发布链，随后再扩展术数和协作表层；embedding 后置。

# 工作清单

本清单的完成条件是验收门禁，不是“页面可打开”。所有项必须保留失败路径，并禁止模型或默认值绕过人工审核。

## P0：可信知识内核

- [ ] 建立 `Work`、`Edition`、`SourceSpan` 与原文索引；验收：任一发布 Assertion 可定位到版本、页/叶/行或等价连续范围，且查询可重放。
- [ ] 建立 OCR PDF/PNG 字符框与证据哈希；验收：抽样 Assertion 可从文本跳到原图区域，修改证据文件会使哈希校验失败。
- [ ] 拆分 `PatternShape`、`PatternDoctrine`、`Assertion`、`ApplicabilityRule`、`Evidence`、`ReviewDecision`；验收：原文、派生释义、模型候选和发布结论不能写入同一对象或状态。
- [ ] 分离 School 与 Work/Edition；验收：旧 `type=book` 行全部迁入作品/版本及来源关系，目标 School 表不存在书籍记录，同一作品可关联多个观点而不冒充流派。
- [ ] 修复启动覆盖数据库；验收：重启不丢用户草稿/审核记录，显式导入或重置须确认、备份并可审计。
- [ ] 取消“保存即 verified”；验收：编辑、导入和 AI 结果均以未审核候选进入队列，只有有权审核者的 ReviewDecision 可改变发布资格。
- [ ] 实现不可抵赖的版本审计与撤销；验收：每次变更保留作者、时间、前后内容和理由，历史不可被覆盖，撤销可追踪。
- [ ] 建立 `TechniqueProfile`、七政 `FactSchema` 和严格 Condition DSL；验收：非法事实/条件、无匹配和未决默认值均 fail closed，并有确定性 fixture。
- [ ] 实现 School 主视图与关键分歧门禁；验收：选定 School 优先呈现，其他流派显示为不同观点；影响适用性/判断的冲突必须首层提示。
- [ ] 集成 Learn System Pipeline；验收：来源处理、候选生成和验证结果可追溯到本工作台领域对象，不能直接进入发布区。
- [ ] 实现 `KnowledgeReleaseCompiler`；验收：只从获批对象编译 ReleaseBundle，缺来源、证据、适用规则或审核决定时编译失败。
- [ ] 实现只读 App adapter；验收：客户端只消费 ReleaseBundle，不能直接修改知识源，也不能依赖原型 SQLite 的 `verified` 字段。
- [ ] 清理并迁移 496 rule 基线；验收：报告逐条说明是否有条件、章节、原文、Assertion、证据和审核状态，未补齐项不得发布。

## P1：多术数与受控协作

- [ ] 接入八字 profile；验收：交付 FactSchema、Condition DSL、ImportAdapter、validator、fixture 和 client projection，并以“丙日干 + 亥月”验证完整召回及冲突呈现。
- [ ] 接入紫微斗数 profile；验收：交付相同六件套，fixture 覆盖宫位/四化及至少一个流派分歧。
- [ ] 接入大六壬 profile；验收：交付相同六件套，fixture 可重放起课事实与多分支判断。
- [ ] 接入奇门遁甲 profile；验收：交付相同六件套，fixture 校验局数、九宫和条件例外。
- [ ] 实现 Annotation 与私人笔记；验收：每条附注锚定词条、主张、原句或扫描区域，含作者、可见性、修订和权限；旧 `notes` 不被误当作该模型。
- [ ] 实现公开分享与 BBS thread/comment/reply；验收：公开内容、回复层级、作者和修订可审计，知识主张仍须走审核链。
- [ ] 实现 like/dislike（或“彩”）和 moderation；验收：互动计数不可替代证据或审核，违规处理及恢复均有审计。
- [ ] 实现离线同步；验收：离线改动有冲突检测、可解释合并/人工决议，且不覆盖审核和版本历史。

## P2：检索与产品强化

- [ ] 增加跨 profile 的精确检索和比较；验收：结果说明 Technique、School、Edition、条件与证据范围，不能混淆不同术数或流派。
- [ ] 在 P0/P1 稳定后评估 Embedding；验收：embedding 仅作辅助召回，精确条件、来源跳转、审核状态和 ReleaseBundle 门禁仍由确定性链路决定。

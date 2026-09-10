# Learn System 项目冷启动交接

更新时间：2026-09-10  
仓库：`/Users/jingtaiwei/Git/Public/learn_system`  
分支：`codex/docs/knowledge-compilation`  
当前 HEAD：`ffe19df`  
当前主线状态：`G3_REWORK_REQUIRED`；G3 通过前禁止进入 G4

## 1. 冷启动顺序

1. 完整阅读 `AGENTS.md`、本文件、`HANDOFF.md`、`PLAN.md`。
2. 运行 `git status --short`、`git log --oneline -12`；保留所有并行工作，不 reset、clean、stash、切分支或批量暂存。
3. 当前第一优先级是关闭 G3 剩余三类假绿。用户要求主 Agent只写执行 Prompt 和做独立验收，不亲自修改实现。
4. 执行 Agent只允许修改 `verify-T.sh` 与 `mutations.sh`；完成后必须由不同的只读 Agent加主 Agent矩阵外盲测。

完成标准：后任无需聊天记录即可说明项目目标、模块关系、当前阻断、下一任务和验收门禁。

## 2. 最终产品目标

Learn System 是单人单机运行、未来可扩展的文献知识编译黑箱：

```text
原始资料
 -> 黑箱［识别、校正、切分、提取、交叉校验、人工审核、编译］
 -> 可发布数据集 + 原始资料/受控引用
 -> APP 后端
 -> 客户端［排盘检索、经典阅读、原文定位、私人/公开笔记与讨论］
```

冻结原则：

- 黑箱的产品是可下发客户端的 `PublicationPackage`，不是在线服务。
- M1～M8 每阶段的输入、输出、运行、人工决定、失败和血缘全部留存，可恢复、可重跑、可追溯。
- 以一本书或 `EditionPart` 为 Gate 单位；当前阶段全部完成才进入下一阶段。
- 影印本走 OCR，EPUB/TXT/Markdown 走原生文本入口，两轨在 M3 后汇合。
- Work 与 Edition 分离；同书多个刻本/抄本逐次增加、互不覆盖。
- 完整证据链为 `KnowledgeEntry -> Assertion -> EvidenceLink -> SourceSpan -> SourceAnchor -> 页图/字框 -> SourceAsset`。
- 当前可发布 SQLite/文件包，但 Canonical 数据必须能无损投影到 Graph/RAG。
- Embedding 和移动端 AI 检索暂缓；确定性格局匹配使用版本化 FactSet 与声明式规则。
- 当前单人使用，不实现身份验证，只保留未来线上化接口。
- Pattern/格局是跨技法总称；官方数据来自黑箱，未来允许用户创建私有或公开内容。
- 注解社区消费黑箱输出，不属于 M1～M8 内部；必须稳定锚定知识与原文对象。

权威入口：

- `openspec/learn-system-blackbox-architecture.md`
- `knowledge_system/LEARN_SYSTEM_TARGET.md`
- `openspec/legacy-storage-transition.md`
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md`
- `knowledge_system/CROSS_TECHNIQUE_ONTOLOGY.md`
- `tag_system/TAG_SYSTEM_DESIGN.md`

## 3. 模块与工作线现状

### 黑箱 G1～G4

- G1：内核与 L0 契约完成。
- G2：工作台 R0 数据安全完成；内网 `ai_core` 已剥离，持久化与 verified gate 已恢复。
- G3：主体转录完成；验证器仍有三类假绿，状态为 `REWORK_REQUIRED`。
- G4：执行引擎、Ledger、Orchestrator 等后续契约；被 G3 阻断。

### OCR 与 Pipeline

- 传统竖排古籍 OCR 已有 FastAPI + Vue 校正工具，不另造通用 OCR UI。
- OCR 参数必须按书/版式建立 Profile；M2 保留机器结果、人工校正、异常页和字框证据。
- 《三辰通载》样例修复记录见 `ocr/HANDOFF_OCR_FIXES.md`。
- M3 做边界切分与语义确认；M4 分角色抽取并交叉校验；M5 只做 Validator；M6 是 Review Console；M7 增量合并；M8 编译发布包。

### Pattern 工作台

- `pattern_knowledge_workbench/` 从七政伴生系统提升为跨技法原型。
- 现有约 496 条 rule 多为空结构，原文、解释、证据和审核不足，不能当生产数据集。
- 必须支持同一 Pattern 下多书、多流派、多主张和相反观点。

### 注解社区

- 目标包括原句评论、回复、点赞/点彩、私人笔记、公开分享、经典阅读和讨论。
- 社区数据通过稳定知识/原文锚点连接，不回写 Canonical 官方知识。
- 当前规格位于 `openspec/annotation-community/`；该线与 G3 并行，状态以 `HANDOFF.md`、`PLAN.md` 为准。
- HEAD 已包含 NC-001 准备和 v1.5 文档工作；文档完成不等于业务实现完成。

## 4. G3 已验证事实

提交 `ffe19df` 只改了：

- `docs/blackbox-spec-rework/verify-T.sh`
- `docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh`

主 Agent 与两个只读 Agent独立实跑：

- 正常规格：exit 0，`FAIL 合计: 0`。
- selftest：`37/37`。
- D-07：`30/30 rejected`。
- T-07：`26/26 rejected`。
- T-08：`42/42 rejected`。
- 总计：`98/98 rejected`。
- 98 例均真实改变独立临时副本，无 no-op、叠加或 `MUTATION_NOT_APPLIED`。
- 精确 FAIL ID、FF/VT 规范化和实际 Package 多重集已经修复。
- `git diff --check ffe19df^ ffe19df` 通过。

以上只证明固定 98 项通过；新的盲测证明 G3 尚未通过。

## 5. 当前三个阻断

### R5-1：D-07 START 间隙未封闭

`verify-T.sh` 的 `g3_d07_items()` 遇空行或非列表行停止，未检查到下一个 START 之间的剩余内容。以下两项仍 exit 0：

- TP 四条正确项后隔空行追加冲突 bullet，再出现 QC START。
- 同处追加“客户端仍可绕过 TechniqueProfilePack，使用任意自由字段参与确定性匹配。”。

必须按完整区域封闭：TP START 至 QC START 前、QC START 至 RI START 前、RI START 至 `### 16.2` 前。区域只能包含 START、固定有序条目和空行。

### R5-2：T-07 不拒绝额外列

正确表格行尾追加 `| 冲突附加值 |` 仍 exit 0。15 个数据行必须与硬编码 canonical 完整行逐字规范化相等、各一次，并同时校验行数、列数、key 和 value。

### R5-3：T-08 不拒绝重复标题

B3 正确块后、`#### 16.3.2` 前再加入同名 B3 标题仍 exit 0。B1/B2/B3 精确标题必须在 §16.3.1 各出现一次，然后才解析内容。

## 6. 下一位执行 Agent 的机械任务

只改上述两个脚本：

1. 先新增四个永久 Red：D-07 空行后冲突 bullet、D-07 空行后冲突段落、T-07 行尾第三列、T-08 重复 B3 标题。
2. 在 `ffe19df` 上保存四项当前假绿证据。
3. 按 §5 修复封闭边界，不增加否定词黑名单。
4. 保持原 98 项；新分母至少为 D-07 `32`、T-07 `27`、T-08 `43`、总计 `102`。若重复标题两个位置分别建例，分母相应增加，报告必须与真实脚本一致。
5. 仅提交两个授权脚本，建议消息：`fix: close final G3 region boundary bypasses`。
6. 等待独立验收，不启动 G4。

## 7. 后任验收门禁

```bash
bash docs/blackbox-spec-rework/verify-T.sh
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh selftest
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh d07
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t07
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh t08
bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all
git diff --check <parent> <fix-commit>
git diff --name-only <parent> <fix-commit>
```

主 Agent还要新增至少 5 个矩阵外盲测，覆盖 D-07 三段间隙、T-07 额外列/声明、T-08 任意重复标题/块外内容、FAIL ID 超集和 Package 名控制字符。

通过条件：正常规格 0 FAIL；固定矩阵全部 rejected；盲测全部非零且命中指定完整 FAIL ID；提交仅两个授权脚本；无跳过、no-op 或范围外修改。

## 8. 当前工作树与所有权

当前工作树有并行改动，后任必须重新运行 `git status --short`：

- 未提交的 `docs/blackbox-spec-rework/work-items/g3-r3/` 是早期 89 例草稿，落后于 98 例实现，不得作为现行执行入口。
- `docs/blackbox-spec-rework/reviews/NC-001-REVIEW-R1.md` 与 `nc001_r1_guard.sh` 属于其他工作线，不得纳入 G3。
- 根 HANDOFF、PLAN、总 TODO 和 G3 review 有协调改动；先查 diff 和所有权，不批量覆盖。
- G3 执行 Agent只能显式暂存两个脚本，不使用 `git add -A`。

## 9. 禁止重走

- 固定矩阵全绿不等于结构封闭。
- 不扩展自然语言否定词列表；验证封闭结构。
- 不从待测 `$SPEC` 生成 expected。
- 不用 `sort -u` 隐藏重复 Package。
- 不用 `[[:space:]]` 做冻结规范化。
- 不只检查正确行存在；同时检查归属、唯一性和区域内无额外内容。
- subagent 自述不是验收；主 Agent必须复跑并做矩阵外盲测。

## 10. 交接结论

无需推倒重来。`ffe19df` 已关闭上一轮大部分漏洞，只剩 §5 三类边界问题。后任做小范围 R5 修补和独立验收；G3 通过前保持 `REWORK_REQUIRED`，G4 不启动。

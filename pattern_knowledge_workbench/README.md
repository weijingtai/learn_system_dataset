# pattern_knowledge_workbench

多术数格局知识审核与发布工作台。它面向多种术数的、可追溯且须经审核的格局知识；七政四余只是第一个 `TechniqueProfile`，不是本项目边界。

## 定位与非目标

本项目的目标是把来源材料、结构化事实、条件化主张、证据、流派观点与审核决定组织为可发布的知识包，并为 App 提供只读投影。知识必须经确定性校验和人工审核；`ReleaseBundle` 由编译器生成，禁止手工编辑。

当前目录保留的是原样迁移的 Flutter 原型快照，而不是发布级知识系统。它目前只支持七政四余的单术数格局录入、浏览、条件 JSON 编辑、导入及 AI 辅助候选；不能据此宣称具备多术数、来源可追溯、审核发布、协作社区或生产级数据安全能力。

非目标包括：替代排盘/推演引擎、让模型输出直接成为知识、复制五套技术各异的 UI，或把私人笔记直接发布为公共知识。

## 当前数据基线

迁移资产 `assets/ge_ju_database.sqlite` 中有 496 条 pattern 与 496 条 rule；404 条 rule 有 conditions，486 条有 chapter。`original_text`、`assertion`、`brief`、`explanation`、旧 `notes` 均为空；`is_verified=1` 为 0；`ge_ju_versions` 为 0。它是待治理的录入基线，不能被当作已验证语料。

特别注意：旧 rule 的 `notes` 是遗留扁平字段，**不是** `Annotation`，也不是 `UserNote`；它没有锚点、作者、可见性、审核、修订或证据语义。

## 目标数据流

```text
Work / Edition / SourceSpan → Evidence → Assertion + ApplicabilityRule
  → ReviewDecision → KnowledgeReleaseCompiler → ReleaseBundle → App adapter
```

模型只能在该流中提供候选（例如 OCR、拆分、抽取或条件建议）；候选必须绑定来源和证据，并通过 validator 与审核决定后才可进入发布包。

## 流派与冲突

用户选择的 `School` 是 App 主视图：其观点优先呈现。其他流派并列为“不同观点”，而不是静默合并或覆盖。若观点分歧改变当前盘的适用性或判断，第一层界面必须显示关键分歧；用户可再展开来源、证据、条件和完整理由。没有选定 School、没有可比条件或冲突未审核时，不得伪造默认结论。

## 目录

- `lib/`：原样迁入的 Flutter 原型；不是目标领域模型的权威实现。
- `assets/ge_ju_database.sqlite`：七政四余原型数据库基线。
- `assets/ge_ju_condition_spec.md`：原型条件表达说明。
- [CONTEXT.md](CONTEXT.md)：跨术数领域词汇。
- [EXTENSION_PLAN.md](EXTENSION_PLAN.md)：通过 profile 扩展新术数的边界。
- [GAP_ANALYSIS.md](GAP_ANALYSIS.md)：原型与发布级目标之间的缺口和风险。
- [TODO.md](TODO.md)：按优先级及可验收条件排列的工作清单。
- [MIGRATION.md](MIGRATION.md)：迁移证明和快照边界。

## 运行要求与当前阻断

需要 Flutter/Dart SDK 以及各平台构建工具。依赖解析目前被两个私有内网 Git 依赖阻断：`ai_core`（`xuan-ai.git`）与 `enumeration`（`enumeration.git`），地址均位于 `192.168.0.165:3000`。没有该网络权限与凭据时，`flutter pub get`/运行不保证可用；不要以下载或编译失败推断数据模型已经被验证。

## 五分钟上手

1. 先读本文件、[CONTEXT.md](CONTEXT.md)、[GAP_ANALYSIS.md](GAP_ANALYSIS.md) 与 [TODO.md](TODO.md)。
2. 检查私有依赖可达后，在本目录执行 `flutter pub get`。
3. 仅为了解原型时执行 `flutter run`；不要把运行结果当作发布级验收。
4. 浏览 pattern/rule 与条件 JSON，记录问题时区分来源事实、模型候选和产品展示需求。
5. 任何数据治理改动先走 `Work → Edition → SourceSpan → Evidence → Assertion → ReviewDecision`，再交由编译器生成 App 可读包。

## 数据安全警告

当前代码会在启动时把 asset SQLite 覆盖到应用文档目录。故原型界面的本地编辑可能在下次启动丢失；不要用它保存唯一的工作成果、审核结论、私人笔记或待发布资料。导入、编辑和 AI 结果在有版本审计、备份、权限与离线同步方案前均须视为不可信草稿。

## 文档地图

从术语开始读 [CONTEXT.md](CONTEXT.md)，再看 [EXTENSION_PLAN.md](EXTENSION_PLAN.md) 理解为什么不复制 UI；用 [GAP_ANALYSIS.md](GAP_ANALYSIS.md) 判断当前原型不能承担什么；按 [TODO.md](TODO.md) 的验收条件实施；需要复核迁移资产时看 [MIGRATION.md](MIGRATION.md)。

## AI agent 开工顺序

1. 阅读本 README、`CONTEXT.md`、`GAP_ANALYSIS.md`、`TODO.md`、`MIGRATION.md`，并保留快照边界。
2. 先实施 P0 的来源、证据、审核、版本和数据覆盖保护；不得先做新 UI 或 embedding。
3. 为每个 `TechniqueProfile` 建立 schema、DSL、导入、校验和 fixture，再写 client projection。
4. 以 `KnowledgeReleaseCompiler` 的确定性输出作为 App adapter 输入；AI 只写候选区。
5. 每项变更都验证失败路径，确保没有默认值、保存动作或模型输出绕过审核。

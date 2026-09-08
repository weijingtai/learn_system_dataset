# 迁移记录

## 身份与日期

- 正式目标路径：`/Users/jingtaiwei/Git/Public/learn_system/pattern_knowledge_workbench`
- 原始路径：`/Users/jingtaiwei/Git/Public/xuan-migration/xuan-qizhengsiyu/companion_system`
- 迁移日期：2026-09-08
- 原样快照提交：`4ca1a73`（`feat: import pattern knowledge workbench`）

该迁移先建立物理复制的原样基线，再修改 README 并增加五份治理文档；因此当前目录比源快照多五个文件，README 内容也已升级。原样代码和数据保存在 Git 提交 `4ca1a73`，不是完成重构或质量认证。正式名称为 `pattern_knowledge_workbench`（多术数格局知识审核与发布工作台）；目录中保留的 `companion_system` 包名、代码和历史说明属于快照遗留，不能用于缩小项目边界。

## 复制基线

- 复制瞬间：179 个普通文件、1,827,975 bytes、0 symlinks；逐文件相对路径、类型、内容和 SHA-256 全部一致。
- 初次复制核验记录为 84 个目录（含根）；后续复核发现其中八个是无文件内容的 Xcode `swiftpm/configuration` 临时空目录，移除后源和目标均为 76 个目录（含根）。空目录不属于 Git 内容资产。
- 复制 manifest SHA-256：`ee73da5fb4f49fa8d229a995d3762717e1f68a98e48a7cd582e91b80dd3febfa`。生成口径为：按相对路径排序，为复制瞬间的每个对象记录对象类型；普通文件同时记录 SHA-256，符号链接记录 link target。
- 迁移后治理增量：重写 `README.md`，新增 `CONTEXT.md`、`EXTENSION_PLAN.md`、`GAP_ANALYSIS.md`、`TODO.md`、`MIGRATION.md`。最终删除源目录前，按“源快照文件 + 上述治理增量”验收，不再错误要求 README 与源快照逐字相同。
- SQLite：`assets/ge_ju_database.sqlite`，450,560 bytes，SHA-256 `1f25a9304d6b88394f495267d371ea7566ca19de431026b3c79b13340111c764`

SQLite 表计数：`ge_ju_patterns=496`、`ge_ju_rules=496`、`ge_ju_categories=10`、`ge_ju_schools=3`、`ge_ju_versions=0`。其中 rule 的非空 `conditions=404`、`chapter=486`；`original_text`、`assertion`、`brief`、`explanation`、旧 `notes` 均为 0，`is_verified=1` 为 0。

## 本机文件说明

`android/local.properties` 是机器本地 Android 配置，受 `android/.gitignore` 排除；迁移时曾物理复制以保持原始工作树状态，但不会成为 Git 追踪资产，也不应被共享、以其为构建前提，或填入文档示例。

## 使用边界

迁移快照可用于复查历史界面、条件数据和数据库行为。它不能替代 Work/Edition/SourceSpan/Evidence/Assertion/ReviewDecision/ReleaseBundle 的目标链路；尤其旧 `notes` 不是 Annotation 或 UserNote，空版本表也不是版本审计。后续改造必须保留此证据基线，并从获批知识重新编译发布物，而非手改 ReleaseBundle。

## 源目录清理

2026-09-08，在两次独立逐文件核验、SQLite `integrity_check`、规格复审、文档质审和 Learn System 快照提交完成后，原始 `companion_system` 目录按用户授权删除。删除后复核：原路径不存在；目标目录为 184 files / 76 dirs，机器本地 `android/local.properties` 仍存在；SQLite SHA-256 仍为上述值且完整性为 `ok`。源父仓库显示 175 个受 Git 跟踪文件被删除，未在该仓库提交；完整原样快照可由 Learn System 提交 `4ca1a73` 恢复。

# 笔记、原句注解与讨论 Implementation Plans

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（获得派发授权后）或 superpowers:executing-plans 逐项执行；必须遵守本仓库工作包 READY 门禁，不能从本总计划直接开始业务实现。

**Goal:** 交付可离线编辑、保留历史、私密同步备份、显式发布与真实讨论通知的 Flutter/Python 笔记系统。

**Architecture:** 独立学习领域模型消费只读书籍包，复用 Social、Notification、Storage 与 Repository。私人密文链和公共发布链隔离，原书与 Tooltip 共用讨论。

**Tech Stack:** Flutter、flutter_markdown_plus、Drift、现有 Repository/Storage；Python Firebase Functions、Firestore、对象存储；REST/OpenAPI 3.1/Swagger。

版本：1.0；2026-09-10。状态：`IMPLEMENTATION_PLAN`，尚非执行包 READY。依据：[PRD](PRD.md)、[Design](DESIGN.md)、[Tasks](TASKS.md)；准出规则：[工作包门禁](../subagent-delivery-gate.md)。

## 1. 目录与文件职责

以下为精确根路径约定，不是 Shell 环境变量。外部项目本轮只读，不创建或修改；代码实施前 NC-001 记录其各自工作树、AGENTS 与权限。

| 标记 | 根路径 | 文件职责 |
|---|---|---|
| SPEC | `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community` | 四份需求/设计/计划/任务文档及后续契约冻结记录 |
| CLIENT | `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（拟新建） | Flutter 学习功能包；NC-001 核实是否已有等价包后冻结，不能当作现有目录 |
| SERVER | `/Users/jingtaiwei/Git/Public/xuan-server/functions-py` | 既有 Python 服务；新增 `xuan/handlers/community_*`、领域服务与对应测试 |
| STORAGE | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage` | 通道/加密/备份驱动和公共端口，不放笔记 UI |
| SOCIAL | `/Users/jingtaiwei/Git/Public/xuan-migration/social` | 复用关系/私信/候选/交互组件；缺目标适配才局部修改 |
| NOTIFICATION | `/Users/jingtaiwei/Git/Public/xuan-migration/notification` | 稳定管线及接入契约；业务适配优先放 CLIENT/SERVER |
| REST | `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter` | HTTP 约定及权威 OpenAPI 入口，修正必要结构并加入社区资源 |
| PACK | `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items` | 按既有门禁生成 nc-xxx 工作包，不另造一套工作包规范 |

NC-001 可决定复用已存在等价包而非新增 CLIENT，但必须先回写此表和所有任务路径，不能带着两个可能位置派发。已核实 `xuan-migration/learn_system` 无 Flutter pubspec/lib/test，不可直接作为 CLIENT。现有 `notebook` 是排盘图元模型，不当作永久笔记修订库。

CLIENT 拟分工：`domain/` 定义笔记与修订；`persistence/` Drift 和 outbox；`editor/` 编辑、撤销、保存；`community/` 发布/讨论/互动；`storage/` 密文 mapper；`notifications/` 宿主适配；`reader/` 来源锚点；`example/` 提供独立运行的 Flutter 验收宿主与 Tooltip 原型。宿主连接通过注入账号、API、关系/IM 导航与存储端口，不修改排盘子模块。

## 2. 并行工作流与依赖顺序

| 阶段 | 任务 | 可以准备的工作 | 退出条件 |
|---|---|---|---|
| P0 契约与选址 | NC-001～003 | 实际文件映射、依赖版本、非书籍领域契约、OpenAPI | 输入唯一、正反 fixture 明确、真正规范验证通过 |
| P1 独立本地笔记 | NC-004～007 | Drift 修订、Markdown 编辑、Undo/Redo、历史冲突 | 真文件重启恢复；IME/撤销/自动保存测试；不依赖书籍 |
| P2 媒体与公开社交 | NC-008～012 | 私人图片本地引用、发布权限、页面、评论/互动 | 两账号真实 HTTP；私改不公开；收回不泄漏；计数幂等 |
| P3 通知 | NC-013～014 | outbox/delivery API、Notification 与导航 | 回复/@ 去重、失败补拉、可靠 ACK、点击定位 |
| P4 同步与备份 | NC-015～019 | 密钥协议先行、P2P/云网关/恢复/删除 | 两设备真实链路及全设备丢失恢复；删除无复活 |
| P5 书籍与 Tooltip | NC-020～023 | 上游政策/Schema 后接导入、阅读、原句与原型 | 真实样例精准选区、跨版解释、两入口同讨论 |
| P6 总验收 | NC-024 | 全链路及文档/任务核对 | 全部本期 R 项证据齐全；未完成不包装成全部交付 |

P4 的协议设计、P5 的上游协调可与 P0/P1 并行准备；它们不阻断纯文本本地笔记。P2 公共图片发布需 NC-008 的资源接口，私人云图片需 P4。P3 依赖评论事务和正式通知契约。NC-019 的清理依赖云备份，不能只做本地软删后宣布删除全链完成。

各阶段是分别可验证的纵向结果，不意味着可以取消其他本期功能。P1 通过可称“本地笔记阶段通过”，不能称“整套笔记系统完成”。

## 3. 每个任务如何成为可执行工作包

Tasks 中 NC-xxx 是有范围和验收点的工作项；体积较大时拆为多个 30–60 分钟 ACT，按 client/server/协议分别限制写入范围，不让一个执行 Agent 同时自由修改所有子模块。

- [ ] 根据任务条目读取指定源码，记录 git 基线、真实目录、SDK、当前既有失败；不修改其他工作树。
- [ ] 生成 `PACK/nc-xxx/README.md`：需求 ID、目标、文件白名单、禁止项、依赖及失败停点。
- [ ] 生成 `BDD.md`：至少一条正常行为、失败/缺依赖行为、回归风险；必须可从数据或 UI 观察。
- [ ] 生成 `TDD.md`：每个失败 fixture、精确测试名/文件、命令、退出码、前后期望。Schema 先负例，代码先失败测试，不让执行者自行解释验收口径。
- [ ] 生成 `ACT.yaml` 或有序 `act/01.yaml`：逐步 Red → 最小实现 → Green → 必要回归 → 小提交；禁止临时扩功能或换依赖。
- [ ] 生成 `PROMPT.md` 与 `ACCEPTANCE.md`，经 wjt-react 审查后才将 Tasks 状态变 READY。
- [ ] 派发后收取 commit、文件差异、命令原始结果、跳过项；主 Agent 独立复核关键行为才标 ACCEPTED。

本轮只交付四份总文档，不假称这些六件套或其 READY 已存在。普通 Tasks 勾选不代替工作包准出。

## 4. 验证命令与环境分层

| 环境 | 命令基线（在对应根目录） | 证据用途 |
|---|---|---|
| SPEC 所在仓库 | `git diff --check`，需求/任务映射、链接与占位符扫描 | 文档一致性；不能证明业务可用 |
| CLIENT | `flutter test test/...`，`flutter analyze` | 模型/Widget/Drift 测试；精确文件见 Tasks |
| SERVER | `python3 -m pytest tests/test_community_*.py -q` | 领域和 handler 测试，工作包须替换通配为其精确范围 |
| REST | 既有测试加真正 OpenAPI 验证命令 | NC-003 固定工具/版本/离线策略，禁止只检查 YAML 字段 |
| example/真实后端 | `flutter test integration_test/... -d <实际设备ID>` | 工作包将设备 ID/后端环境记录为实值；占用端口、账号和凭据通过受控配置注入 |

测试文件列为“拟新增”时，在对应任务产出前不能声称该命令已通过。云/设备验收使用受控测试账号和独立命名空间，记录环境版本，不将凭据或私人正文写入证据。Fake 单测与真云联调分别报告。

## 5. 首批准备顺序

1. NC-001 实际客户端位置与端口装配；不需要用户重新讨论产品范围。
2. NC-002 本地/公共模型契约与正反 fixture；书籍 AnchorRef 只引用待冻结边界，不自建影子模型。
3. NC-004 的本地修订与 NC-005/006 的编辑器/撤销工作包；同时准备 NC-003 公共 API。
4. 并行准备 NC-015 密钥恢复方案、NC-020 上游政策/Schema 工作项，完成后解锁依赖实现。

先解决目录与接口，不先开工再从 UI 反推数据库。用户已确认自动保存、回收站、图片与撤销规则，无需再作为产品问题阻断准备。

## 6. 风险、退路与范围约束

- 书籍未交付：独立笔记继续，源句和真实来源 Tooltip 保持 BLOCKED，不用模糊文本匹配假装通过。
- 密钥协议未定：可测试本地加密组件，跨设备恢复保持 BLOCKED；不降级明文云备份。
- 云环境不可用：保留离线稿/待发操作，报告验收未执行；不以 Fake 替代生产链路。
- 原公共媒体不可撤权：新增受控访问适配，不能降低用户已确认的隐私要求。
- 现有 OpenAPI/通知文档矛盾：按源码记录事实，在对应契约任务修正并验证，不整体重写旧模块。
- 完整键盘方案：明确 F-01，保持 BACKLOG，不在本期新增更多快捷键设计。

## 7. 交付与完成

最终交付包括 Flutter 功能包/可运行验收宿主、Python handlers 与存储规则/索引、同源 OpenAPI/Swagger、迁移与配置说明、BDD/TDD/ACT、真实链路证据和使用说明。所有 R-01～R-20 在 Tasks 有映射；F 项独立后续登记，不混入本期通过率。

任务状态由主 Agent 更新；跨仓库提交各自保留，记录对应版本组合，禁止主 Agent 擅自合并到 main/master。本设计文档输出完成不等于业务开发完成。

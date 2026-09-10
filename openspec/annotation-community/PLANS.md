# 笔记、原句注解与讨论 Implementation Plans

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（获得派发授权后）或 superpowers:executing-plans 逐项执行；必须遵守本仓库工作包 READY 门禁，不能从本总计划直接开始业务实现。

**Goal:** 交付可离线编辑、保留历史、私密同步备份、显式发布与真实讨论通知的 Flutter/Python 笔记系统。

**Architecture:** 独立学习领域模型消费只读书籍包，复用 Social、Notification、Storage 与 Repository。私人密文链和公共发布链隔离，原书与 Tooltip 共用讨论。

**Tech Stack:** Flutter、flutter_markdown_plus、Drift、现有 Repository/Storage；Python Firebase Functions、Firestore、对象存储；REST/OpenAPI 3.1/Swagger。

版本：1.3；2026-09-10（R2 六项返工补全；待独立复核）。状态：`APPROVED_DESIGN`；执行状态：`NOT_STARTED`，尚非执行包 READY。
依据：[PRD](PRD.md)、[Design](DESIGN.md)、[Tasks](TASKS.md)；准出规则：[工作包门禁](../subagent-delivery-gate.md)；审查缺陷登记：[REVIEW_R1](REVIEW_R1.md)。

## 1. 目录与文件职责

以下为精确根路径约定，不是 Shell 环境变量。

**「只读」的准确范围（R1 修订，原表述自相矛盾）：** 本轮＝四份文档交付轮次，在此轮内不修改任何外部仓库。进入 NC 执行阶段后，SERVER/STORAGE/SOCIAL/NOTIFICATION/REST **均需写入**，写入范围由 §1.2 的 `SCOPE.WRITE` 白名单逐任务限定，不存在「全程只读」。代码实施前 NC-001 记录各自工作树、AGENTS、当前 HEAD、当前测试基线与是否允许写入。

| 标记 | 根路径 | 文件职责 |
|---|---|---|
| SPEC | `/Users/jingtaiwei/Git/Public/learn_system/openspec/annotation-community` | 四份需求/设计/计划/任务文档及后续契约冻结记录 |
| CLIENT | `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`（拟新建） | Flutter 学习功能包；NC-001 核实是否已有等价包后冻结，不能当作现有目录 |
| SERVER | `/Users/jingtaiwei/Git/Public/xuan-server/functions-py` | 既有 Python 服务；新增 `xuan/handlers/community_*`、领域服务与对应测试 |
| STORAGE | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage` | 通道/加密/备份驱动和公共端口，不放笔记 UI |
| SOCIAL | `/Users/jingtaiwei/Git/Public/xuan-migration/social` | 复用关系/私信/候选/交互组件；缺目标适配才局部修改 |
| NOTIFICATION | `/Users/jingtaiwei/Git/Public/xuan-migration/notification` | 稳定管线及接入契约；业务适配优先放 CLIENT/SERVER |
| REST | `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter` | HTTP 约定及权威 OpenAPI 入口，修正必要结构并加入社区资源 |
| NOTIFIER | `/Users/jingtaiwei/Git/Public/xuan-server/notifier` | 独立 Go 推送服务，持有权威 `api/openapi.yaml`（**3.0.3**）与 `docs/OPENSPEC-PUSH-CELL.md` 冻结口径。**本轮及后续均只读**，只引用不复制契约正文 |
| PACK | `/Users/jingtaiwei/Git/Public/learn_system/docs/blackbox-spec-rework/work-items` | 按既有门禁生成 nc-xxx 工作包，不另造一套工作包规范。既有包用 `t01/d02/act01` 命名，`nc-` 是本线新前缀而非既有系列延续；六件套格式与 gate §2 完全一致 |

NC-001 可决定复用已存在等价包而非新增 CLIENT，但必须先回写此表和所有任务路径，不能带着两个可能位置派发。已核实 `xuan-migration/learn_system` 无 Flutter pubspec/lib/test，不可直接作为 CLIENT。现有 `notebook` 是排盘图元模型，不当作永久笔记修订库。

CLIENT 拟分工：`domain/` 定义笔记与修订；`persistence/` Drift 和 outbox；`editor/` 编辑、撤销、保存；`community/` 发布/讨论/互动；`storage/` 密文 mapper；`notifications/` 宿主适配；`reader/` 来源锚点；`example/` 提供独立运行的 Flutter 验收宿主与 Tooltip 原型。宿主连接通过注入账号、API、关系/IM 导航与存储端口，不修改排盘子模块。

### 1.2 写入所有权与共享文件串行顺序

gate §3.2 第 8 条要求 PROMPT 含允许/禁止范围。每个 NC 的 `SCOPE.WRITE` 在其工作包 README 中给出精确文件白名单；本节固定跨任务的共享约束。

**同一文件被多个任务写入时的串行顺序（后继任务必须以前一个的产出为基线重跑契约测试）：**

| 共享文件 | 写入顺序 | 说明 |
|---|---|---|
| `REST/openapi/openapi.yaml` | NC-003 → NC-013 → NC-017 → NC-021 | 唯一 3.1 权威入口；`NOTIFIER/api/openapi.yaml` 全程只读 |
| `REST/test/openapi_validation_test.dart` | NC-003（唯一） | 该文件现有 8 处断言要求非法的 operation 级 `headers:`，修正结构必然弄红；必须进入 NC-003 白名单并在 README 记录改前基线 |
| `SERVER/tests/conftest.py` | NC-009 → NC-011 → NC-012 → NC-013 → NC-017 → NC-019 → NC-021 | **仅允许向 `COLLECTIONS` 追加键**，不得修改其他内容。该文件此前不在任何任务白名单内，会导致新增社区集合无法清理、用例互相污染 |
| `SERVER/xuan/config.py`、`SERVER/main.py` | NC-009 → NC-013 → NC-017 → NC-021 | 仅追加路由/配置注册 |
| `SPEC/contracts/`、`SPEC/fixtures/` | NC-002 → 各消费任务只读 | 消费任务不得修改 fixture 以迁就实现 |

**跨仓库任务的 ACT 拆分：** 一项涉及多仓库时，六件套须拆为有序 ACT，每个 ACT 只持有一个仓库的写入权。其他 Agent 的改动不得回退。

## 2. 并行工作流与依赖顺序

| 阶段 | 任务 | 可以准备的工作 | 退出条件 |
|---|---|---|---|
| P0 契约与选址 | NC-001～003 | 实际文件映射、依赖版本、非书籍领域契约、OpenAPI | 输入唯一、正反 fixture 明确、真正规范验证通过 |
| P1 独立本地笔记 | NC-004～007 | Drift 修订、Markdown 编辑、Undo/Redo、历史冲突 | 真文件重启恢复；IME/撤销/自动保存测试；不依赖书籍 |
| P2 媒体与公开社交 | NC-025, NC-008～012 | 私人图片本地引用、发布权限、页面、评论/互动 | 两账号真实 HTTP；私改不公开；收回不泄漏；计数幂等 |
| P3 通知 | NC-013～014 | outbox/delivery API、Notification 与导航 | 回复/@ 去重、失败补拉、可靠 ACK、点击定位 |
| P4 同步与备份 | NC-015～019 | 密钥协议先行、P2P/云网关/恢复/删除 | 两设备真实链路及全设备丢失恢复；删除无复活 |
| P5 书籍与 Tooltip | NC-020a/b～023 | 上游政策/Schema 后接导入、阅读、原句与原型 | 真实样例精准选区、跨版解释、两入口同讨论 |
| P6 总验收 | NC-024 | 全链路及文档/任务核对 | 全部本期 R 项证据齐全；未完成不包装成全部交付 |

P4 的协议设计、P5 的上游协调可与 P0/P1 并行准备；它们不阻断纯文本本地笔记。P2 公共图片发布需 NC-025 的生产 BlobGateway 与 NC-008 的资源接口——现有 firebase 实现是自述的内存 fake，没有 NC-025 就没有任何真实公共媒体链路；私人云图片需 P4。P3 依赖评论事务和正式通知契约。NC-019 的清理依赖云备份，不能只做本地软删后宣布删除全链完成。

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

| 环境 | 命令基线（在对应根目录） | 前置环境（缺失即「未执行」而非「失败」） | 证据用途 |
|---|---|---|---|
| SPEC 所在仓库 | `git diff --check`；`bash openspec/annotation-community/verify.sh` | 无 | 文档一致性；不能证明业务可用 |
| CLIENT | `dart run build_runner build --delete-conflicting-outputs`（测试前置，其失败不计为业务红测）；`flutter analyze`；`flutter test test/...` | Flutter/Dart/drift/drift_dev/build_runner 精确版本由 NC-001 冻结；CLIENT 根路径目前**不存在**，NC-001 完成前所有 flutter 命令不可执行 | 模型/Widget/Drift 测试；精确文件见 Tasks |
| SERVER | `python3 -m pytest tests/test_community_*.py -q` | **必须有 Firestore/Auth Emulator**：`functions-py/tests/conftest.py` 强制 `FIRESTORE_EMULATOR_HOST=192.168.0.165:8080`、`FIREBASE_AUTH_EMULATOR_HOST=192.168.0.165:9099`、`GCLOUD_PROJECT` 由 NC-001 记录实值。Emulator 不可达时该命令视为**未执行**，与业务未实现的失败必须区分 | 领域和 handler 测试，工作包须替换通配为其精确范围 |
| REST | `dart test test/community_openapi_contract_test.dart`；`tool/validate_openapi openapi/openapi.yaml` | 验证器名称/版本/安装方式由 NC-001 指定实值；`repository_contract_kernel` 走局域网 Gitea `http://192.168.0.165:3000`，离线时依赖 `dependency_overrides` 本地路径 | NC-003 固定工具/版本/离线策略，禁止只检查 YAML 字段 |
| example/真实后端 | `flutter test integration_test/... -d <实际设备ID>` | **设备清单与测试后端由 NC-001 的 `INTEGRATION_BASELINE.md` 提供**（此前 NC-016/018/023 引用了 NC-001 从未承诺的产物）：设备表含 device_id/平台/系统版本/是否可作 P2P 对端；后端表含 project_id、命名空间前缀 `nc_<日期>_<短哈希>`、测试账号 uid ↔ app_user_id 对、凭据注入方式 | 真实链路证据 |

测试文件列为「拟新增」时，在对应任务产出前不能声称该命令已通过。云/设备验收使用受控测试账号和独立命名空间，记录环境版本，不将凭据或私人正文写入证据。Fake 单测与真云联调分别报告；「离线」在单测中允许注入可控 `ApiClient` 故障，集成层必须真实断网（Design §9.2）。

## 5. 首批准备顺序

1. NC-001 实际客户端位置、端口装配、设备与后端清单、OpenAPI 验证器选型；不需要用户重新讨论产品范围。
2. NC-002 本地/公共模型契约、状态机转移表、canonical 编码与正反 fixture；**须先取得用户对 Design §2.1 的 UGC ID 前缀确认**，未确认前保持 `PREPARING`。书籍 AnchorRef 只引用待冻结边界，不自建影子模型。
3. NC-003 公共 API 与错误目录；同时准备 NC-004 的本地修订与 NC-005/006 的编辑器/撤销工作包。
4. 并行准备 NC-015 密钥恢复方案（**从零设计，不是复用**：`xuan-storage` 现有只有单设备 Ed25519 身份种子，无任何恢复原语，30–60 分钟 ACT 粒度对它不适用）与 NC-020a 消费端核对清单，完成后解锁依赖实现。
5. NC-025 生产 BlobGateway 与 NC-002/003 并行准备，它是 NC-008/017 的硬前置。

先解决目录与接口，不先开工再从 UI 反推数据库。用户已确认自动保存、回收站、图片与撤销规则，无需再作为产品问题阻断准备。

## 6. 风险、退路与范围约束

- 书籍未交付：独立笔记继续，源句和真实来源 Tooltip 保持 BLOCKED，不用模糊文本匹配假装通过。
- 密钥协议未定：可测试本地加密组件，跨设备恢复保持 BLOCKED；不降级明文云备份。
- 云环境不可用：保留离线稿/待发操作，报告验收未执行；不以 Fake 替代生产链路。
- 原公共媒体不可撤权：新增受控访问适配，不能降低用户已确认的隐私要求。
- 现有 OpenAPI/通知文档矛盾：按源码记录事实，在对应契约任务修正并验证，不整体重写旧模块。
- 完整键盘方案：明确 F-01，保持 BACKLOG，不在本期新增更多快捷键设计。**无障碍不在 F-01 范围内**，PRD §4.1 的 A11Y-01～09 是本期承诺项。
- 生产 BlobGateway 未交付：公共图片链路保持 BLOCKED，禁止 import `InMemoryFirebaseBlobGateway` 充当生产实现；独立笔记与纯文本发布不受影响。
- notifier 契约版本裂口：ACK/relay 只引用 3.0.3 权威文档，不并入本系统 3.1 契约；拉正文与补拉端点由本系统实现。
- R2-03：社区命令由 NC-009 新增同事务 command_service 与查询路由，NC-011/012 复用；完整结果 14 天后仅精简、不清去重身份。不得以调高旧包装器 TTL 替代崩溃恢复。NC-009 白名单包含 command_service.py、community_commands.py、test_community_commands.py 及命令集合注册。

## 7. 交付与完成

最终交付包括 Flutter 功能包/可运行验收宿主、Python handlers 与存储规则/索引、生产 BlobGateway、本系统 3.1 OpenAPI/Swagger（notifier 3.0.3 只引用）、迁移与配置说明、BDD/TDD/ACT、真实链路证据和使用说明。所有 R-01～R-20 在 Tasks 有映射且在 PRD §3.1 有断言点；F 项独立后续登记，不混入本期通过率。

任务状态由主 Agent 更新；跨仓库提交各自保留，记录对应版本组合，禁止主 Agent 擅自合并到 main/master。本设计文档输出完成不等于业务开发完成。

## 8. R2 修订的执行约束

五项修订以 [Design](DESIGN.md) §4.4/§6.2.1/§7.2/§7.4 为准，具体反例已进入 NC-002/003/004/009/011/012/013/014；NC-007 的历史恢复也消费 v2 规则。先完成契约与成对 fixture，再执行依赖任务。通知可信映射缺证只阻断 NC-013/014 对应链路，书籍类型未冻结只阻断对应原句契约；不得凭本轮文档检查将任何任务升级为 READY 或 ACCEPTED。独立复核入口：[五项复核清单](REVIEW_R2_CHECKLIST.md)。

RW-1～6 补全：NC-002 冻结集合排序、说明来源、命令/桥接类型及标识反例；NC-010 接客户端持久队列恢复；NC-017 显式依赖 NC-009 并复用命令服务；NC-019 验证删除清理命令恢复。验收顺序为 review_r2_guard.sh → verify.sh → 人工语义复核，脚本通过不等于业务验收。

# NC-001 工程装配基线（本地准备）

日期：2026-09-10。状态：PREPARING；不是完整 NC-001 验收通过。机器事实快照：[integration_baseline.json](integration_baseline.json)。两位 Terra 只读调查，主线程抽验关键源码并决定下列方案。没有执行外部仓库测试、创建客户端目录或安装依赖。

## 1. 本轮决定

- 用户暂缓书籍整理：本轮不启动 NC-020a，不盘点书目、不导入原书；现有原句系统设计保留。
- CLIENT 固定计划新建于 `/Users/jingtaiwei/Git/Public/xuan-migration/reading-notes`，包名 reading_notes，状态 PLANNED_NEW。NC-004 承接建包及独立 example；本轮不以创建空目录骗过存在性门禁。xuan-migration 父目录不是 Git 仓库；CLIENT 定为独立 Git 仓库（与该目录下其他子模块一致，JSON 记为 client.vcs=NEW_GIT_REPOSITORY），由 NC-004 在 `reading-notes` 内执行 `git init` 建立，不在父目录提交；远端地址由用户后续指定，不阻塞本地开发。
- 不依赖 notebook 作为本期笔记底座。它是排盘圈画模块，有 chartKey/stage 结构及内存降级；本期新建 Note/Revision Repository 与领域表，但复用 Drift 和宿主连接/作用域能力，不复刻圈画引擎。
- 身份由现有宿主 ScopeResolver/账号会话提供，不新增随机 localProfileId 身份系统。独立测试宿主可注入受控测试 scope，不能把测试 scope 当作真实账号授权或公开匿名身份。
- 首个本地切片只负责账号隔离的本地保存/不可变历史/Markdown；NC-004 采用已允许的“加密无关 outbox 外层”路径，具体字段归 NC-002 冻结。未启用密文适配前不传私人正文。
- social 的普通通知中心可作为业务表现层复用来源，注解系统不启用匿名发言/匿名通知入口；其静态 initialNotifications 不是已接入的 Repository。notification 包复用传输/接收/ACK 管线，不同时装配遗留 NotificationPage。
- REST driver 已有可注入 http.Client；后续使用宿主认证 Client 装配 Firebase Bearer，不另建 HTTP 框架。仅注入点存在不等于当前鉴权已接通。

## 2. Terra 证据与主线程复核

| 模块 | 原始证据（外部路径前缀为 /Users/jingtaiwei/Git/Public） | 决定/限制 |
|---|---|---|
| notebook | xuan-migration/notebook/lib/src/annotation/engine/database_provider.dart:33，AnnotationDatabaseProvider；annotation_engine.dart:338，enter 内存降级 | 借鉴独立 QueryExecutor 生命周期，不复用其存储语义 |
| 账号作用域 | xuan-migration/xuan-storage/drift/lib/scope/scope_resolver.dart:27，ScopeResolver；xuan-shell/lib/app/xuan_shell_dependencies.dart:92，create | 复用宿主作用域；reading_notes 不为此整包依赖所有排盘持久化模块 |
| 本地隔离 | xuan-storage/drift/lib/record/drift_record_data_source.dart:75；record_storage_driver.dart:41 | 已有隔离思路；笔记需要自己的修订事务，不映射成覆写记录 |
| Profile/IM | social/lib/src/profile/public_profile_page.dart:20，PublicProfilePage/onStartChat | 回调参数实际为 PlaygroundUserId（presentation ID）；Terra 初稿简写为 appUserId 不采用，须显式映射三种身份 |
| Mention | social/lib/src/mention/mention_input_enhancer.dart:24，MentionInputEnhancer/onInsert | 复用组件，候选 Source 及 code point offset 由笔记适配；服务器旧扫描不冒充新稳定分页契约 |
| 通知 | notification/docs/integration-guide.md:105；lib/src/receive/receive_pipeline.dart:86 | 接收/ACK 行为可复用，宿主端口和生命周期仍须接线 |
| 去重 | notification/lib/src/receive/dedup_store.dart:28，InMemoryDedupStore | 当前非持久且无TTL；不算可靠生产接入 |
| 服务端身份 | xuan-server/functions-py/xuan/identity.py:61，resolve_app_user_id | 返回 appUserId/publicPresentationId；不能把 Firebase uid 直接当业务/展示 ID |
| HTTP | xuan-migration/repository-rest-adapter/lib/src/rest_storage_driver.dart:19，RestStorageDriver(client) | 包内默认 Client 无自动 Bearer；认证由宿主注入，不宣称已闭环 |
| 服务端测试 | xuan-server/functions-py/tests/conftest.py:11，_emulator_env | 仅核配置，没有连接、清库或运行测试 |

端口的机器登记见 JSON `ports`（8 项，按文件与符号记录、不用行号，由校验器检查）；上表行号仅供阅读，以 JSON 为准。Terra 建议中的 notebook 依赖和新增随机身份未采纳。两套 Drift 版本是 2.31 与 2.34 的次版本差异，SQLite 2.x/3.x 才是主版本分歧；不能据缓存存在就称依赖解析通过。

## 3. 仓库快照

| 标记 | 路径 | HEAD | 未提交条目数（采样时） |
|---|---|---|---|
| SPEC | `/Users/jingtaiwei/Git/Public/learn_system` | `7dd2e5f977b95a9e1b7155ef20e648a16fe96e55` | 14 |
| MIGRATION | `/Users/jingtaiwei/Git/Public/xuan-migration` | `NOT_A_GIT_REPOSITORY` | — |
| STORAGE | `/Users/jingtaiwei/Git/Public/xuan-migration/xuan-storage` | `87f0ee514ca4255909901f27f4f4a55301fb20b9` | 0 |
| SOCIAL | `/Users/jingtaiwei/Git/Public/xuan-migration/social` | `1971f79320ba679daf9be9e89d13a221eae6ff88` | 0 |
| NOTIFICATION | `/Users/jingtaiwei/Git/Public/xuan-migration/notification` | `e8cee528ff6aabe6bca744e546ffbe4f25cb02a7` | 0 |
| REST | `/Users/jingtaiwei/Git/Public/xuan-migration/repository-rest-adapter` | `0f8bf521a421592284e02fe0cd578b6db34ef439` | 0 |
| SERVER | `/Users/jingtaiwei/Git/Public/xuan-server/functions-py` | `866ea138c2a5b51e9fa5d4280568e78308090d63` | 0 |
| NOTIFIER | `/Users/jingtaiwei/Git/Public/xuan-server/notifier` | `8f32132c245598e23ece1d28f5090b094e0c8037` | 0 |

全部外部测试状态 NOT_RUN，无成功退出码或用例数可报。代码执行前重新记录 HEAD 与原有失败；SPEC 中其他 Agent 的 G3 改动不纳入本包。

## 4. SDK、依赖与工具决定

本机缓存元数据：Flutter 3.44.6 / Dart 3.12.2。Flutter 启动探测会写 SDK cache，Terra 的一次探测被沙箱拒绝，故这里只声称读到版本元数据，未声称运行环境测试通过。

本地依赖拟锁定 storage 已解析版本系列：drift 2.31.0、drift_dev 2.31.0、drift_flutter 0.2.8、sqlite3 2.9.4、sqlite3_flutter_libs 0.5.42、path_provider 2.1.6、build_runner 2.15.1；flutter_markdown_plus 固定 1.0.12。代码生成与渲染仅在建包后以实际 lock/解析结果验收；任何不兼容原样报告，不自动升级全仓。用户指定 Plus，不能换回旧 flutter_markdown。Plus 是渲染器，编辑使用 Flutter 文本输入与已设计的撤销适配；[维护方包说明](https://pub.dev/packages/flutter_markdown_plus)支持这一职责。

OpenAPI 选用 openapi-spec-validator 0.9.0，工具隔离于 SPEC/.venv-openapi，后续安装命令 `python3 -m venv openspec/annotation-community/.venv-openapi`，再使用其中 python 执行 `-m pip install openapi-spec-validator==0.9.0`。支持 OpenAPI 3.1 的依据：[维护方发布说明](https://pypi.org/project/openapi-spec-validator/0.9.0/)。本轮未安装，当前 Python 未装该包/pytest/jsonschema。离线无 wheel 或依赖时明确 ENV_BLOCKED，禁止改为字段存在性检查；NC-003 用合法/非法规范成对运行验证器。精确传递依赖 lock 在工具安装工作包输出，不伪造已冻结环境。

## 5. NC-001 十项完成情况

| 项 | 本次事实 | 完整门禁 |
|---|---|---|
| 两台设备 | 未盘点/未验证，不填写虚假 device_id | 两台真实设备及用途，NC-016/018 前必需 |
| 后端与账号对 | 无测试 token、无真实 uid↔appUserId 映射证据 | 受控命名空间、两账号、凭据仅运行时注入 |
| Emulator | 配置 192.168.0.165:8080 / :9099 / demo-xuan | 连通与隔离证据尚无；不用生产替代 |
| 仓库/测试/写范围 | HEAD 已记录；外部测试 NOT_RUN，本轮无外部写权限 | 执行时补测试基线与逐仓 ACT 范围 |
| OpenAPI 工具 | 选型完成，未安装/实跑 | 安装锁及非法样例确实失败 |
| Markdown Plus | 已指定版本，有缓存/官方说明 | 新工程实际依赖解析与 Widget 验证 |
| Firestore rules | 本轮未定位权威部署路径 | SERVER 集成前必须由部署证据确定 |
| 通知表现层 | 复用 social 普通中心组件；不挂遗留页 | 非静态 Repository 接入、导航真实验证 |
| 宿主账号注销 | 来源、送达语义和测试均未验证。已查到的只有客户端删号：xuan-account `lib/auth/auth_coordinator.dart` 的 `AuthCoordinator.deleteAccount` 调 `deleteCurrentAccount()` 删除 Firebase 当前用户并清本地会话，xuan-shell `ShellAccountController.deleteAccount` 转调；functions-py 的 `main.py` 与 `xuan/` 中没有删号处理函数或触发器，服务端当前收不到删号事件 | NC-001 登记证据，NC-026 消费；缺证只阻断 NC-026 注销子项，不能以退出登录代替删号事件 |
| 静音/聚合 | 存在UI/callable入口，未证明端到端语义 | NC-013/014 提供持久化、优先级和聚合证据 |

这些缺口不要求用户现在整理书籍，也不妨碍 NC-002 本地模型文稿准备；完整 NC-001 不能据此标 ACCEPTED。

## 6. 两级准备门禁（主线程本轮细化）

NC-001-01 只验证本地**规划基线**：计划目录声明、版本来源、依赖边界、复用证据和所有未验证项诚实登记。PLANNED_NEW 的合法性不等于目录/程序已存在。NC-001-02 是完整联调基线，继续要求原十项真实完成；本轮不编造它的执行命令或凭据。原 TASKS 的“目录必须存在”用于运行/完整准出；本地准备允许有明确创建责任与现存父目录的计划路径。禁止创建空目录或伪造测试结果让总项通过。

首份六件套见 [nc-001 README](../../docs/blackbox-spec-rework/work-items/nc-001/README.md)。它仍为 PREPARING，需独立 ACT 审查；本轮没有业务编码派发。

# 笔记、原句注解与讨论 Tasks

版本：1.5；2026-09-10（新增 R-21 行为事件数据源，见 FIX_V1_5；待抽查确认）。状态：`APPROVED_DESIGN`；执行状态：`NOT_STARTED`。
权威需求：[PRD](PRD.md)，技术依据：[Design](DESIGN.md)，根路径与执行门禁：[Plans](PLANS.md)，审查缺陷登记：[REVIEW_R1](REVIEW_R1.md)。下面路径使用 Plans §1 的精确根路径标记；标为「新增」的路径是任务产物，不声称当前文件存在。

**状态枚举直接引用 [工作包门禁](../subagent-delivery-gate.md) §7 的七值枚举**（`BACKLOG / PREPARING / READY / DISPATCHED / REVIEWING / ACCEPTED / BLOCKED`），本文件不再自造释义。总表「初始状态」是登记时的取值；**流转中的当前状态以仓库唯一监控表 [`SUBAGENT_TODO.md`](../../docs/blackbox-spec-rework/SUBAGENT_TODO.md) 为准**，NC-001～NC-026 须在该表登记「NC 注解社区线」章节后方可开始流转，避免两处状态源并存。

所有条目初始未完成。**本文件没有 READY 任务，不能凭自然语言直接派发业务编码。** 一项涉及多仓库时，六件套须拆为有序 ACT，分别限定写入所有权（见 [Plans §1.2](PLANS.md)）；其他 Agent 的改动不得回退。

## 1. 总表与需求追踪

| 任务 | 范围 | 依赖 | 初始状态 | BDD/TDD 就绪度 | PRD |
|---|---|---|---|---|---|
| NC-001 | 客户端位置、宿主、端口装配、设备与后端清单、验证器选型 | 无 | BACKLOG | BDD+TDD 均可写 | R-18 |
| NC-002 | 非书籍模型、ID 前缀、状态机、限额、canonical 编码与 fixture | NC-001 | BACKLOG | BDD+TDD 均可写（需先取得 ID 前缀确认） | R-01, R-04, R-05, R-18, R-20 |
| NC-003 | 公共 REST/OpenAPI/Swagger 契约与错误目录 | NC-002 | BACKLOG | BDD+TDD 均可写 | R-18, R-20 |
| NC-004 | Drift 修订与可靠保存 | NC-002, NC-015 | BACKLOG | TDD 待 NC-002 冻结 | R-02, R-04, R-16 |
| NC-005 | Markdown 编辑预览、状态与撤销栈裁定 | NC-004 | BACKLOG | TDD 待 NC-002 冻结 | R-01, R-02, R-16 |
| NC-006 | Undo/Redo 与 IME/焦点 | NC-005 | BACKLOG | 仅 BDD，TDD 待 NC-005 裁定撤销栈归属 | R-03 |
| NC-007 | 历史、差异、恢复与冲突处理旅程 | NC-004, NC-005 | BACKLOG | TDD 待 NC-002 冻结 | R-04, R-12 |
| NC-008 | 本地图片与公共资源适配 | NC-003, NC-004, NC-025 | BACKLOG | 仅 BDD，TDD 待 NC-025 | R-15, R-20 |
| NC-009 | 发布/更新/收回、权限事务与 ACL 全入口扫描 | NC-003, NC-008, NC-015 | BACKLOG | 仅 BDD，TDD 待 NC-002/003 | R-05, R-20 |
| NC-010 | 笔记列表、公开详情与发布 UI | NC-005, NC-007, NC-009 | BACKLOG | 仅 BDD，TDD 待 NC-003 | R-01, R-05, R-16 |
| NC-011 | 两级评论/回复与编辑删除 | NC-003, NC-009, NC-010 | BACKLOG | 仅 BDD，TDD 待 NC-002/003 | R-08, R-20 |
| NC-012 | 赞踩/收藏/分享/@/关系与举报 | NC-003, NC-009, NC-011 | BACKLOG | 仅 BDD，TDD 待 NC-002/003 | R-09, R-10, R-20 |
| NC-013 | 事务事件、投递、通知正文与补拉端点 | NC-003, NC-011, NC-012 | BACKLOG | 仅 BDD，TDD 待 NC-002/003 | R-11, R-20 |
| NC-014 | Notification 宿主适配、去重与导航 | NC-010, NC-013 | BACKLOG | 仅 BDD，TDD 待 NC-013 | R-11, R-16 |
| NC-015 | 密钥恢复、设备授权与删除窗口协议 | NC-001 | BACKLOG | BDD 可写，TDD 待协议样例格式确定 | R-12, R-13, R-14, R-20 |
| NC-025 | **生产 BlobGateway（公共 + 私有）** | NC-001, NC-003 | BACKLOG | BDD 可写，TDD 待 NC-003 | R-15, R-13, R-20 |
| NC-026 | 行为事件数据源、假名化与私人笔记元数据上报 | NC-002, NC-003, NC-005, NC-009 | BACKLOG | 仅 BDD，TDD 待 NC-002/003 | R-21 |
| NC-016 | 私人加密 mapper 与设备同步 | NC-004, NC-015 | BLOCKED | 仅「密文无明文」负向断言可先写 | R-12, R-20 |
| NC-017 | 生产密文网关与备份清单 | NC-003, NC-015, NC-025, NC-009 | BLOCKED | 待 NC-015 | R-13, R-20 |
| NC-018 | 备份设置、进度与恢复 | NC-008, NC-016, NC-017 | BLOCKED | 待 NC-015 | R-12, R-13 |
| NC-019 | 回收站、恢复、永久清理 | NC-007, NC-009, NC-018 | BLOCKED | 本地回收站子 ACT 可先写 | R-14, R-20 |
| NC-020a | 消费端书籍契约核对清单 | 无 | BACKLOG | BDD+TDD 均可写（文档扫描型） | R-06, R-07, R-17 |
| NC-020b | 上游书籍政策/Schema/D-06/样例冻结 | NC-020a, 既有上游交付 | BLOCKED | 均待上游 | R-06, R-07, R-17 |
| NC-021 | 书籍上传、导入、激活与查询 | NC-003, NC-020b | BLOCKED | 均待上游 | R-17, R-20 |
| NC-022 | 阅读、原句注解与锚点解析 | NC-004, NC-020b, NC-021 | BLOCKED | 均待上游 | R-06, R-07, R-17 |
| NC-023 | 真实 Tooltip 原型与入口一致性 | NC-010, NC-012, NC-014, NC-022 | BLOCKED | 均待上游 | R-07, R-19 |
| NC-024 | 跨模块真实验收与交接 | NC-003, NC-006, NC-007, NC-008, NC-009, NC-010, NC-011, NC-012, NC-013, NC-014, NC-016, NC-018, NC-019, NC-021, NC-022, NC-023, NC-025, NC-026 | BLOCKED | 待全部前置 | R-01～R-21 |

需求 ID 使用完整形式（不用 `R-09/10/20` 压缩写法），以便 `verify.sh` 的双向闭环断言可机械核对。

### 1.1 R1 审查带来的依赖修正

- **NC-004 补 NC-015 依赖**：其「记录待同步操作」的 outbox 信封格式由 NC-016/NC-015 冻结。若要解除该阻塞，NC-004 须先冻结一个与加密无关的 outbox **外层** schema 并声明「信封内容由 NC-016 填充」，二选一在工作包 README 中写明。
- **NC-009 补 NC-015 依赖**：Design §4.3 的 trash 要求「传播 tombstone」，而 tombstone 保留窗口/epoch 由 NC-015 冻结。或把该窗口从 NC-015 拆出为 NC-009 自有决策，同样须在 README 写明。
- **NC-008/NC-017 补 NC-025 依赖**：生产 BlobGateway 此前无任何任务拥有。
- **NC-020 拆为 NC-020a/NC-020b**：消费端核对清单可现在准备（`PREPARING`），上游政策/Schema 冻结保持 `BLOCKED`，消除 Plans「首批准备顺序」与总表 `BLOCKED` 的口径冲突。
- **NC-024 依赖补全**：原列表遗漏 NC-003、NC-009、NC-013、NC-025，虽可传递但总验收显式列全更利于区分失败来源。

依赖图经逐条展开**无环**；无「BACKLOG 任务依赖 BLOCKED 任务」的隐藏阻塞。

### 1.2 共享文件写入所有权

见 [Plans §1.2](PLANS.md)。特别注意 `SERVER/tests/conftest.py`：它强制 Emulator 主机并硬编码 `COLLECTIONS` 清理清单，此前不在任何任务白名单内，新增社区集合会导致用例互相污染。本版将其纳入 NC-009/011/012/013/017/019/021/026 的白名单，**仅允许向 `COLLECTIONS` 追加键**。

NC-019 可先准备本地回收站子 ACT，但完整清理验收等待备份协议；NC-020 的协调文档可现在准备，不能越过上游政策冻结。状态解锁须记录证据，不只删除 BLOCKED 字样。

## 2. 前置契约

### NC-001：实际工程位置与装配基线

- [ ] 读取现有 SOCIAL/STORAGE/REST/NOTIFICATION 及候选 CLIENT 的 AGENTS、pubspec、导出与真实调用；确认是否已有可复用学习包。当前相邻 learn_system 不是 Flutter 包。
- [ ] 新增 `SPEC/INTEGRATION_BASELINE.md`，冻结 CLIENT 实际根、包名、Flutter/Dart 版本、各依赖精确范围、宿主初始化/账号/HTTP/存储/IM 导航注入点、各仓库基线提交。若改变拟建目录，回写所有任务路径。
- [ ] `INTEGRATION_BASELINE.md` 必填项（R1 补入，此前 NC-016/018/023 引用了本任务从未承诺的产物）：① **设备清单表**（device_id、平台、系统版本、是否可作 P2P 对端，至少两台）；② **测试后端表**（project_id、命名空间前缀 `nc_<日期>_<短哈希>`、测试账号 uid ↔ app_user_id 对、凭据注入方式）；③ **Emulator 实值**（`FIRESTORE_EMULATOR_HOST`、`FIREBASE_AUTH_EMULATOR_HOST`、`GCLOUD_PROJECT`）与启动方式；④ 每个外部仓库的当前 HEAD、当前测试基线（退出码 + 用例数）、是否允许写入及精确写入路径；⑤ **OpenAPI 3.1 验证器实值**（名称 + 精确版本 + 安装方式 + 离线失败行为）；⑥ `flutter_markdown_plus` 的选型依据、精确版本范围（workspace 内 pub-cache 现为 1.0.12，但**无任何 pubspec 引用它**，属新依赖）与离线 pub-cache 失败策略；⑦ Firestore 安全规则文件路径；⑧ 通知回跳挂靠哪一套 notification 表现层（`social/lib/src/notification/` 与 `notification/lib/src/` 并存）；⑨ 宿主 notification 是否支持「按内容静音」与「聚合」粒度，不支持则登记为 E-WIRING 缺口；⑩ 宿主账号注销与本人彻底删除账号事件的来源、送达语义（至少一次还是恰好一次）与测试方式，供 NC-026 消费。
- [ ] 新增 `SPEC/tools/check_integration_baseline.py`，机器输入为 `SPEC/integration_baseline.json`，并扫描同目录 `INTEGRATION_BASELINE.md`；字段契约见 `PACK/nc-001/VALIDATION_CONTRACT.md`。分两级：**NC-001-01** 用 `--profile local` 校验规划基线，允许 CLIENT 为 `PLANNED_NEW`（创建归 NC-004、父目录存在、目录尚不存在），未验证项必须按契约如实登记；**NC-001-02** 用 `--profile integrated` 作为本任务总项准出，要求 CLIENT 为 `EXISTING` 且十项全部为验证态。两级共同红条件：`INTEGRATION_BASELINE.md` 含 `TBD`/`待定` 占位、任一端口缺存在的文件或合法符号、上述十项必填项任一缺失。
- [ ] 验收：每个端口列真实文件/符号和「已有实现/新增适配」，不把 mock 或内存降级当生产；目录/版本未唯一确定则本任务不通过。NC-001-01 运行 `python3 SPEC/tools/check_integration_baseline.py --profile local --input SPEC/integration_baseline.json`，退出 0，只关闭 NC-001-01；**NC-001 总项**运行同一命令的 `--profile integrated`，退出 0 且 stdout 恰为 `INTEGRATED_STRUCTURE_PASS`（不带 `(TEST_FIXTURE)`）才可标 ACCEPTED。

### NC-002：模型与固定行为契约

- [ ] RW-1～3：三类顶层引用集合规范排序后数组换序 hash 不变，完全相同的重复项被 Schema 拒绝（需负例 fixture）；仅 change_summary 不同则 hash 不同并新增修订，系统派生摘要不同不影响保存；嵌套合法有序数组换序则 hash 不同。补 CommandRecord 完整/精简/拒绝终态、NotifierDeliveryBinding 可信来源及 command_id 正则正反例；外部不透明 ID 不套本地前缀正则。

- [ ] **先取得用户对 [Design §2.1](DESIGN.md) 的 UGC ID 前缀确认**（仅本系统拥有的业务 ID；notifier 原始 ID 不适用此前缀表）。未确认前本任务保持 `PREPARING`，不得进入 `READY`。
- [ ] 新增 `SPEC/contracts/community-models.md` 与 `SPEC/contracts/state-machines.md`，覆盖 Note/Revision/Publication/ContentAccess/Comment/Reaction/NotificationRecord/NotifierDeliveryBinding/CommandRecord 的字段归属，以及九台状态机（编辑态、发布态、生命周期、审核态、客户端 `pending_op`、清理任务 `PurgeTask.state`、投递态、导入态、锚点解析）的**完整转移表**：每条边标注触发事件、前置条件、目标态与失败错误码；含 §4.1 的状态组合白名单与非法转移期望。
- [ ] **机器 Schema 落位沿用仓库既有范式**（不另造一套）：新增 `openspec/schemas/community_note.schema.json` 等，正反例放 `openspec/schemas/examples/`，命名 `<obj>.valid.yaml` / `<obj>.invalid_<reason>.yaml`，并在 `openspec/schemas/verify.sh` 追加成对判据（正例必须通过、负例必须失败）。跨端 fixture 另放 `SPEC/fixtures/community/`。
- [ ] 冻结 [Design §7.2](DESIGN.md) 的 content_hash canonical 编码，产出 `SPEC/fixtures/community/content_hash_cases.json`，并**同时指定两个消费者**：`SERVER/tests/test_community_hash_parity.py` 与 `CLIENT/test/contracts/content_hash_parity_test.dart`，逐条断言 `expected_hash` 字面量。fixture 不得只有生产者无消费者。按 nchash/v2 同时断言 expected_canonical_hex；仅改 binding/selector/mention offset/图片 alt/change_summary 必须不同，对象键序/同步进度不改变 hash；恢复同文另建修订。另含「mention 之前有一个 4 字节字符（如 `𠀀` U+20000）」用例：写明按 code point 计数的期望 start_offset、期望 canonical hex 与期望 hash，Python 与 Dart 必须得出同一字面值。
- [ ] 冻结 [Design §7.1](DESIGN.md) 的限额边界闭合语义与计量口径，产出恰好等于/超一个单位的成对 fixture；必须含「4,000 个 4 字节 emoji 的评论」用例（期望通过）与 `limit=101`（期望 400）。
- [ ] Fixture 至少含：私改未发布、恢复同文新修订、两个并发 parent、跨楼非法 reply、超限内容、四类无效 mention（user_id 不存在 / 账号已注销 / 已被拉黑 / 文本不再匹配）、五类非法 ID 格式（含 `rev_` 误用作 NoteRevision）。每条写清完整期望记录或错误 code，不写「验证失败即可」。
- [ ] 新增 `SPEC/tools/validate_fixtures.py`。红条件：任一 fixture 缺 `expected` 字段、或出现未登记在 `state-machines.md` 枚举表中的状态值、或 ID 不符合 §2.1 前缀规则。
- [ ] 验收：每个 DTO 与私人/公共字段归属唯一；私人 parent 链和正文不进入公共查询；PRD 已确认默认值无矛盾。运行 `bash openspec/schemas/verify.sh` 与 `python3 SPEC/tools/validate_fixtures.py SPEC/fixtures/community/`，均退出 0。

### NC-003：公共 API 与 Swagger

- [ ] 修改 `REST/openapi/openapi.yaml`，新增社区公共资源/命令/错误/分页/ETag/幂等；请求头一律用 `in: header` 的 header parameters。**该文件由五个任务串行写入：NC-003 → NC-013 → NC-017 → NC-021 → NC-026**，后继任务以前一个产出为基线重跑契约测试。密码学/书籍扩展在 NC-017/021 合并至同一入口，不伪造已冻结字段。
- [ ] **写入白名单必须包含既有的 `REST/test/openapi_validation_test.dart`**：该文件现有 8 处断言（第 147/148/161/217-218/239-240/292/307 行附近）正好**要求** operation 级 `headers:` 存在，修正结构必然弄红。README 记录改前基线（当前 `dart test` 退出码与用例数），ACT 中把「迁移 8 处断言到 `in: header`」作为独立步骤，以便区分既有失败与本任务新增失败。
- [ ] 落地 [Design §7.3](DESIGN.md) 的**错误目录**：每个场景唯一 HTTP 状态码 + 唯一 `code` + Problem Details 附加字段；不得保留「403 或 404」这类二选一。`conflict.idempotency` 沿用 SERVER 仓 `tests/test_playground_rest_writes.py` 的既有命名。限流阈值与 `retry_after_seconds` 填实值，未填实值前 `429` 不写入验收。
- [ ] 按 Design §7.4 定义 command_id=Idempotency-Key、唯一键 (owner_scope, command_id)、payload_hash（含 operation）、命令查询端点与恢复错误。完整结果保留 14 天，精简账本持续去重；超期同键绝不新建业务。reaction If-Match、expected_access_version、原始 applied_version 与当前状态读取分别建 Schema/HTTP 正反例。
- [ ] 新增 `REST/test/community_openapi_contract_test.dart` 与 `REST/tool/validate_openapi`；验证器名称/版本/安装方式/离线失败行为取自 NC-001 的实值，**不由本任务执行 Agent 选型**。Swagger UI 读取同一 3.1 契约；notifier 的 3.0.3 契约只引用不复制。
- [ ] Red fixture 包含：operation 级 `headers:`、缺必填、非法状态、同键异载荷、412，以及**一份故意非法的 3.1 文档（验证器必须返回非零退出码）**——这一条专为防止再写一个 yaml 字段检查器充数。Green 用真实解析器验证。
- [ ] 运行 `dart test test/community_openapi_contract_test.dart` 与 `tool/validate_openapi openapi/openapi.yaml`，均退出 0；两者需本任务实际创建，不能假称现已可运行。

## 3. 独立本地笔记

### NC-004：可靠保存与不可变修订

- [ ] 在 NC-001 冻结的 CLIENT 位置建立或扩展 `pubspec.yaml`、`lib/reading_notes.dart`、`analysis_options.yaml`，依赖严格采用 NC-001 固定版本；登记 Drift 生成文件与 schema migration 步骤，运行必要生成命令后才能运行测试。
- [ ] 新增 `CLIENT/lib/src/domain/note.dart`、`note_revision.dart`、`persistence/note_database.dart`、`note_repository.dart`；在 `test/persistence/note_repository_test.dart` 建失败用例后实现事务保存与待同步记录。
- [ ] 覆盖首次/无变化保存、连续两版本、附件引用、磁盘失败回滚（回滚后编辑态为 `save_failed` 且无半个 head/outbox）、文件库关闭重开、账号切换旧回调隔离；本地超限（1 MiB + 1 B）抛 `NoteSizeLimitExceeded` 且缓冲保留、不生成修订。禁止照搬 notebook 覆盖 committed 或内存模式报成功。
- [ ] 冻结 outbox **外层** schema（与加密无关的信封头），声明「信封内容由 NC-016 填充」；或在 README 中改为直接依赖 NC-015 的冻结产物。二选一必须写明，不能带着未决依赖派发。
- [ ] 消费 NC-002 的 `content_hash_cases.json`，新增 `CLIENT/test/contracts/content_hash_parity_test.dart` 断言 `expected_hash` 字面量；普通保存以完整语义投影去重，显式恢复/合并不按 hash 折叠。按 Design §7.2 的 `summary_touched` 规则补三条用例：① head 说明为 X，新会话改动正文后改回原文再保存 → 不新增修订；② 新会话只填写说明 Y → 新增修订且 change_summary=Y；③ 新会话改动正文、未碰说明 → 新增修订且 change_summary 为空串（不继承 X）。
- [ ] 运行 `flutter test test/persistence/note_repository_test.dart`；期望真文件重开后版本与引用不丢，失败不产生半个 head/outbox，不只测内存 Fake。

### NC-005：Markdown 编辑、预览和保存状态

- [ ] 新增 `CLIENT/lib/src/editor/note_editor_controller.dart`、`note_editor_page.dart`、`markdown_preview.dart`，及 `test/editor/note_editor_test.dart`；使用 Plus 渲染、现有文本输入与薄格式工具栏。
- [ ] **裁定并实现撤销栈归属**（Design §3 已定为方案 b：`editor_history_adapter` 为唯一真源，编辑器内禁用平台 `UndoHistory`），把裁定结果写入工作包 README 供 NC-006 直接消费，避免 NC-006 先写红测再返工。
- [ ] 按 [Design §3](DESIGN.md) 的编辑态转移表逐边建测，含 `saving` 期间继续输入置 `pending_dirty`、`save_failed` 不自动重试、`ime_composing` 无法完成输入时不允许离开。
- [ ] 测试虚拟时间 2 秒去抖、失焦 flush、返回失败留页、相同内容去重、IME composing 未提交不建最终修订、无书籍也能编辑；UI 分开本地/设备/备份状态。
- [ ] 按 PRD §6.1 实现三态指示：本地/设备同步/云备份各自取值互不共用文案，断网时云备份显示「状态未知（离线），最后确认备份时间 …」，未开启显示「未开启」且不使用失败样式；`saving` 持续不足 400 ms 不显示中间态。
- [ ] 安全断言（此前无所有者）：原始 HTML 不执行；私密预览下外部图片默认不自动请求，用户显式加载才发起。
- [ ] 无障碍断言（PRD §4.1）：A11Y-04 状态文本等价、A11Y-05 撤销/重做 semantics 与禁用语义、A11Y-07 在 320pt × 200% 字体下无截断。
- [ ] 运行 `flutter test test/editor/note_editor_test.dart`；自动保存不改变已发布正文，未知云状态不显示成功；不添加本期以外快捷键。

### NC-006：撤销、重做与输入法

- [ ] 新增 `CLIENT/lib/src/editor/editor_history_adapter.dart`，修改 editor controller/page 的局部命令接线；新增 `test/editor/editor_history_test.dart` 与 `test/editor/editor_shortcuts_test.dart`。
- [ ] 用同一输入序列分别调用按钮/快捷键：Windows/Linux Ctrl+Z、Ctrl+Shift+Z、Ctrl+Y；macOS ⌘Z、⌘⇧Z；移动按钮。检验正文、光标、图片/@ 引用和 canUndo/canRedo 一致，不同时调用平台及自有栈造成双撤销。
- [ ] 归组规则按 [Design §3.1](DESIGN.md) 的可判定阈值实现（间隔 < 500 ms、未跨空白或换行、单元 ≤ 20 字符三条全满足才合并；粘贴/格式/图片/@ /光标跳转无条件开新单元），阈值取自 NC-002 的测试常量。**禁止以「平台默认行为」作为验收 oracle**——那等于用实现定义验收。
- [ ] 基准断言：空编辑器以 100 ms 间隔输入 `a`、`b`、`c` 后按一次 Ctrl+Z，文本为空串且 `canRedo=true`、`canUndo=false`。
- [ ] 「不双撤销」断言：按下一次 Ctrl+Z，`undoCount` 增加 1 且文本仅回退一个 undo 单元。
- [ ] 覆盖连续输入归组、中文 composition 一次撤销、粘贴/格式/图片操作边界、自动保存后 Undo、Undo 后新输入清 redo、焦点在其他控件不响应、重开栈清空但修订仍在。
- [ ] 运行 `flutter test test/editor/editor_history_test.dart test/editor/editor_shortcuts_test.dart`；禁止把“取消发布”塞入 Undo；禁止实现 F-01 的其他快捷键。

### NC-007：历史差异与多分支恢复

- [ ] 新增 `CLIENT/lib/src/history/revision_history_page.dart`、`revision_compare.dart`、`revision_conflict_controller.dart` 及 `test/history/revision_history_test.dart`。
- [ ] 验收编辑会话归组但能查看每次修订；恢复旧版新建 ID/restored_from，不覆盖历史；选择任一冲突分支或手动合并生成含父链的新版本，旧分支仍可查。
- [ ] 实现 PRD 旅程 6 的完整冲突处理路径：列表标记 → 顶部横幅（正文默认本机版本且**可继续编辑**）→ 对照页 → 四选项（保留本机/采用对方/手动合并/**稍后处理**）。断言：选「稍后处理」后可继续输入并自动保存、横幅不再自动弹出、不阻断任何编辑；提交前收到第三条分支不覆盖正在编辑的合并稿；合并编辑区支持 §4 的撤销/重做。
- [ ] 长文差异可读性：默认折叠未变更段落，提供「跳到上/下一处变更」，以 1 MiB 文档验证。
- [ ] 运行 `flutter test test/history/revision_history_test.dart`；比较私人内容不调用服务器明文 diff API。

## 4. 图片与公开社区

### NC-025：生产 BlobGateway（公共 + 私有）

R1 核验发现的独立缺口：`STORAGE/firebase/lib/media/blob_gateway_firebase.dart` 第 1–5 行自述「BlobGateway 的 firebase 占位实现…⚠ **真云端实现未交付**（Phase 0 审计确认：全仓库无 firebase/supabase 真实现）。本类为内存 fake」。R-15 依赖的公共图片真实上传/下载/鉴权链路此前**没有任何任务拥有**，NC-008 只做 handler 与 resolver、NC-017 只做私人备份网关。

- [ ] 新增 `STORAGE/firebase/lib/media/production_blob_gateway.dart` 与 `test/media/production_blob_gateway_test.dart`；新增 `SERVER/xuan/handlers/blob_tickets.py`、`tests/test_blob_tickets.py`。写入白名单含 `SERVER/tests/conftest.py`（仅追加 `COLLECTIONS` 键）。
- [ ] 实现服务器推导 owner/path（不信任客户端）、每次重新鉴权的下载票据、**票据 TTL ≤ 300 秒**、公共与私有两条资源策略隔离、与 Playground 媒体及 relay 的路径/生命周期隔离。
- [ ] 明确「收回后新的取票据请求返回 404，已签发的未过期票据不吊销」这一已知窗口，并在 PRD §5 的口径内如实呈现，不声称「立即撤权」。
- [ ] 运行 `flutter test test/media/production_blob_gateway_test.dart` 与 `python3 -m pytest tests/test_blob_tickets.py -q`（需 Emulator）。**真实证据定义**：真实 bucket 名、对象路径、上传后用**另一个账号的 token** 取票据被拒的原始 HTTP 响应、票据过期后访问被拒的原始响应。**禁止任何生产代码路径 import `InMemoryFirebaseBlobGateway`**，该断言以静态扫描形式固化。

### NC-008：图片引用与访问边界

- [ ] 新增 `CLIENT/lib/src/media/note_attachment_repository.dart`、`markdown_image_resolver.dart`、`test/media/note_attachment_test.dart`；新增 `SERVER/xuan/handlers/community_media.py`、`tests/test_community_media.py`。
- [ ] **前置 NC-025**：公共资源必须走生产 BlobGateway，禁止 import `InMemoryFirebaseBlobGateway`（它就在 `firebase/lib/media/` 里且 import 路径看起来完全正规，是最容易蒙混的一处）。
- [ ] 本地图片使用现有 cipher 端口注入并按 scope 读取；发布资源独立于私有对象。校验 20 张/10 MiB 限额（**以加密前明文字节计**，密文膨胀不计入配额）、丢文件/上传中断、图片 Undo 不清历史引用、私密外部图片默认不请求。
- [ ] 实现 PRD §6.3 的上传进度：n/m + 单文件进度、可取消、单张失败不使整批作废；断言「20 张上传中断第 12 张，重进后前 11 张不重传」。
- [ ] 验收公共图片每次访问当前 ACL，票据 TTL ≤ 300 秒；禁止永久公开 URL 或改变私人 Blob ACL。R-20 的可测断言是「收回后**新的**取票据请求返回 404」，而非旧票据立即失效。
- [ ] 运行 `flutter test test/media/note_attachment_test.dart` 与 `python3 -m pytest tests/test_community_media.py -q`（后者需 Emulator，见 [Plans §4](PLANS.md)）。**真对象证据定义**：记录真实 bucket 名、对象路径，以及用**另一个账号的 token** 取票据被拒的原始 HTTP 响应；内存 Fake 通过不算。

### NC-009：公共发布事务与权限

- [ ] 新增 `SERVER/xuan/community/content_service.py`、`xuan/handlers/community_contents.py`、`tests/test_community_publications.py`；修改 `xuan/config.py`、`main.py` 的必要注册；**写入白名单含 `SERVER/tests/conftest.py`（仅允许向 `COLLECTIONS` 追加社区集合键）**。实际规则/索引路径取自 NC-001 登记。
- [ ] **新增 `SERVER/tests/test_community_acl_sweep.py`：R-20 的唯一系统扫描所有者**（此前 R-20 分散在 11 个任务里顺带断言、无专属命令）。参数化 6 入口（正文 / 历史 / 附件 / 分享 / 关联列表 / 通知正文）× 3 失效原因（withdrawn / trashed / hidden）= 18 条，每条断言状态码 + `code` + 响应体不含正文任意 20 字连续片段，且四种失效原因**共用同一响应、不含可区分字段**（PRD §6.2 决策）。
- [ ] 实现 [Design §4.1](DESIGN.md) 的状态组合白名单与非法转移期望（`409 conflict.lifecycle`），含 `withdrawn → published` 允许、`purge_pending` 下 restore 拒绝、`hidden` 内容 restore 后仍 hidden。
- [ ] Firestore 安全规则测试（此前有交付物无所有者）：规则文件路径取自 NC-001，命令形如 `firebase emulators:exec --only firestore '<规则测试命令>'`，作为本任务的第二条验证命令。
- [ ] 实现选定快照发布、更新、收回、当前权限查询。**原子边界按 [Design §4.3](DESIGN.md)**：事务内包含发布记录 + 当前指针 + 公共绑定 + outbox + command 终态结果；对象上传在事务**之前**完成并校验，孤儿由清理任务回收；不得笼统声称跨对象存储原子。社区命令新增事务级 command_service，不套用既有 claim/fn/result 包装器；不修改其他旧业务幂等路径。
- [ ] **R2-03 命令恢复**：新增 `SERVER/xuan/community/command_service.py`、`xuan/handlers/community_commands.py`、`tests/test_community_commands.py`，纳入写入白名单和命令集合清理注册；实现 Design §7.4。Firestore Emulator 注入提交前异常、提交后响应前中断、响应丢失、结果 14 天后精简，再以同键重试；断言只有一个业务对象/事件、计数正确、可恢复 applied_version，异载荷 409。捕获业务、outbox、账本原始记录；不接受补偿记录替代同事务原子性。
- [ ] **R2-05 提交顺序**：受控屏障分别强制 withdraw 先提交与 comment 先提交，含 Firestore 回调重跑。前者评论 404 not_found.content 且零评论/事件；后者评论可成功，随后 withdraw 成功并隐藏主题。仍可访问且 expected_access_version 过时才 409；迟到评论成功不恢复公开 UI，通知正文重新鉴权。2 评论 + 1 收回另做三方竞争。
- [ ] 先测私改不公开、旧 ETag、同键重试/异载荷、他人操作拒绝、收回与写评论并发。
- [ ] 可观测性断言（此前无所有者）：捕获 log sink，断言日志不含 fixture 中的标题与正文子串、不含密钥或完整敏感路径。
- [ ] 运行 `python3 -m pytest tests/test_community_publications.py tests/test_community_acl_sweep.py tests/test_community_commands.py -q`（需 Emulator）；原始 HTTP 测试按 [Design §7.3](DESIGN.md) 的错误目录断言**唯一** code，不接受 `assert status in (403, 404)` 这类二选一；直接服务函数成功不等于 REST 已通。

### NC-010：列表、详情与发布页面

- [ ] **RW-5，客户端命令恢复（Design §7.4）**：本任务新增 `CLIENT/lib/src/community/command_queue.dart`（账号隔离的 Drift 持久命令队列），它是客户端全部社区写命令的唯一队列。本任务负责 `content.publish/update/withdraw/trash/restore/purge` 的接入；`comment.create/edit/delete` 由 NC-011、`reaction.set`、`bookmark.set`、`share.create`、`share.revoke`、`report.create` 由 NC-012 复用同一队列，并按本条三项断言验收。操作先以该队列持久化 command_id、operation、payload_hash、请求与状态，再发送。测试真实文件库关闭重开后以原键重试；响应丢失后调用命令查询端点对账，committed/rejected 对应原结果且不新建命令；收到 410 保留最小结果并读取当前资源核实，503 保留待办且只允许原键查询/重试，两者均不换键重放。未发送意图可取消；已发送操作取消只停止本地重试，不能显示服务端已撤销。用 HTTP 请求记录及服务器账本证明无第二次业务写入，迟到响应不得覆盖较新版本；验收加入 publication_flow_test.dart。

- [ ] 新增 `CLIENT/lib/src/community/note_list_page.dart`、`content_detail_page.dart`、`publication_controller.dart`、`community_api.dart` 和 `test/community/publication_flow_test.dart`；在拟新建 `CLIENT/example/` 配置真实测试宿主。
- [ ] 验收本人草稿/有未发布修改/已公开状态、发布预览固定修订、图片未就绪拒绝发布、离线保留待发操作、版本冲突保留私人稿、服务器确认前不显示成功。
- [ ] 实现 PRD 旅程 3 的完整发布路径（消除「被拒即死胡同」）：预览页显示每张图的就绪状态与具体原因（上传中 x% / 上传失败 / 文件已丢失）及对应动作；**可就地切换选中的修订**并重算就绪状态；取消预览返回编辑页且未保存内容不丢失；首次发布展示 PRD §5.1 的一次性后果说明；成功页提供「查看公开效果（他人视角）」，断言其渲染内容不含任何未发布修订、未选中图片或私人父链（R-20 的用户自证形式）。
- [ ] 实现 PRD 旅程 9 的「待处理」全局队列：列出所有未被服务端确认的公共操作，可重试/取消/复制正文；因目标被删除/收回/拉黑/权限变更而终止时产生用户可见提示且正文可复制，**不得静默丢弃**；空态显示「所有操作都已完成同步」。
- [ ] 实现 PRD §5.1 的五个不可逆动作确认层，断言文案中的数量为运行时真实值（不出现未替换的「N 篇」字面量）。
- [ ] 七状态必答矩阵（PRD §6.4）：笔记列表与公开详情两屏逐状态断言，EMPTY 必须同时回答「为什么为空」与「下一步做什么」。
- [ ] 运行 `flutter test test/community/publication_flow_test.dart`；公共内容缓存重连失效，不承诺完整离线公共阅读。

### NC-011：两级评论、排序与修改历史

- [ ] 新增 `SERVER/xuan/community/discussion_service.py`、`xuan/handlers/community_comments.py`、`tests/test_community_comments.py`；新增 `CLIENT/lib/src/community/discussion_controller.dart`、`discussion_panel.dart`、`test/community/discussion_test.dart`。
- [ ] **客户端命令恢复**：`comment.create/edit/delete` 复用 NC-010 的 `command_queue.dart`，按 NC-010 RW-5 的三项断言验收：真实文件库关闭重开后以原键重试；响应丢失后调用命令查询端点对账，不新建评论；收到 410/503 时不换键重放。另测离线发表评论后重启 App：该评论在服务端只出现一次，讨论区与「待处理」队列中的「待发送」标记在服务端确认后同时消失。
- [ ] 复用 replies 的 depth/root 校验思路；新事务同时检查主题 ACL、root/target 与版本，通过 NC-009 command_service 同事务写 comment/revision/计数/outbox/命令终态。一级可最新/最早，楼内正序，各层独立稳定游标。
- [ ] 排序 tie-break 按 `(created_at, id)`，`id` 以 **UTF-8 字节序升序**比较（跨端游标稳定性的唯一依据）；一级默认 20 条、楼内默认展开 5 条，加载更多时已有内容与滚动位置不跳动。
- [ ] 测跨 thread/root 拒绝、回复楼内仍 depth1、删除 root 留墓碑（`Comment.status = deleted`）/已有回复但禁止新回复（返回 403 `forbidden.thread_closed`）、编辑不改 created_at、收回并发按 Design §4.4 两种提交顺序及仍可读旧版本分别断言、评论正文 4,000 与 4,001 code points 的成对边界（含 4 字节 emoji 用例）。
- [ ] 讨论区空态区分「还没有人评论，来写第一条」与「该内容不接受新评论」（已收回 / root 已删除）。
- [ ] 写入白名单含 `SERVER/tests/conftest.py`（仅追加 `COLLECTIONS` 键）。运行 `python3 -m pytest tests/test_community_comments.py -q`（需 Emulator）、`flutter test test/community/discussion_test.dart`。

### NC-012：互动、关系与结构化 mention

- [ ] 新增 `SERVER/xuan/handlers/community_interactions.py`、`tests/test_community_interactions.py`；新增 `CLIENT/lib/src/community/interaction_controller.dart`、`mention_adapter.dart`、`social_navigation_adapter.dart`、`test/community/interactions_test.dart`。
- [ ] **R2-02**：赞踩采用服务器 version + If-Match + NC-009 command_service，API viewer_reaction 为 like/dislike/null；取消只清活跃关系/计数，保留 null 状态行版本。新命令携带旧版本为 412；已执行命令重放返回原 applied_version，当前状态另读。客户端持久串行队列复用 NC-010 的 `command_queue.dart`，重启恢复和迟到版本防回滚均需实现；`bookmark.set`、`share.create`、`share.revoke`、`report.create` 同样经该队列发送，并按 NC-010 RW-5 的三项断言验收。
- [ ] @ 按 [Design §6](DESIGN.md) 的三元组 `(user_id, start_offset, length)` + 创建时 `display_name` 持久化，保存时按 code point 偏移（Design §6；Dart 经 `runes` 换算，禁止直接用 `String.substring` 截取）逐条校验子串是否仍等于 `"@" + display_name_at_creation`，不相等即解除该条关系；同昵称多处按各自 offset 独立判定。
- [ ] 收藏私有；分享解析检查当前权限，并提供分享链接管理与撤销（PRD §6.6）。资料/关注/私信/举报/拉黑调用已有能力，不添加排盘反馈；举报提交后给出受理确认并在举报者视图折叠该内容。
- [ ] `social` 的可复用面已核实为**部分成立**（`mention/` 是注入式真端口，其余导出多为 `plaza_*` UI 组件），注入点逐个取自 NC-001，缺端口则本任务新增适配。
- [ ] 基准反例：like(v0) → v1、cancel(v1) → v2、旧 like 同键重放后数据库仍 null/v2，UI 不被旧 v1 响应覆盖；重启后新动作使用读取版本；两设备同基线不同意图一个成功一个 412，禁止自动换版本抢写。另测未执行旧键/旧版本、相同值不重复计数、10 个并发操作、目标 purge 后旧命令不复活。
- [ ] 测快速切换的乱序/重试、两账号计数、失权目标、空候选、名字重复但 ID 不同、四类无效 mention；**关系与互动的业务结果**必须走实际宿主注入，不接受本地翻转/mock 关系——但单测中注入可控 `ApiClient` 网络故障来模拟离线是允许的（[Design §9.2](DESIGN.md)），两者不冲突。
- [ ] 运行 `python3 -m pytest tests/test_community_interactions.py -q`、`flutter test test/community/interactions_test.dart`。

### NC-026：行为事件数据源与假名化

- [ ] 新增 `SERVER/xuan/community/behavior_events.py`、`xuan/community/pseudonyms.py`、`xuan/handlers/analytics_events.py`、`tests/test_behavior_events.py`；新增 `CLIENT/lib/src/analytics/private_note_metrics.dart`、`test/analytics/private_note_metrics_test.dart`。在同一 3.1 OpenAPI 中增加 `POST /v1/analytics/events`（串行写入排在 NC-021 之后，见 [Plans §1.2](PLANS.md)）。写入白名单含 `SERVER/tests/conftest.py`（仅追加 `COLLECTIONS` 键）与 Firestore 安全规则文件。
- [ ] 沿用 NC-002 的机器 Schema 范式，为 BehaviorEvent、PseudonymMapping 补正反 Schema：负例逐项覆盖 [Design §11.2](DESIGN.md) 的禁止字段；`bev_`、`psn_` 前缀随 Design §2.1 一并取得用户确认。
- [ ] **服务端事件**：由 NC-009 的 command_service 在同一事务内追加，event_id 按 Design §11.2 确定性派生。测试：注入「业务写入后、事务提交前」异常，断言既无业务记录也无事件；事务回调重跑与同键重试后事件只有一条；rejected 命令不产生事件；Design §2.1.1 目录中每个 operation 在 committed 后恰有一条同名事件。
- [ ] **只追加**：Firestore 安全规则测试断言对 BehaviorEvent 的 update 与 delete 均被拒绝；静态扫描断言服务端代码中不存在对该集合的更新或删除调用。
- [ ] **假名**：断言 actor_pseudonym 由密码学安全随机数生成（同一 account_id 在两个独立测试库中得到不同假名）；事件集合中没有任何字段等于 account_id。
- [ ] **注销**：模拟宿主注销事件后，断言该账号的 PseudonymMapping 已删除、行为事件条数不变；扫描本系统全部集合，不再有任何字段等于该 account_id（公开内容与评论作者显示为「已注销用户」，Design §11.3 列出的个人记录已删除）；把逐集合处理清单写入工作包 README。注销事件来源取自 NC-001 登记的第⑩项，缺证时本子项保持 BLOCKED，其余子项继续。
- [ ] **私人笔记元数据（默认上报）**：`private_note.revision_saved` 与 `private_note.session_ended` 只含 Design §11.4 列出的字段；对上报请求的原始字节断言不含 fixture 笔记的标题、正文片段、附件名与 note_id 原值；char_count 按 code point 计数（含一个 4 字节字符的用例）；离线暂存超过 10,000 条时丢弃最旧事件，并在下一条上报事件中带 `dropped_before`；服务端按 event_id 去重，重复上报只存一条。
- [ ] 运行 `python3 -m pytest tests/test_behavior_events.py -q`（需 Emulator）与 `flutter test test/analytics/private_note_metrics_test.dart`。

## 5. 通知

### NC-013：业务投递与服务端通知契约

- [ ] 新增 `SERVER/xuan/community/notification_dispatch.py`、`xuan/handlers/community_deliveries.py`、`tests/test_community_deliveries.py`；扩展 NC-003 的同一 3.1 OpenAPI（串行顺序见 [Plans §1.2](PLANS.md)），接入既有 outbox 触发入口；写入白名单含 `SERVER/tests/conftest.py`（仅追加 `COLLECTIONS` 键）。
- [ ] **实现上游 notifier 明确不提供的两个端点**：通知正文拉取与 cursor 补拉（`OPENSPEC-PUSH-CELL` 已答复「⛔ notifier 给不出这个端点…请向上游业务子系统要」）。ACK/`/receipts` 属 notifier 的 3.0.3 契约，**只引用不复制**，本任务不在 3.1 契约中重定义。
- [ ] **R2-01**：业务 NotificationRecord.notification_id 按 Design §6 的 E 编码确定性生成 ntf_ ID，以 create-if-absent 去重；notifier_delivery_id 是上游原始不透明 deliveryId，严禁重命名/重算为业务 ID。实现 event+recipient → 多设备/用途投递的可信映射、账号/设备/当前 ACL 校验；NC-013 工作包必须附真实映射来源与契约证据，缺接口时登记上游扩展和失败停点，不允许构造 Fake 映射宣称接通。
- [ ] 显式声明并测试 at-least-once 语义（[Design §6.1](DESIGN.md)）：Firestore trigger 与外部推送均为 at-least-once，「原子」仅指投递记录终态写入一次；不得在任何文档或注释中声称 exactly-once。
- [ ] 推送重试状态与记录创建分离；`delivery_state` 走 `created / dispatching / delivered / failed / abandoned` 五态，退避 1s/2s/4s/8s 上限 5 次。评论/回复/@ 去重，无自通知；赞站内、偏好控制系统提醒，踩/收藏/分享不通知。
- [ ] 按 [Design §6.3](DESIGN.md) 实现聚合（默认 10 分钟窗口，@ 与直接回复不参与合并）与按内容静音（静音后该内容新评论不通知，但 @ 我的仍送达）。
- [ ] 验收偏好/拉黑/失权过滤、双触发并发、创建成功推送失败后的重试、正文当前权限、游标补拉、ACK 与已读分离。**`ReceiptRejected` 的 HTTP 映射不由本任务定义**（R1 修正）：`/receipts` 属 notifier 契约且已冻结为「整批原子，任一 id 失败则整批 4xx，调用方无法区分具体原因」，本任务遵守该口径，NC-014 负责客户端侧行为。
- [ ] 可观测性：投递记录创建到首次推送尝试 p95 < 5 s；补拉游标不回退。
- [ ] 运行 `python3 -m pytest tests/test_community_deliveries.py -q`（需 Emulator）。

### NC-014：Notification 生产适配与回跳

- [ ] 新增 `CLIENT/lib/src/notifications/community_notification_adapters.dart`、`notification_target_router.dart`、`test/notifications/community_notifications_test.dart`。**范围提醒（R1 修正，原估算严重偏低）**：`notification` 包文档明写「本包⛔不含任何具体 adapter」「你必须实现的 8 个端口」，本任务需实现全部 8 个端口的适配，不是 2 个 dart 文件；`BackfillSource` 与 `MessageBodyFetcher` 对应的服务端端点由 NC-013 提供。
- [ ] **实现原始 `deliveryId` 客户端去重表与 7 天裁剪窗口**（E-DEDUP）；业务列表另按 notification_id 唯一 upsert。测试同事件两设备、同设备不同用途各自原样 ACK；业务已存在仍须持久当前传输后 ACK 新 ID；落盘失败不 ACK/不推进游标。业务补拉不制造传输 ID 或无来源 ACK，越权 deliveryId 拉正文拒绝。
- [ ] 回跳挂靠哪一套 notification 表现层由 NC-001 指定（`social/lib/src/notification/notification_center_page.dart` 与 `notification/lib/src/notification_page.dart` 并存）。
- [ ] 使用同一持久接收管线处理实时/唤醒/补拉；落盘失败不 ACK、不推进 cursor；ReceiptRejected 整批终止并可观察，不任意重试 4xx，也不拆批探测（与 `ack_pipeline.dart` 既有行为一致）。
- [ ] **「落盘失败不 ACK」的真实证据定义**：必须有 fake 返回**失败**的分支，断言 cursor 未推进且 ACK 未发出；用一个永远返回 `DeliveryPersisted()` 的 fake 不算通过（接入指南正警告这一点）。
- [ ] 验收通知打开 content/thread/root/comment 的精确目标、账号切换、删除/收回后落到占位页：统一文案「该内容已不可访问」+ 返回按钮，**四种失效原因下页面文案完全一致且响应中不含可区分原因的字段**（PRD §6.2 决策）。
- [ ] 运行 `flutter test test/notifications/community_notifications_test.dart`；真实设备推送在 NC-024 用 NC-001 登记的设备单独验证。

## 6. 私人同步、备份与删除

### NC-015：恢复、设备授权和清理协议设计

- [ ] 新增 `SPEC/PRIVATE_SYNC_PROTOCOL.md` 与正反协议样例；读 STORAGE 真实 cipher/pairing/guard/row 网关，选成熟密码学组件与可恢复封装，不自创算法。
- [ ] 明确密钥生成/保存/授权新设备/全旧设备丢失恢复/吊销/epoch/密码改变；认证绑定 scope、设备 ID、指纹、有效期。不得仅凭现有 guard 返回 authorized 放行。
- [ ] **本任务是从零设计密码学协议，不是「复用」**：R1 核验确认 `xuan-storage/p2p/lib/device_key_store.dart` 只有单设备 Ed25519 身份种子（`_loadOrCreateIdentity/sign/verify/_fingerprintOf`），加密侧只有 `AesGcmBlobCipher`，**无 escrow、助记词、社会恢复或密钥分片任何原语**。Plans §3 的 30–60 分钟 ACT 粒度对本任务不适用，须按协议设计单独排期。
- [ ] 明确恢复材料的**产品形态**并落到 PRD 旅程 7（用户已确认：**支持事后重新导出**，需当前设备已授权 + 本地生物识别或设备密码二次验证）；含回填验证、未通过不启用备份、后果说明页不可跳过、截图与云剪贴板风险提示。
- [ ] 明确不可恢复失败行为（输入错误只提示「恢复材料不正确」，不提示错在第几位）、tombstone 保留窗口与离线重入、备份开关/删除/清理窗口、备份命令对 Design §7.4 账本恢复/结果精简规则的遵循。
- [ ] 「全部旧设备丢失」定义为**可执行步骤序列**供 NC-018 直接消费，例如：在设备 B 全新安装 → 清空 keychain 与应用数据 → 仅输入用户保存的恢复材料 → 期望能解密备份中 `nrev_3` 的正文与 `img_1`。
- [ ] 新增 `SPEC/tools/check_private_sync_protocol.py`。红条件：协议文档缺上述任一小节、或正反样例缺 `expected` 字段、或出现 `TBD`/`待定` 占位。运行该脚本退出 0。
- [ ] 以攻击/故障场景审查并经主 Agent 接受后解锁 NC-016～019；不能用一句「复用 E2EE」通过。

### NC-016：加密 mapper 与双设备同步

- [ ] 新增 `CLIENT/lib/src/storage/private_note_mapper.dart`、`private_note_sync.dart`、`test/storage/private_note_sync_test.dart`，在 STORAGE 必要导出点薄接线；私有/public 注册不同 entityType。
- [ ] **「密文无明文」是可先行的负向断言**（不依赖 NC-015 冻结），建议抽为独立子 ACT 先写红：对**序列化后的原始字节**断言 `contains(明文标题)` 为 false、`contains(明文正文片段)` 为 false；只断言「解密后可读」不算通过。
- [ ] 云/P2P 重复投递去重，双方分支保留；错误账号/指纹/过期/吊销在交换正文前拒绝。**必须实际比较 `peerDeviceId` 与 `peerFingerprint`**：R1 核验确认 `xuan-storage/core/lib/sync/same_account_im_reconciliation.dart` 的 `verifyPeerSession` 收下这两个参数却在五步校验中从不使用，类名 `SameAccountSessionGuard` 不是授权证据；修复该缺口需写 STORAGE，属 [Plans §1.2](PLANS.md) 白名单内的显式例外。
- [ ] 运行 `flutter test test/storage/private_note_sync_test.dart`；另建 `CLIENT/example/integration_test/private_device_sync_test.dart`，运行 `flutter test integration_test/private_device_sync_test.dart -d <NC-001 设备表中的 device_id>`，在**设备表登记的两台真实设备**上分别验证 LAN 与 WebRTC，各自记录证据。

### NC-017：密文云网关与完整备份

- [ ] **RW-4，依赖 NC-009 command_service，按 Design §7.4 验收**：backup.begin/complete/delete 的会话登记、manifest 激活、清理登记各在对应命令事务中写终态结果；对象传输仍在事务外。分别注入提交后响应前崩溃，原 command_id 重试只产生一个会话/一次激活或一个清理任务与对应事件；14 天结果精简后仍不重复写入，同键异载荷 409、未知状态保留原键。断言完整/精简账本、manifest 与事件实际记录；纳入 test_private_note_backups.py。

- [ ] 新增 `SERVER/xuan/handlers/private_note_backups.py`、`tests/test_private_note_backups.py`；新增 `STORAGE/firebase/lib/media/private_backup_blob_gateway.dart`（**建立在 NC-025 的生产网关之上**，不是又一个内存 fake），补同源 3.1 OpenAPI 中密文上传/完成/下载/删除 Schema（串行顺序见 [Plans §1.2](PLANS.md)）；写入白名单含 `SERVER/tests/conftest.py`（仅追加 `COLLECTIONS` 键）。
- [ ] 复用 bucket/Auth 基础，限定服务器推导 owner/path；密文对象全部存在/hash 匹配后原子激活完整 manifest。备份集合/路径/清理与 Playground 媒体及 relay 隔离。
- [ ] 运行 `python3 -m pytest tests/test_private_note_backups.py -q`（需 Emulator）；验收跨账号、路径篡改、部分上传、错 hash、重试幂等、清理失败可重试。**真实上传/下载证据必须另外提供**：真实 bucket 名、对象路径、跨账号取访问被拒的原始 HTTP 响应；内存 BlobGateway 不足。

### NC-018：备份 UI 与恢复验证

- [ ] 新增 `CLIENT/lib/src/storage/backup_controller.dart`、`backup_settings_page.dart`、`test/storage/backup_controller_test.dart`；新增 `CLIENT/example/integration_test/private_backup_restore_test.dart`。
- [ ] 验收首次选择/启用自动/关闭仅停新传/单独删除云备份；三个状态按 PRD §6.1 的取值表分开呈现（含「状态未知（离线）」与「已关闭（存量保留）」）；跨版本修订与图片依赖恢复完整。
- [ ] 实现 PRD 旅程 7/8：后果说明页不可跳过、恢复材料回填验证通过才启用、**事后重新导出入口**（设备已授权 + 本地二次验证）、新设备恢复的进度显示与中断续传、「暂不恢复」时明确告知云端备份仍保留且本设备新建笔记不会覆盖它。
- [ ] 按 PRD §5.1 实现「删除云备份」「关闭云备份」两个确认层，数量为运行时真实值；提供「仅 Wi-Fi 备份」开关并在首次开启时告知流量影响。
- [ ] 备份进度（PRD §6.3）：显示 n/m 与剩余量，可离开设置页后台继续，完成与失败各一次应用内提示；PARTIAL 态显示「已完成 8/12，其余可重试」。
- [ ] 运行 `flutter test test/storage/backup_controller_test.dart`；再运行 `flutter test integration_test/private_backup_restore_test.dart -d <NC-001 设备表中的 device_id>`，按 NC-015 给出的可执行步骤序列分别演练「原设备在场」与「全部原设备丢失」。**后者的真实证据定义**：销毁进程与本地密钥存储、仅凭用户保存的恢复材料重建，并记录两次运行的时间戳与设备标识；在同一进程内保留密钥对象后「恢复」不算通过，仅新生成密钥打不开旧数据的测试也不算。

### NC-019：30 天回收站与永久清理

- [ ] **RW-6，Design §7.4 命令恢复**：服务器 trash/restore/purge 复用 NC-009 command_service；逐项测试提交后响应前中断并原键重试。尤其 purge 提交后、响应前中断，以同键重试只产生一个清理任务与一条 purge 请求事件，不能推进第二次生命周期；后续清理进展事件另按任务阶段去重。客户端重启恢复原键，410/503 不换键，`pending_op=purge_requested` 表示客户端已发出、服务端未确认；服务端 `lifecycle=purge_pending` 仅表示清理任务已登记，`PurgeTask.state=succeeded` 之前不显示 purged。纯本地私人 trash/restore 仍使用本地事务，不伪造云命令。覆盖 test_community_purge.py 与 note_trash_test.dart。

- [ ] 新增 `CLIENT/lib/src/history/note_trash_page.dart`、`test/history/note_trash_test.dart`；新增 `SERVER/xuan/community/purge_service.py`、`tests/test_community_purge.py`，接入已冻结删除事件/备份清理。
- [ ] **30 天的 T0 分两类，边界用例须分别构造**（[Design §4](DESIGN.md)）：曾公开的内容从服务端 trash 事件 `server_time` 起算；从未公开的纯本地笔记从本地持久 trash 事件起算并在首次上线时以服务端时间校正（只推后不提前）。
- [ ] 测 30 天边界（可注入时钟，含第 30 天与第 31 天成对用例）、恢复保持私密、`purge_pending` 下 restore 返回 `409 conflict.lifecycle`、已公开离线删除时客户端 `pending_op=trash_requested` 且显示「正在停止公开，他人可能仍可访问」（禁止任何完成时态文案）、共享附件仍被引用时不删、清理重试、`PurgeTask.state=failed` 可重试且重试不产生第二个清理任务、旧离线设备不能复活已清理正文。
- [ ] 按 PRD §5.1 实现「彻底删除」确认层（含 N 个历史版本、M 张图片的真实数量与「已被他人保存的公开副本无法收回」）；回收站显示「剩余 N 天」，剩余 3 天内在列表提醒。
- [ ] 写入白名单含 `SERVER/tests/conftest.py`（仅追加 `COLLECTIONS` 键）。运行 `flutter test test/history/note_trash_test.dart` 与 `python3 -m pytest tests/test_community_purge.py -q`（需 Emulator）。**「云端清理完成」的真实证据**：清理后从云端 GET 返回 404 的原始响应；只断言本地 `deleted_at` 不代表清理完成。

## 7. 书籍与真实 Tooltip

### NC-020a：消费端书籍契约核对清单（可现在准备）

- [ ] 输入 `SPEC/../../docs/annotation-community/UPSTREAM_DATA_CONTRACT_REPLY.md` 与 `CONSUMER_ALIGNMENT_RESPONSE.md`（相对 SPEC 根为 `../../docs/annotation-community/`，此前裸路径不解析）。产出 `SPEC/BOOK_CONTRACT_ACCEPTANCE.md` 的**核对清单骨架**：逐条列出消费端需要上游冻结的项目及其判定标准，每项标注「已交付 / 未交付 / 有回执但未冻结」。
- [ ] 登记 D-07/D-08 对相关知识/流派入口的依赖，明确它们不阻断独立笔记。
- [ ] 新增 `SPEC/tools/check_book_contract.py`。红条件：清单中存在未标注状态的项、或把「有回执」标为「已冻结」。运行该脚本退出 0。

### NC-020b：上游书籍政策/Schema/D-06/样例冻结（BLOCKED）

- [ ] 由上游交付来源分型发布政策、共同 Schema/文件映射、D-06、多段选区/迁移规则和真实原件样例；核对结果回填 NC-020a 的清单。
- [ ] 抽查 EPUB 空格/脚注/图片与原件映射、重复句/跨块/补充平面字符、旧版/校订/拆分；确认原生来源 PUBLIC_RELEASE 门禁已在权威规范与验证器同时生效。
- [ ] 缺 Schema/样例保持 BLOCKED。不得仅因有回执就升级 ACCEPTED，也不在下游二次 OCR/切句。

### NC-021：对象上传、入库和版本激活

- [ ] 新增 `SERVER/xuan/handlers/library_imports.py`、`xuan/library/import_service.py`、`xuan/handlers/library_queries.py`、`tests/test_library_imports.py`，扩展同一 OpenAPI；输入仅 NC-020b 已冻结记录。
- [ ] 实现缺失对象登记、完整性核验、隔离分批装载、校验报告、作用域内原子 active 指针；保留历史修订查询。对象存储/Firestore 各自事务边界与恢复状态明确。
- [ ] 导入进度（PRD §6.3）：阶段（校验中 / 装载中 / 激活中）与进度可见，允许离开；失败时明确告知旧版本仍可正常阅读。批大小 500 条/批。
- [ ] 写入白名单含 `SERVER/tests/conftest.py`（仅追加 `COLLECTIONS` 键）。运行 `python3 -m pytest tests/test_library_imports.py -q`（需 Emulator）；验收漏文件/悬空引用/hash 错/dev 包拒绝、失败旧版可读、同 release 异清单拒绝、传输分片不变 block_id。真实对象中断恢复为必要补证。

### NC-022：原书阅读与原句注解

- [ ] 新增 `CLIENT/lib/src/reader/book_reader_page.dart`、`anchor_resolver.dart`、`annotation_controller.dart`、`test/reader/anchor_contract_test.dart` 与 `test/reader/annotation_flow_test.dart`。
- [ ] 使用 NC-020b 原生/扫描样例，固定版本取正文，Unicode 范围与 Python hash 对账，跨块与无知识 Span 正文可注解；原图/派生图能力分开显示，不制造 EPUB 页码/字框。
- [ ] 实现 PRD §6.5 的位置待确认旅程：创建时多处匹配须在带上下文的候选列表中确认（`AnchorResolution.state = ambiguous`）；「我的注解」提供「需要确认位置（N）」筛选入口；待确认时注解正文仍完整可读可编辑；处置动作至少「指认新位置」与「保留为无位置注解」两个；已公开注解进入待确认时他人只见引文与正文、无可点击定位、不显示内部状态词。
- [ ] 原书阅读页按页边标记显示哪些句子已有公开讨论及其条数（R-07 在原书这一侧的可发现性）。
- [ ] 运行 `flutter test test/reader/anchor_contract_test.dart test/reader/annotation_flow_test.dart`；旧注解保留原始 AnchorRef，歧义显示待确认，不取第一个同句命中。

### NC-023：Tooltip 真实链路原型

- [ ] 新增 `CLIENT/example/lib/tooltip_prototype_page.dart`、`CLIENT/example/integration_test/tooltip_discussion_test.dart`，只通过同一 DiscussionContext/REST/Notification 适配；不修改占卜盘面代码。
- [ ] 演练原句 → 原型讨论 → 回复/@ → 另一个账号通知 → 原书/原型定位同一 thread/comment；赞踩收藏分享及资料/私信路由使用真实宿主适配。
- [ ] 运行 `flutter test integration_test/tooltip_discussion_test.dart -d <NC-001 设备表中的 device_id>`，退出 0。**真实链路的证据定义**：记录服务端存储中的同一 `thr_*`/`cmt_*` ID、两个账号的 token 标识（不写入凭据原文）与通知投递记录；静态页面、mock JSON、纯按钮回调或知识关系未交付均不能通过。
- [ ] 定义原型每一步的返回行为（从讨论返回 Tooltip 保留滚动位置与已展开楼层）——DESIGN §6 说明它同时是 UI 调用协议，返回态属于协议的一部分。

## 8. 总验收

### NC-024：全链路验收与交接

- [ ] 新增 `SPEC/ANNOTATION_COMMUNITY_ACCEPTANCE.md`（与 gate §2 的工作包内 `ACCEPTANCE.md` 及未来的 `openspec/acceptance/run_all.sh` 总入口区分命名）、`CLIENT/example/integration_test/notes_full_flow_test.dart`，逐项映射 R-01～R-21 到提交、命令、真实数据与截图/录屏（适用时），不能只记录测试数。
- [ ] 主 Agent 复核所有子包依赖、范围、原始证据与失败路径；检查 Undo/Redo/IME、重启、云恢复、ACL 全入口、并发评论/outbox、双入口和修订迁移。
- [ ] 无障碍总验收（PRD §4.1）：A11Y-01～09 逐条给证据，含纯键盘走完发布全程、读屏朗读三态与撤销禁用态、320/375/414 × 100%/200% 快照、灰阶下失败态可识别、深浅两模式。
- [ ] 新增 `SPEC/tools/check_r_coverage.py`。红条件：R-01～R-21 中任一项在 `ANNOTATION_COMMUNITY_ACCEPTANCE.md` 里缺 commit / 命令 / 证据三元组。运行 `python3 SPEC/tools/check_r_coverage.py` 与 `flutter test integration_test/notes_full_flow_test.dart -d <NC-001 设备表中的 device_id>`，均退出 0。
- [ ] 更新各工作包验收、总表与 `SUBAGENT_TODO.md`；未完成项保持未勾选。输出配置/部署/迁移/恢复说明及准确版本组合，不把 F 项算本期欠交，也不把 E 依赖未完成隐藏掉。

## 9. 后续版本登记（当前不执行）

- [ ] F-01：完整键盘操作设计（自定义快捷键、快捷键配置、跨页面键盘导航方案）。**当前缺失；本期仅撤销/重做。** 后续单独做需求与设计，本次不提供额外按键表、不实现配置框架。**无障碍不在 F-01 范围内**：PRD §4.1 的 A11Y-01～09 是本期承诺项，由各 NC 分别验收。
- [ ] F-02：原书与 Markdown 分屏、**原书**阅读分页体验。讨论区评论分页 UI 属本期（PRD §6.3）。
- [ ] F-03：Markdown 引文点击定位原书。
- [ ] F-04：高亮/圈画/手写图形标记，评估 notebook 图元能力。
- [ ] F-05：通用附件、复杂富文本与实时协作，另行确定范围。

本文件为开发任务定义，不是完成报告；代码、Schema 和测试均应通过各自 READY 工作包执行。用户后续变更必须在 [PRD §9 变更记录](PRD.md) 登记，并回写 PRD/Design/Plans/Tasks 的对应 R-xx / NC-xxx，保持四份文档一致；状态流转同步更新 `SUBAGENT_TODO.md`。

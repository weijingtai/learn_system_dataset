# 注解社区线文档 R1 审查缺陷登记

版本：1.0；2026-09-10。状态：`APPROVED_DESIGN`；执行状态：`NOT_STARTED`。
审查对象：[PRD](PRD.md) / [Design](DESIGN.md) / [Plans](PLANS.md) / [Tasks](TASKS.md) 的 v1.0。
审查角色：OpenSpec 规范审核官、用户体验官、BDD/TDD 就绪度审核官、技术契约与落地可行性审核官（四角色并行只读审查）。
处置结果：四份文档升版至 v1.1。本文件是缺陷台账，不是完成报告。

## 0. 结论

四角色初审**全部否决**进入 BDD/TDD 阶段。共 43 条阻断级缺陷（去重后 37 条独立问题），已在 v1.1 中处置。

修订后的判断：**NC-001 / NC-002 / NC-003 / NC-015 / NC-020a / NC-025 六项可立即进入 BDD+TDD 编写**；NC-004～NC-014 待 NC-002/003 冻结后写字段级 TDD，此前只写 BDD 与测试骨架；NC-016～NC-019 待 NC-015；NC-020b～NC-024 待上游书籍契约。

## 1. 已在 v1.1 处置的阻断级缺陷

### 1.1 用户体验（12 条）

| ID | 缺陷 | 处置 |
|---|---|---|
| UX-01 | 设备同步/云备份两个状态的取值集合、离线未知态未定义，「UI 分开三个状态」无法断言 | PRD §6.1 三态取值表；NC-005/NC-018 验收点 |
| UX-02 | 24 种内部状态组合未映射成用户语言；「待收回 vs 已收回」等三对高危混淆 | PRD §6.2 封闭状态词表（作者视角/他人视角双列） |
| UX-03 | 冲突合并无入口、无出口、无「稍后再说」 | PRD 旅程 6；NC-007 验收点 |
| UX-04 | 五个不可逆动作零确认定义（全文「二次确认」零命中） | PRD §5.1 确认规范；NC-010/018/019 验收点 |
| UX-05 | 恢复材料 UX 被下放给密码学任务，且形态/能否跳过/能否事后再看无产品决策 | **用户决策：支持事后重新导出**；PRD 旅程 7/8；NC-015/NC-018 验收点 |
| UX-06 | 离线待提交操作无全局入口、失败后静默丢弃 | PRD 旅程 9；NC-010 验收点 |
| UX-07 | 空态/加载态/部分成功态全缺席，未复用仓库既有七状态必答矩阵 | PRD §6.4 |
| UX-08 | 无障碍全文零命中，与仓库已批准决议 D-012 直接冲突且未申请豁免 | **用户决策：本期承诺完整基线**；PRD §4.1 的 A11Y-01～09；NC-005/NC-024 验收点 |
| UX-09 | 限额已埋下必然卡顿场景，却无任何时延或进度要求 | PRD §6.3；NC-008/018/021 验收点 |
| UX-10 | 通知目标失效落地页未定义；通知洪水无抑制手段 | **用户决策：统一文案不区分原因**；PRD §6.2、Design §6.3；NC-013/014 验收点 |
| UX-11 | 发布预览是死胡同，被拒后无返回路径 | PRD 旅程 3；NC-010 验收点 |
| UX-12 | 注解「歧义待处理」只定义进入不定义离开 | PRD §6.5；NC-022 验收点 |

UX-13～UX-28（重要但不阻断）已按类别并入 PRD §6.5/§6.6、Design §9.1 与各 NC 验收点，未单独列出的属体验优化建议，登记为后续迭代候选。

### 1.2 OpenSpec 规范（6 条）

| ID | 缺陷 | 处置 |
|---|---|---|
| A-1 | 24 个 NC 未登记进仓库唯一监控表 `SUBAGENT_TODO.md`，形成第二套状态源 | Tasks 头部声明「定义源在本文件、流转状态以 SUBAGENT_TODO 为准」，并在该表新增「NC 注解社区线」章节 |
| A-2 | 自造 `BACKLOG`/`BLOCKED` 释义，与门禁 §7 七值枚举冲突；无状态流转落位 | Tasks 直接引用门禁枚举；总表列名改「初始状态」并说明流转位置；verify.sh 断言状态值属于七值枚举 |
| A-3 | 15 类新 UGC 对象 ID 格式未冻结、未提请用户确认、无任务负责 | Design §2.1 给出 15 个前缀与五条非法格式判定；NC-002 新增「取得用户确认」勾项，未确认前保持 `PREPARING` |
| A-4 | NC-002 只产 Markdown 契约与 fixture，无机器 Schema、无校验命令，红灯立不起来 | NC-002 改为落位 `openspec/schemas/*.schema.json` + `examples/<obj>.valid\|invalid_*.yaml` + 追加 `verify.sh` 成对判据 |
| A-5 | E-BOOK/E-CRYPTO/E-WIRING 全仓只出现一次，无承接任务，PRD「有负责任务」不可核验 | PRD §8 改为依赖表并标注承接任务；新增 E-NOTIFIER/E-BLOB/E-DEDUP；verify.sh 断言每个 E-* 行含 NC 编号 |
| A-6 | 6 个 NC 无可执行验证命令，其中 4 个是阶段解锁闸门 | NC-001/002/015/020a/023/024 各补扫描或集成命令与退出码 |

B-1～B-8、C-1～C-7 中，已处置：DESIGN 章节加 R-xx 追踪（B-1）、TASKS 用完整 R ID（B-2）、四份文档状态值改双行式（B-3）、新增 `verify.sh`（B-4）、NC-024 独立成 §8（B-6）、渲染库选型依据移入 NC-001（B-7）、NC-020 拆 a/b（B-8）、`ACCEPTANCE.md` 更名（C-2）、DESIGN 补 PLANS 链接（C-4）、NC-020 路径改用根标记（C-5）、PRD 新增变更记录章（C-6）、状态枚举取值补全（C-7）。

**未处置并说明理由**：B-5 建议把 PLANS/TASKS 迁出 `openspec/`。四份文档是用户明确要求的一组交付物，拆散存放会破坏阅读顺序与相对链接；本版改为在各文档头部标注执行状态 `NOT_STARTED`，以状态字段而非目录位置表达「尚非最终获批规格」。C-1/C-3（工作包目录命名、fixture 路径层级）已在 Plans §1 一句话说明 `nc-` 为本线新前缀，不再改动既有工作包命名。

### 1.3 BDD/TDD 就绪度（15 条）

| ID | 缺陷 | 处置 |
|---|---|---|
| BT-01 | 错误码目录不存在；「403 或 404」二义已被抄进 NC-009 | Design §7.3 错误目录（唯一 HTTP + 唯一 code + 附加字段）与 403/404 边界规则；NC-003/009 验收点 |
| BT-02 | 五个关键状态字段只有字段名无枚举值 | Design §2 表内联枚举 + §2.2 状态机总览；NC-002 产出 `state-machines.md` |
| BT-03 | 编辑态转移未穷举，`save_failed` 无出边 | Design §3 全转移表（含 `pending_dirty`、`ime_composing`） |
| BT-04 | 3×4×2 状态交叉合法性未定义；UI 出现枚举外的第四组「待处理」态 | Design §4.1 组合白名单 + §4.2 客户端 `pending_op` 字段 |
| BT-05 | 并发胜负规则缺失（收回 vs 评论、快速赞踩） | Design §4.4 写死：`409 conflict.access_version`；`client_seq` 单调判定 |
| BT-06 | 全部限额缺边界闭合语义；本地超限无可观察输出 | Design §7.1 边界表（恰好等于/超一单位/观察点） |
| BT-07 | 计量口径未定：code point vs UTF-16、加密前 vs 加密后 | Design §7.1 口径列；NC-002 强制 emoji fixture |
| BT-08 | content_hash canonical 编码未定义；fixture 有生产者无消费者 | Design §7.2 冻结编码；NC-002 指定 Python/Dart 两个消费者与 parity 测试 |
| BT-09 | 五个任务（含首批三个）完全无验证命令 | NC-001/002/015/020a/024 各补扫描脚本与退出码 |
| BT-10 | SERVER 测试前置未定义：实测需局域网 Emulator；`conftest.py` 不在任何白名单内 | Plans §4 前置环境栏；Plans §1.2 与 Tasks §1.2 把 `conftest.py` 纳入七个任务的白名单（仅允许追加 `COLLECTIONS` 键） |
| BT-11 | NC-016/018/023 引用了 NC-001 从未承诺的「两台真实设备」 | NC-001 新增设备清单表与测试后端表；三个任务的命令改为带 `-d <设备表 device_id>` |
| BT-12 | Undo 归组规则「合理」不可判定，等于用实现定义验收 | Design §3.1 三条件阈值（<500 ms、不跨空白、≤20 字符）+ 基准断言 |
| BT-13 | 撤销栈归属未决，NC-006 测试面本身不确定 | Design §3 裁定方案 b（adapter 为唯一真源，禁用平台 `UndoHistory`）；裁定动作前移到 NC-005 |
| BT-14 | R-20 出现在 11 个任务里却无 ACL 全入口测试所有者 | NC-009 新增 `test_community_acl_sweep.py`（6 入口 × 3 原因 = 18 条）；PRD §3.1 指定所有者 |
| BT-15 | mention 失效判定谓词未定义 | Design §6 三元组 + 子串等值判定；NC-002 四类无效 mention fixture |

BT-16～BT-23 已处置：总表新增「BDD/TDD 就绪度」列（BT-16）、NC-001 冻结 SDK 与生成命令（BT-17）、验证器选型上移至 NC-001（BT-18）、Design §9.1 非功能指标（BT-19）、安全测试所有者（BT-20）、可观测性所有者（BT-21）、NC-024 依赖补全（BT-22）、回收站 T0 分两类（BT-23）。

### 1.4 技术契约与落地可行性（10 条）

| ID | 缺陷 | 核验证据 | 处置 |
|---|---|---|---|
| TC-01 | Plans「外部项目本轮只读」与表内 5 行要求写入外部仓库自相矛盾 | 同表 SERVER/STORAGE/SOCIAL/REST 均写「新增/修改」 | Plans §1 限定「本轮＝文档交付轮次」；新增 §1.2 写入所有权 |
| TC-02 | 第 8 个仓库 `xuan-server/notifier` 缺失；存在两份互斥权威 OpenAPI（3.0.3 vs 3.1.0） | `notifier/api/openapi.yaml` 首行 `openapi: 3.0.3`；`notification/docs/from-server-coder.md` 明写「⛔不复制契约正文」 | Plans §1 增列 NOTIFIER（全程只读）；Design §6.2 拆分权威来源；§7 表拆行 |
| TC-03 | outbox→投递语义未声明，与上游已冻结的 at-least-once 口径不一致 | `OPENSPEC-PUSH-CELL.md`「⛔ **永不**声称 exactly-once」「7d 客户端去重窗口」；`dedup_retention_ms` 未实现 | Design §6.1 显式声明；NC-014 承接 deliveryId 去重与 7 天裁剪；新增 E-DEDUP |
| TC-04 | 生产 BlobGateway 不存在，R-15 的真实链路无任何任务拥有 | `blob_gateway_firebase.dart:1-5`「真云端实现未交付…本类为内存 fake」 | **新增 NC-025**，置于 NC-008/017 之前；新增 E-BLOB |
| TC-05 | 「原子变化」在现有 Python 栈中无先例且结构上不可达 | `idempotency.py:87-89` 注释「刻意放在事务外」；`posts/replies/likes.py` 全无事务 | Design §4.3 新增「原子边界」列（事务内/事务外/中间态可见性）+ §7.4 跨系统一致性模型 |
| TC-06 | 幂等键 TTL 60 分钟，与 R-16 离线待发直接冲突 | `idempotency.py:46` `ttl_minutes=60`，过期「当作不存在」 | Design §7 冻结社区资源 TTL 为 14 天；NC-003 写入契约 |
| TC-07 | 两处 BACKLOG 任务隐藏依赖 BLOCKED 产物 | NC-009 的 tombstone 窗口、NC-004 的 outbox 信封均由 NC-015 冻结 | 两者补 NC-015 依赖，或在 README 二选一写明拆分方案（Tasks §1.1） |
| TC-08 | 同一 `openapi.yaml` 被四任务写入，无串行化声明 | NC-003/013/017/021 | Plans §1.2 固定串行顺序 NC-003 → NC-013 → NC-017 → NC-021 |
| TC-09 | 修正 `operation.headers` 必然弄红既有测试，基线未定义 | 35 处 `headers:` / 0 处 `in: header`；`openapi_validation_test.dart` 8 处断言**要求**该非法形式 | 该文件进入 NC-003 白名单；README 记录改前基线；迁移作为独立 ACT 步骤 |
| TC-10 | 「真正 OpenAPI 3.1 验证器」在 Dart 宿主内选型不可行，离线策略缺失 | REST 仓依赖仅 `http/meta/yaml`，`tool/` 不存在 | 选型上移至 NC-001 由主 Agent 指定实值；NC-003 Red fixture 强制「故意非法的 3.1 文档必须非零退出」 |

技术契约官另核验通过：16 处相对链接全可达、六个既有根路径全部存在、依赖图无环、六件套格式与门禁 §2 逐字吻合、`RecordOutboxMapper` 明文序列化属实、`SameAccountSessionGuard` 缺口属实、`replies.py` 的 depth/root 校验可复用、`notebook` 确为排盘图元模型、`xuan-migration/learn_system` 确非 Flutter 包。

## 2. 防假性完成的真实证据定义

以下验收点最容易被 mock/fake 蒙混，已在对应任务写入证据定义：

| 验收点 | 蒙混方式 | 已写入的真实证据要求 | 任务 |
|---|---|---|---|
| 真对象访问 | 直接用 `InMemoryFirebaseBlobGateway`（import 路径看起来完全正规） | 真实 bucket 名、对象路径、**另一账号 token** 取票据被拒的原始 HTTP 响应 | NC-008, NC-017, NC-025 |
| 原子变化 | 顺序写多个 doc 后只断言最终状态 | 在第 2 写与第 3 写之间**注入异常**，断言无半持久状态或有补偿记录 | NC-009 |
| 投递幂等 | 照抄既有 query 查重 + 随机 doc ID | doc ID 由 `(event_id, recipient_id)` **确定性派生**，并发双写第二次 already-exists | NC-013 |
| 落盘失败不 ACK | 用永远返回 `DeliveryPersisted()` 的 fake | fake 返回**失败**的分支，断言 cursor 未推进且 ACK 未发出 | NC-014 |
| 序列化无明文 | 只断言解密后可读 | 对**序列化后的原始字节**断言不含明文标题与正文子串 | NC-016 |
| 全旧设备丢失恢复 | 同一进程内保留密钥对象后「恢复」 | 销毁进程与本地密钥存储，仅凭恢复材料重建，记录两次运行时间戳与设备标识 | NC-018 |
| 云端清理完成 | 只断言本地 `deleted_at` | 清理后从云端 GET 返回 404 的原始响应 | NC-019 |
| 真正 OpenAPI 验证 | 再写一个 yaml 字段检查器（既有测试正是这么做的） | 一份故意非法的 3.1 文档，验证器必须非零退出 | NC-003 |
| 真实 Tooltip 链路 | 静态页 + mock JSON | 服务端存储中的同一 `thr_*`/`cmt_*` ID、两账号 token 标识、通知投递记录 | NC-023 |

## 3. 待用户确认的遗留项

| 项 | 说明 | 阻断范围 |
|---|---|---|
| UGC ID 前缀 | [Design §2.1](DESIGN.md) 的 15 个前缀需按仓库既有范式取得用户确认后冻结 | NC-002 不得离开 `PREPARING`，进而阻断全部模型与 Schema 工作包 |

已确认的三项产品决策（2026-09-10）：无障碍本期承诺完整基线；恢复材料支持事后重新导出；内容失效对他人统一文案不区分原因。详见 [PRD §9 变更记录](PRD.md)。

## 4. 校验

运行 `bash openspec/annotation-community/verify.sh`，退出码 = FAIL 条数，0 表示文档层结构与交叉引用全部通过。该脚本只证明文档一致性，不证明业务可用。

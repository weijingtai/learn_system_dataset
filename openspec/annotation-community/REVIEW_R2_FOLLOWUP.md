# v1.1 补充复核记录

日期：2026-09-10。状态：`DOC_REVISED_PENDING_REVIEW`。
对象：提交 `9e6793a` 的四份文档及 R1 结论。范围：针对用户贴出的审核报告，核对实际提交、现有校验器及关键接入语义；不是重新跑全部四角色审核，也不是业务实现验收。

## 1. 结论

v1.1 已实际落盘，新增状态、无障碍、环境和契约归属等内容有价值。重跑 `bash openspec/annotation-community/verify.sh` 返回 0，但它主要检查文件、引用、枚举存在和依赖图，不覆盖下列语义。

不能据此给出“只剩 15 个 ID 前缀确认即可全部展开字段级 TDD”的结论。先处理受影响协议；不阻止 NC-001 环境调查或独立 BDD 场景准备，不新增无依据的整体停工条件。

## 2. 原始发现（v1.1 历史证据，处置见 §4）

| 编号 | 级别/位置 | 核验发现 | 修订方向及验收 |
|---|---|---|---|
| R2-01 | P1；DESIGN §2.1、§6；NC-002/013/014 | 为 Delivery 冻结 dlv_32hex，同时将 delivery_id 交给现有 Notification ACK；notifier 实际规定 deliveryId 是 HMAC(key,eventId\|deviceId\|channelPurpose) 不透明值。业务 event+recipient 投递记录与设备/channelPurpose 投递不是同一身份，现设计没有明确映射 | 业务通知 ID 与 notifier deliveryId 分字段；后者由 notifier 返回，客户端原样保存/ACK。定义一对多关系与正文解析授权。测试同业务事件两设备投递，各自 ACK 原始 ID，不改写为 dlv_ |
| R2-02 | P1；DESIGN §2、§4.4；NC-012 | Reaction 取消即删除该行，client_seq 却在该行且服务端依赖 last_applied_seq；删除后在哪里保留高水位未定义。不同设备计数和客户端重启也缺作用域规则 | 将命令排序/去重元数据与当前 reaction 值分离，或采用服务器 revision 前置条件；明确设备 epoch 与跨设备并发语义。测试 like(seq1)→none(seq2)→重试 seq1、重启和两设备同 seq，旧值不复活且新设备不永久被拒 |
| R2-03 | P1；DESIGN §4.3/§7.4；NC-003/009/011 | 现 with_idempotency 是先 claim、事务外 fn、再写 result；业务提交后结果回填前崩溃可留下 running。14 天 TTL 只是延长记录寿命，没有定义恢复已提交命令结果；过期后重放仍可能新建评论 | 定义持久 command_id 与业务结果关联，在同一 Firestore 事务内保存业务记录/事件及可恢复结果；外部对象上传仍在事务外。明确 running 恢复和超期查询结果后再决定重试；测试业务提交后强制中断、响应丢失、TTL 后重试，只有一个评论/事件 |
| R2-04 | P1；DESIGN §7.2；NC-002/004/007 | content_hash 公式只含 title、markdown、attachment_ids、mention_user_ids，漏 bindings/原句 selector，也没有结构化 mention 位置；只改原句绑定而正文不变会得到同一 hash，与“有效修改保存新修订”冲突 | 分开正文摘要与完整修订等价判断，或把所有可编辑语义字段纳入版本化 canonical 编码。测试只改 binding/selector/mention 位置时仍保存新修订；只改同步进度不产生正文修订 |
| R2-05 | P1；DESIGN §4.4；NC-009/011 | “收回 vs 评论，冲突方一律失败，评论不先成功再隐藏”没有覆盖评论先提交、随后收回的合法串行情况。Firestore 事务读取权限版本不天然产生该指定 409，也不能撤销已经成功的更早评论 | 按事务提交顺序定义：收回先提交则后续评论拒绝；评论先提交可成功，随后收回隐藏整个主题。若期望乐观版本拒绝须显式请求字段/错误映射；测试两种受控提交顺序及事务回调重试，不要求阻止所有合法串行写入 |

## 3. 原始证据与推论边界

- `/Users/jingtaiwei/Git/Public/xuan-server/notifier/api/openapi.yaml:841` 明确定义 HMAC deliveryId；本文未修改该权威契约。
- `/Users/jingtaiwei/Git/Public/xuan-server/functions-py/xuan/idempotency.py:41` 至函数末尾显示 claim/业务/result 三步；不声称“业务事务不可能实现”，而是现包装器不能自动提供崩溃恢复，必须新增明确实现。
- DESIGN §2 的 Reaction 行与 §4.4、§7.2 公式可直接对照；这里指出规范缺失，不声称尚未编写的新实现已发生故障。
- 现行 `learn-system-blackbox-architecture.md` §8.1 记录的是六类黑箱 ID 已获用户确认；不能仅凭这段历史扩大为“所有 APP 字段命名必须再次逐项请用户批准”。用户已授权常规工程设计。无论审批方式如何，R2-01 说明当前 15 项 ID 表不宜原样整体冻结。
- 原 R1 台账同时写 NC-015/025 可立即写 BDD+TDD，而 TASKS 总表分别写待协议格式/NC-003；需区分“可写场景、负例和测试计划”与“可冻结字段级可执行测试”，不能把两种就绪度混为一谈。

## 4. 修订处置与状态

2026-09-10 按用户授权将 R2-01～05 写回 PRD/DESIGN/PLANS/TASKS v1.2；五项均为 `DOC_REVISED_PENDING_REVIEW`，未声明独立复核通过或业务实现完成。

- R2-01：DESIGN §2/§6.2.1，业务 notification_id 与 notifier_delivery_id 分开；可信映射缺证保留接入前置。
- R2-02：DESIGN §4.4，取消保留版本，服务器 If-Match 与持久队列替代设备序号。
- R2-03：DESIGN §4.3/§7.4，命令终态与业务同事务；14 天仅精简结果，不清去重身份。
- R2-04：DESIGN §7.2，nchash/v2 覆盖完整可编辑语义，恢复/合并不按同文折叠。
- R2-05：DESIGN §4.4，按提交先后区分合法成功与失权拒绝，不把事务重跑强制映射成 409。

关联 NC 已补齐反例和写入范围；另一位 Agent 可直接使用 [简短复核清单](REVIEW_R2_CHECKLIST.md)。R1 历史报告保持原样；现行规则以 v1.2 为准，verify.sh 的结构通过不能替代语义复核及以后真实实现验收。

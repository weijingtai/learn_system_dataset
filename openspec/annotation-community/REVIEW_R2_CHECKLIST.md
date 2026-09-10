# R2 五项修订复核入口

日期：2026-09-10。状态：`DOC_REVISED_PENDING_REVIEW`。请只读复核现有 PRD、DESIGN、PLANS、TASKS v1.3，逐项回答“通过/不通过＋文件章节证据＋残余问题”。历史发现保留在 [R2 记录](REVIEW_R2_FOLLOWUP.md)，本清单不代表实现验收通过。

| 项 | 检索入口 | 必须反证的场景 |
|---|---|---|
| R2-01 通知 ID | DESIGN §2/§6.2.1；NC-002/013/014 | 同业务事件多设备/用途：业务列表一条，各自原始 deliveryId ACK；不能用 dlv_ 替代；可信映射来源缺证必须保留接入阻断 |
| R2-02 赞踩 | DESIGN §4.4；NC-012 | like→取消→旧 like 重试、重启、两设备同基线竞争；取消后 version 保留，旧响应不能回滚 UI |
| R2-03 命令恢复 | DESIGN §4.3/§7.4；NC-003/009/011 | 业务提交后响应前崩溃、响应丢失、14 天后重试；同键只产生一份业务/事件；账本与业务同事务，不能只延长旧 TTL |
| R2-04 完整修订 | DESIGN §7.2；NC-002/004/007 | 只改 binding/selector/mention 位置/图片 alt 仍建修订；键序/同步进度不改 hash；恢复同文新 ID；Python/Dart 共用固定期望值 |
| R2-05 提交顺序 | DESIGN §4.4；NC-009/011 | 收回先提交→评论拒绝；评论先提交→成功后随收回隐藏；仍可读旧权限版本→409；事务重跑不能被误判为必然 409 |

运行 `bash openspec/annotation-community/verify.sh` 与 `git diff --check`，但结构检查通过不能替代上述语义核对。请搜索四份正文是否残留 `client_seq`、取消删除状态行、超期同键视为新请求、幂等结果事务外回填、并发一律 409 等旧要求；历史审查记录中的引用不算现行规范。

此次只修文档。机器 Schema、真实 notifier 映射、Firestore 故障注入、跨端 hash fixture 尚待对应任务交付；不要将文档修订直接标成业务 READY/ACCEPTED。PRD 产品范围、完整键盘方案 F-01 后置及其他上游依赖保持原边界。

本轮复核重点：按 [独立复核报告 §4](REVIEW_R2_RESULT.md) 检查 RW-1～6；先运行 `bash openspec/annotation-community/review_r2_guard.sh`。同时确认顶层集合排序没有误排有序 selector、系统摘要不污染用户说明、备份与删除任务确实消费命令服务；已通过的 R2-01/02/05 做回归核对。

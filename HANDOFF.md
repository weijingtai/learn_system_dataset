# HANDOFF

## 上下游生产交付核对

更新时间：2026-09-09（环境日期）
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：两份消费协议的只读并行核对及主线程证据复核，逐项回执见 `docs/annotation-community/UPSTREAM_DATA_CONTRACT_REPLY.md`。
进行到一半的事（精确到文件和章节）：U/A 回执为协调建议，未改写消费草案或发布政策；尚无真实生产包和云端联调证据。
下一步（第一件事）：联合确认纯 EPUB/TXT 的生产证据要求，再收敛 D-06 选区/迁移与共同交付 Schema。
已知的坑：当前 PUBLIC_RELEASE 强制字框；旧 unit 编号按排序重建；OCR corpus 导出不含完整定位资产。当前有其他 Agent 并发修改协调文档与草案，提交只包含本次回执及本节增补。

## 注解社区线交接（独立于下方 G3 线）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：三位 Terra 只读调研存储、社交通知、客户端/Repository，主 Agent 核对关键代码；新增 `docs/annotation-community/MODULE_REUSE_AUDIT.md` 与 `CLIENT_SERVER_DESIGN_DETAIL_DRAFT.md`，同步私人存储、主数据草案和冷启动文档。
进行到一半的事（精确到文件和章节）：书籍主草案 §9 U-01～U-09 与资产稿 §6 A-01～A-06 等上游；非书籍部分已形成接入细化但未冻结。自动保存 2 秒、回收站 30 天、图片本期/通用附件后置均为候选，不冒充用户已批准。本轮不写业务实现或机器 Schema。
下一步（第一件事）：审阅接入细化稿；补齐密钥恢复/设备授权协议与候选默认值，再冻结正式规格/OpenAPI/工作包。书籍回执独立推进；不再等待已离场的 storage/social/notification 开发 Agent。
私人存储新发现：有真实 Firestore/RTDB row SDK 和 generic upsert，但当前 RecordOutboxMapper 明文 JSON 不能用于私人正文；云 blob 生产适配、长期备份和跨设备密钥恢复未见完整实现。IM guard 当前未比较传入设备 ID/指纹，不能直接当笔记授权证明。
已知的坑：Notification 管线有实现，生产业务接线不足；ReceiptRejected 是停止整批并报告；旧通知查重非原子且不适用多收件人。notebook 保存覆盖旧 committed，内存降级仍返回成功，不可当永久修订库。既有 OpenAPI 有 operation headers 非规范结构，字段断言测试不代表合规。D-06 未冻结；收回只能阻止后续访问，公共媒体不能发绕过 ACL 的永久 URL。

## G3 线原交接

更新时间：2026-09-09（G3 R1 返工完成 4/7，可从 D-07 接力）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：T-04、T-06、T-11、T-13 已补语义门禁、完成负向变异并由主 Agent 验收；提交见 `docs/blackbox-spec-rework/work-items/g3-r1/ACCEPTANCE.md`。
进行到一半的事（精确到文件和章节）：G3 R1 为 4/7；D-07、T-07、T-08 尚未执行，工作区无未提交半成品。
下一步（第一件事）：按 `docs/blackbox-spec-rework/work-items/g3-r1/REMAINING_PROMPT.md` 创建并执行 D-07 六件套；D-07 验收后再串行 T-07 → T-08。
已知的坑：T-07/T-08 旧提交虽让旧脚本全绿，但依赖 D-07 未冻结，不能恢复 ACCEPTED；总门禁 0 仍不能替代负向变异和语义审查。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。

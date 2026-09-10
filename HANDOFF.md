# HANDOFF

## 注解社区 v1.2 五项协议修订（优先于下方历史结论）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：用户授权的 R2-01～05 已写回 PRD/DESIGN/PLANS/TASKS，更新 REVIEW_R2_FOLLOWUP.md 并新增 REVIEW_R2_CHECKLIST.md 简短复核入口。
进行到一半的事（精确到文件和章节）：五项状态为 DOC_REVISED_PENDING_REVIEW；未编写业务实现、机器 Schema 或实测 fixture。
下一步（第一件事）：另一位 Agent 按 openspec/annotation-community/REVIEW_R2_CHECKLIST.md 只读复核；再准备相应 NC 工作包。
已知的坑：可信 notifier ID 映射仍需真实契约证据；上游 selector 类型与密钥协议前置保持，不凭结构检查关闭。其他 Agent 的 G3 工作不在本次修订范围。

## 注解社区线四份文档 R1 审查与补全

更新时间：2026-09-10（环境日期）
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：以四个只读角色（OpenSpec 规范、用户体验、BDD/TDD 就绪度、技术契约可行性）并行审查 `openspec/annotation-community/` 的 PRD/DESIGN/PLANS/TASKS v1.0，共 43 条阻断级缺陷（去重后 37 条），全部在 v1.1 中处置；新增 `REVIEW_R1.md` 缺陷台账与 `verify.sh` 结构校验器（FAIL 0）；24 个 NC 任务已登记进唯一监控表 `docs/blackbox-spec-rework/SUBAGENT_TODO.md` 的 G6 节，并新增 NC-025、拆分 NC-020a/b。
进行到一半的事（精确到文件和章节）：`DESIGN.md` §2.1 的 15 个 UGC ID 前缀标为「需用户确认后冻结」，未确认前 NC-002 不得离开 `PREPARING`；四份文档尚无任何工作包六件套，也无 READY 任务。
下一步（第一件事）：取得用户对 `DESIGN.md` §2.1 UGC ID 前缀的确认，然后按 `PLANS.md` §5 的首批顺序为 NC-001 生成工作包六件套。
已知的坑：`xuan-server/functions-py/tests/conftest.py` 强制局域网 Emulator（192.168.0.165），且此前不在任何任务白名单内；`repository-rest-adapter` 既有 `openapi_validation_test.dart` 有 8 处断言要求非法的 operation 级 `headers:`，修正结构必然弄红；`xuan-storage` 的 firebase BlobGateway 自述为内存 fake，生产实现由新增的 NC-025 承接；`xuan-server/notifier` 是文档此前未提及的第 8 个仓库，持有 3.0.3 权威契约，与本系统 3.1 契约必须分开。

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
刚完成：按用户要求输出 `openspec/annotation-community/PRD.md`、`DESIGN.md`、`PLANS.md`、`TASKS.md`，包含确认默认规则、Undo/Redo、24 个本期工作项及需求/依赖/测试映射；完整键盘方案标为当前缺失且后续 F-01 承接。旧接入细化标为历史输入，冷启动入口更新。
进行到一半的事（精确到文件和章节）：四份总文档已产出；未生成机器 Schema/OpenAPI 或 READY 六件套，未写业务代码。书籍 U/A 和密钥恢复仍是明确前置任务，不再将自动保存/回收站/图片等已确认默认值称候选。
下一步（第一件事）：从 TASKS 的 NC-001 准备真实工程/宿主装配基线，再 NC-002 模型契约及本地笔记任务；NC-015 密钥协议与 NC-020 上游共同 Schema 并行准备。CLIENT 拟为 xuan-migration/reading-notes，须 NC-001 确认，现 xuan-migration/learn_system 无 Flutter pubspec，不能误写。
私人存储新发现：有真实 Firestore/RTDB row SDK 和 generic upsert，但当前 RecordOutboxMapper 明文 JSON 不能用于私人正文；云 blob 生产适配、长期备份和跨设备密钥恢复未见完整实现。IM guard 当前未比较传入设备 ID/指纹，不能直接当笔记授权证明。
已知的坑：Notification 管线有实现，生产业务接线不足；ReceiptRejected 是停止整批并报告；旧通知查重非原子且不适用多收件人。notebook 保存覆盖旧 committed，内存降级仍返回成功，不可当永久修订库。既有 OpenAPI 有 operation headers 非规范结构，字段断言测试不代表合规。D-06 未冻结；收回只能阻止后续访问，公共媒体不能发绕过 ACL 的永久 URL。
书籍新增边界：权威架构 PUBLIC_RELEASE 当前强制 glyphbox_level/OcrPage，原生来源分支尚未获批；不能由消费稿绕过。旧 EPUB 去空格/重组换行无原件映射、旧 unit 按排序重编号；两者不能直接作稳定生产锚点。原件档位、运输方式、capability 与正式发布门禁分开。

## G3 线交接（R3 复核未通过，暂不进入 G4）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：G3 R3 交叉复核；R2 的 10 个指定变异已修复，但新增 7 个等价变异仍可假绿：
  - T-04：G1–G7 完整语义门禁与防假绿（提交 `9b6194b` / `b15c25d`）
  - T-06：完整有序证据链（提交 `3768064`）
  - T-11：差距表现状事实与二元判据（提交 `6f62189`）
  - T-13：章节状态映射与 §16 局部候选标签（提交 `e3b1570`）
  - D-07：TechniqueProfilePack 与 QueryContractPack 规约冻结（提交 `f6be483`）
  - T-07：§16.2 表格 15 目录严格映射与 query-contract 归属修正（提交 `a62f225`）
  - T-08：Tag 三接口与五字段承接、Tag G4 命名空间化、排除 M5 生产者身份（提交 `045a0ab`）
  - G3 R3 结论：D-07/T-07/T-08 为 `REWORK_REQUIRED_R3`，详见 `docs/blackbox-spec-rework/reviews/G3-REVIEW-R3.md`。
进行到一半的事（精确到文件和章节）：T-04/T-06/T-11/T-13 保持通过；D-07/T-07/T-08 需改为精确肯定句、精确接口名和唯一供给关系门禁。
下一步（第一件事）：依据 `docs/blackbox-spec-rework/reviews/G3-REVIEW-R3.md` 生成新的冷启动执行契约，再按 D-07 → T-07 → T-08 串行返工。
已知的坑：全量 `verify-T.sh` 当前仍是 0 FAIL，但等价否定句、Package 改名、额外或重复供给包仍可骗绿；旧 R2 冷启动 Prompt 已作废，不得启动 G4。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。

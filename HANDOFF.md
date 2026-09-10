# HANDOFF

## 注解社区线交接（独立于下方 G3 线）

更新时间：2026-09-10
当前分支/worktree：`codex/docs/knowledge-compilation`；`/Users/jingtaiwei/Git/Public/learn_system`
刚完成：按用户要求写入 `docs/annotation-community/SERVER_DATA_CONTRACT_DRAFT.md`，供书籍元数据生成 Agent 回执；技术基线为 REST/OpenAPI 3.1/Swagger、Python Functions/Firestore、Flutter/Drift 及现有 Social/Notification。
进行到一半的事（精确到文件和章节）：主草案 §9 U-01～U-09，以及新增 `BOOK_ASSET_DELIVERY_CONTRACT_DRAFT.md` §6 A-01～A-06 等待上游确认；资产稿已明确原件与派生阅读数据、对象存储/Firestore 分工及避免下游二次加工的交付要求。本轮不写业务实现或机器 Schema。
下一步（第一件事）：用户转交书籍两份草案，收集上游真实字段、各格式样例及共同交付 Schema 回执；私人云同步本期方向已确认，另以 `PRIVATE_NOTES_STORAGE_DRAFT.md` 收集存储 S-01～S-05 回执。
私人存储新发现：StoragePolicy.private 允许 cloud/LAN/WebRTC，不能据此声称长期备份已实现；旧 S6 文档要求 relay 同步后删除，已读 Firebase BlobGateway 为内存 fake。私人修订建议云端密文，公共发布用独立投影，密钥恢复和真实云网关必须核实。
已知的坑：D-06 未冻结；通知适配尚需核实，ACK 拒绝行为的接入文档与代码有矛盾；私人内容不是可清理缓存，公开收回不能承诺抹除已离线持有的字节。

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

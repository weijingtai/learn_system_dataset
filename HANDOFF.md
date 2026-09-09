# HANDOFF

更新时间：2026-09-09（D-03 StepRun 生命周期状态机完成）
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：D-03 已在 `openspec/learn-system-blackbox-architecture.md` §7.1、§8.2 与 §17 落地：StepRun 采用 `running / awaiting_human / suspended / succeeded / failed / superseded` 六状态和封闭迁移表；一次 StepRun 承载一个 EditionPart 的一个阶段任务及其整个人工队列；人工决定作为同一 StepRun 的不可变事件写回；`awaiting_human` 定义了绑定运行与状态版本的单次 `resume_token`、冻结输入、队列引用、事件写回和无自动失败的 deadline；Artifact Revision 另有五状态及封闭迁移表，并明确与七个内容成熟度状态正交；Ledger 故障改用可持久对账的 `suspended` / `recovery` 语义。PLAN 的 RN-3 与 RA D-03 已勾选并附依据，RA 的四张枚举全集表仍未勾选。
进行到一半的事（精确到文件和章节）：规格仍为 `REVIEW_FAILED_R1`；D-02 与其他 R1 返工均未完成，所有 T 类条目仍未完成。迁移只是决议，尚未执行；业务代码、OCR、Schema、验证脚本与验收标准均未修改。
下一步（第一件事）：严格执行 D-02（冻结 L0 机器 Schema）。
已知的坑：StepRun 的终态不可改写；重跑新建运行并用 `supersedes_step_run_id` 关联。`awaiting_human` 只表示等待人工队列，基础设施不可用或操作者主动暂停必须使用 `suspended`。RA 的“四张枚举全集表”仍缺 ReviewDecision / failure 与 SCHEMA 关系，须留给 T-03；`verify-T.sh` 仍会因未完成 T 项按预期失败。首纵切 10 页 PNG 被 Git 忽略，其他 clone 不可恢复，开工前必须登记到本地 Object Store。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。

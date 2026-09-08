# HANDOFF

更新时间：2026-09-08
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：使用 GPT-5.6 Sol 审计《穷通宝鉴》并新增 `pipeline/DATASET_ACCEPTANCE_STANDARD.md` 与 `pipeline/TODO.md`；使用 Terra Medium 代理将七政四余 `companion_system` 完整复制为根级独立项目 `pattern_knowledge_workbench/`。两轮核验确认复制瞬间的 179 files、1,827,975 bytes、逐文件 SHA-256 和 SQLite 完全一致；初次记录的 84 dirs 含八个无内容 SwiftPM 临时空目录，清理后源/目标均为 76 dirs。原样快照提交为 `4ca1a73`；工作台新增通用 README、领域词汇、扩展计划、缺口分析、迁移记录和 P0/P1/P2 待办。
进行到一半的事（精确到文件和章节）：工作台仍是七政硬编码原型，尚未实施新领域模型。`pipeline/tools/gen_outline.py` 仍漏掉带正文的二级总论；`pipeline/rag/build_index.py` 仍无法解析 glossary 完整 span ID；工作台 `lib/database/drift_database.dart` 启动覆盖本地库，编辑/AI 流程可直接设 verified，版本历史未写入。
下一步（第一件事）：先修复《穷通宝鉴》约 7.5% 源文漏编和八字 concept mentions 为 0；工作台并行首项是停止启动覆盖数据库并建立 Candidate→ReviewDecision 状态门。
已知的坑：工作台 496 rules 全无 original_text/assertion/brief/explanation/notes，verified=0、versions=0；404 条有 conditions、486 条有 chapter。`School` 混合书籍与流派，`pattern_id + school_id` 唯一键不能表达多书多主张；私有内网依赖会阻断干净环境构建。OCR corpus 仍无扫描/字框 anchor；ReleaseBundle、APP Adapter 和注解共享系统尚无实现；`Embedding-AI` 明确后置。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。

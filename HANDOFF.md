# HANDOFF

更新时间：2026-09-08
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/learn_system`
刚完成：使用一位 GPT-5.6 Sol 验收代理对《穷通宝鉴》现有拆书结果进行只读全链审计，主线程复核关键证据；新增 `pipeline/DATASET_ACCEPTANCE_STANDARD.md`，定义来源重放、全书覆盖、证据锚点、内容分层、概念检索、盘面匹配、盲审、专家签发和 ReleaseBundle 的 fail-closed 门禁。当前数据总体判定 `NOT_READY`，仅可限域内部演示。
进行到一半的事（精确到文件和章节）：尚未修复本次审计发现的问题。`pipeline/tools/gen_outline.py` 的叶节点选择漏掉带正文的二级总论；`pipeline/rag/build_index.py` 无法解析 glossary 的完整 span ID；现有 validators 会在这两项错误存在时继续 PASS。
下一步（第一件事）：先修复《穷通宝鉴》约 7.5% 源文漏编并建立 100% source→batch→segment coverage 门禁，然后修复八字 concept mentions 为 0 的索引断链；再定义 `BaziFactSet` 与 `ApplicabilityRule`，以 `丙日干 + 亥月` 做确定性召回 fixture。
已知的坑：manifest `body_chars: 31635` 与 outline `total_chars: 29251` 不一致；137 个八字 units 虽全通过现有 validator，但 1,317 assertions 全为 `machine_extracted`、138 paraphrases 全为 `machine_translated`；RAG 的 13 mentions 全属奇门；已发现漏主张、不忠实改写、命例误提、编者标记未分层及条件/例外未结构化。OCR corpus 仍无扫描/字框 anchor；ReleaseBundle、APP Adapter 和注解系统尚无实现；`Embedding-AI` 明确后置。

---
2026-07-11（Claude/Cowork）：仓库文档已按并行线拆分——Tag 文档全部迁至 `tag_system/`（原 docs/superpowers/specs/ 下两份 Tag 规格已移至 tag_system/specs/），知识编译与产品母稿迁至 `knowledge_system/`。仓库地图见根 README.md。本文件中旧路径引用以新位置为准。

---
2026-08-22（Claude/接手 OCR 线）：`ocr/` 单字切分识别质量修复完成。两条根因——
硬编码 `region<128` 二值化阈值对古籍透印/浅印字失效（139 行零段、吞 493 字）、
投影段按位置配字导致整列错位（727 行中 360 行失配）。修复后真实10页复核：失配行
360→0，净丢字 575/3287(17.5%)→0，测试 48→64 passed。任务纪要与踩坑墓地见
`tasks/codex-docs-knowledge-compilation.md`；结论与遗留 R7 见
`ocr/HANDOFF_OCR_FIXES.md` §七。本轮未触碰 Tag 线与 pipeline 线。

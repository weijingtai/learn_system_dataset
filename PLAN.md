# PLAN

更新时间：2026-09-08

## Learn System 系统集成主线

- [x] 确认并记录 Learn System 最终目标、端到端运行方式、现有工具成熟度和缺口。
- [x] 审计《穷通宝鉴》现有拆书数据，并形成 `pipeline/DATASET_ACCEPTANCE_STANDARD.md` 验收草案；当前结论为 `NOT_READY`。
- [ ] 修复《穷通宝鉴》约 7.5% 源文漏编与八字 concept mentions 为 0 的两项假绿问题。
- [ ] 定义第一条八字纵切的 KnowledgePack、FactSet、ApplicabilityRule、SourceAnchor 和 Annotation 契约。
- [ ] 打通一页扫描件到 `SourceSpan → OCR 字框 → PDF/PNG` 的无损证据链。
- [ ] 泛化 taskgen，移除八字/《穷通宝鉴》硬编码，并建立非八字 fixture。
- [ ] 修复完整 span ID 索引和 `concept → assertion → evidence` 查询链。
- [ ] 实现发布级 KnowledgeReleaseCompiler、ReleaseManifest、validator 和只读 AppKnowledgeAdapter。
- [ ] 用 `丙日干 + 亥月` FactSet 验收“十月丙火”全部相关主张召回、原文展示与扫描定位。
- [ ] 实现锚定到词条/主张/原句/扫描区域的私人及公开 Annotation 最小模型。
- [ ] 在首条纵切通过后，扩展十干十二月、十神、格局和其他术数 FactSet Profile。

## 既有知识编译与 Tag 计划

- [x] 保存术数文献知识编译与学习系统讨论草案。
- [x] 将 `learn_system` 初始化为独立 Git 工作区。
- [x] 继续补充未知领域问题与决策清单。
- [x] 汇总跨角色产品评审并保存 v1.2 产品决策母稿。
- [x] 完成 Tag/Marks 系统专题评审并保存独立评审报告。
- [x] 收敛十种 Tag 的个人样式定制与 Marketplace 接口设计规格。
- [x] 完成 Tag Style 规格跨角色复审并落实问题修订。
- [x] 同步 Tag Style 交叉评审报告与 D-015–D-020 落实门槛。
- [x] 将 D-015–D-020 回写到 Tag Style 主规格正文并同步评审报告状态。
- [x] 新增 Official Tag Starter Kit v0.1 规格并接入 Tag 执行计划。
- [x] 完成 `pipeline/` 首轮真实生命周期全面评审并保存 `PIPELINE_REVIEW_v1.md`。
- [ ] 为 `pipeline/` 增加依赖声明与环境检查，保证 validators/RAG 可复现运行。
- [ ] 增加 assertion task、glossary、RAG index 的确定性校验器。
- [ ] 按 `PIPELINE_REVIEW_v1.md` 回写四本手册的当前状态与扩批规则。
- [ ] 为《烟波钓叟歌》s13-s110 扩批建立 batches/id_range/metrics/review 模板。
- [ ] 用户确认 v1.2 推荐项、冻结项和阶段零范围。
- [ ] 确认旧 APP 类型并定稿迁移策略。
- [ ] 选择一段具有正文、注文、条件、例外和术语的奇门试点材料。
- [ ] 建立首个 `SourcePackage` 与连续工位 `TaskPackage` 示例。
- [ ] 建立奇门分工位金标集并比较不同模型表现。
- [ ] 根据试点修订 Schema、错误码和自动放行门槛。
- [ ] 将用户批准的最终设计转入 OpenSpec。
- [ ] 编写实施计划并开始校验器与编译器实现。

当前 Tag 线优先制作 `official_starter_clear` 第一版官方基础包、TechniqueProfile 和 Preview Catalog；随后用它作为 TagStyleCompiler MVP 的 golden input。不得直接启动 `TagStyleEditor`、Marketplace 或用户 Dart/Flutter 插件实施。pipeline 线仍按 `PIPELINE_REVIEW_v1.md` 继续补依赖、环境检查和确定性校验器。

### OCR 线（ocr/ 子目录，与上表并行）
- [x] 修复单字切分「不丢字/不错位」两条根因并建立契约测试（2026-08-22）
- [ ] R7 `segment_block` 横排分支墨迹掩码与取轴错误
- [ ] 清掉 `_find_gaps` 未被使用的 `min_gap` 死参
- [ ] 收紧 `tests/test_segment.py` 的宽松断言（`>= 2` 类）

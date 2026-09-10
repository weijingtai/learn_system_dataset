# G3 R1 返工交叉验收 R2

日期：2026-09-10
结论：`REWORK_REQUIRED`

冷启动执行入口：`../work-items/g3-r2/COLD_START_PROMPT.md`。该文件包含完整读集、写范围、串行顺序、10 个强制变异、停手条件与交付证据；执行 Agent 不需要本次会话上下文。

## 总结

规格正文中的 D-07、T-07、T-08 目标内容目前基本正确，提交顺序与文件范围也正确；但三项机器门禁仍存在可复现假绿，且 T-07/T-08 六件套保留与现行规格冲突的旧指令。因此 G3 不得维持 `ACCEPTED`，暂不进入 G4。

## 独立证据

- 当前 `bash docs/blackbox-spec-rework/verify-T.sh`：退出 0，显示 0 FAIL。
- `git diff --check`：退出 0。
- 主线程有效负向变异：删除 `matchFacts`、把 query-contract 改回 IndexPack、把 M5 改回字段生产者，均退出 1。
- 交叉审查补充的假绿变异如下，均在错误规格下仍退出 0。

## 返工项

### D-07

- [ ] 修复 `verify-T.sh`：分别解析 `TechniqueProfilePack`、`QueryContractPack`、`RuleIndexPack` 专属块，禁止整个 §16 的关键词跨块代偿。｜通过标准：删除 RuleIndexPack 的逐规则 Profile 版本声明后门禁非零。
- [ ] 把“事实字段与枚举”加入 TechniqueProfilePack 强制断言，并拒绝“客户端自由猜测”等否定语义。｜通过标准：删除该条或改成否定句时门禁非零。
- [ ] 在 RuleIndexPack 块内精确验证“每条规则 + 显式声明 + `profile_version` + AST schema 版本”。｜通过标准：ReleaseManifest 中泛化的 Schema/Profile 文字不能让该门禁通过。

### T-07

- [ ] 精确校验 `query-contract` 右侧只能是 `QueryContractPack（查询契约与接口定义）`，不得附加任何其他子包。｜通过标准：追加 EvidenceMapPack 后门禁非零。
- [ ] 精确校验 `optional-vector-index` 只能是“本期不产出（依据 §21 非目标）”。｜通过标准：追加 SearchIndexPack 后门禁非零。
- [ ] 取代声明必须是包含 PublicationPackage、KnowledgeDataPack、正式取代、KnowledgePack 的肯定句。｜通过标准：改成“不得取代”时门禁非零。
- [ ] 同步 `work-items/t07/README.md` 与 `PROMPT.md`：删除禁止修改门禁、错误 IndexPack 映射和旧 8→7 FAIL 口径。

### T-08

- [ ] 精确校验五字段的生产 Module 与归属 Package，不只检查字段唯一和 M5 缺席。｜通过标准：把 concept_id 改成 `M2 / SourceAssetPack` 时门禁非零。
- [ ] 精确校验三接口的供给 Package。｜通过标准：任一接口改成错误子包时门禁非零。
- [ ] 同步 `work-items/t08/README.md`、`BDD.md`、`PROMPT.md`：删除 M4/M5 共同生产、旧 7→5 FAIL 与旧提交指令。

## 重新准出

三项分别完成 Red→Green→Mutation，更新 TDD/ACT/ACCEPTANCE，并经主 Agent 复跑全部变异后，方可恢复 G3 `ACCEPTED` 并进入 G4。

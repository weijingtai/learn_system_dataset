# G3 R3 变异用例清单（89 例）

所有 Anchor 的完整原文见 `CANONICAL.md`。每例都要求原 Anchor 在权威规格中精确命中 1 次；`删除`表示删除完整原行；`替换 X→Y` 只在该 Anchor 行内执行。指定 FAIL ID 必须出现，且门禁必须非零。

Anchor 方括号标签仅是元数据，不属于 expected；expected 固定为 `] ` 之后的完整文本。

变异脚本只允许以下机械原语：

- `delete_line(anchor)`：删除 Anchor 全行。
- `duplicate_line(anchor)`：在 Anchor 后原样追加同一行一次。
- `replace_line(anchor, exact_line)`：把 Anchor 全行替换为给定完整行。
- `replace_text(anchor, before, after)`：要求 Anchor 全文中 `before` 恰好出现一次，再替换为 `after`。
- `replace_map_value(anchor, value)`：仅用于三列 §16.2 行；保留首尾 `|` 和 key，将第三个 pipe cell 完整替换为 `value`。
- `replace_field_cell(anchor, column, value)`：仅用于六个 pipe cell 的 §16.3.2 数据行；`column=module` 替换第四 cell，`column=package` 替换第五 cell。
- `append_line(anchor, exact_line)`：在 Anchor 后追加给定完整行。
- `delete_block(start_anchor, end_heading)`：删除 start Anchor 起至 end heading 前的全部行，end heading 保留。

表格中的“删除”或“删除完整……行”等同 `delete_line`；“完整原行重复一次”等同 `duplicate_line`；“整行替换为”使用 `replace_line`；普通 `X→Y` 使用 `replace_text`。`RHS→` 等同 `replace_map_value`；“RHS 后追加 X”等同以“当前完整 RHS + X”为 value 调用 `replace_map_value`；`Module→`、`Package→` 分别等同 `replace_field_cell(..., module, ...)` 与 `replace_field_cell(..., package, ...)`。组合变异用 `+` 串联，每个子操作都必须独立满足命中次数；不得由执行者自行解释自然语言或扩大替换范围。

稳定 FAIL ID：`G3-D07-TP`、`G3-D07-QC`、`G3-D07-RI`、`G3-D07-COMPAT`、`G3-T07-MAP`、`G3-T07-REPLACEMENT`、`G3-T08-SEC1`、`G3-T08-BLOCK`、`G3-T08-PROSE`、`G3-T08-TABLE`、`G3-T08-DSL`、`G3-T08-G4`。

## D-07（25）

| Case | Anchor | 变异 | 命中 | FAIL ID |
|---|---|---|---:|---|
| d07-01 | D07-TP-FIELDS | 删除 | 1 | G3-D07-TP |
| d07-02 | D07-TP-FIELDS | 整行替换为 `- **事实字段与枚举**：包中不列任何事实字段与枚举；字段由客户端自由猜测；` | 1 | G3-D07-TP |
| d07-03 | D07-RI-VERSION | 删除 | 1 | G3-D07-RI |
| d07-04 | D07-TP-START | `TechniqueProfilePack`→`WrongProfilePack` | 1 | G3-D07-TP |
| d07-05 | D07-QC-START | `QueryContractPack`→`WrongQueryPack` | 1 | G3-D07-QC |
| d07-06 | D07-RI-START | `RuleIndexPack`→`WrongRulePack` | 1 | G3-D07-RI |
| d07-07 | D07-QC-COMPAT | 删除 | 1 | G3-D07-COMPAT |
| d07-08 | D07-QC-COMPAT | `必须保持`→`不得保持` | 1 | G3-D07-COMPAT |
| d07-09 | D07-QC-COMPAT | `必须保持`→`不应保持` | 1 | G3-D07-COMPAT |
| d07-10 | D07-QC-COMPAT | `必须保持`→`并未保持` | 1 | G3-D07-COMPAT |
| d07-11 | D07-TP-PROFILE | 删除 | 1 | G3-D07-TP |
| d07-12 | D07-TP-OPERATORS | 删除 | 1 | G3-D07-TP |
| d07-13 | D07-TP-AST | 删除 | 1 | G3-D07-TP |
| d07-14 | D07-QC-ENTRY | 删除 | 1 | G3-D07-QC |
| d07-15 | D07-QC-SPAN | 删除 | 1 | G3-D07-QC |
| d07-16 | D07-QC-SEARCH | 删除 | 1 | G3-D07-QC |
| d07-17 | D07-QC-MATCH | 删除 | 1 | G3-D07-QC |
| d07-18 | D07-RI-DECLARATIVE | 删除 | 1 | G3-D07-RI |
| d07-19 | D07-TP-FIELDS | 完整原行重复一次 | 1 | G3-D07-TP |
| d07-20 | D07-QC-ENTRY | 完整原行重复一次 | 1 | G3-D07-QC |
| d07-21 | D07-RI-DECLARATIVE | 完整原行重复一次 | 1 | G3-D07-RI |
| d07-22 | D07-QC-ENTRY | `getEntry`→`WronggetEntry` | 1 | G3-D07-QC |
| d07-23 | D07-QC-SPAN | `getSourceSpan`→`WronggetSourceSpan` | 1 | G3-D07-QC |
| d07-24 | D07-QC-SEARCH | `searchKnowledge`→`WrongsearchKnowledge` | 1 | G3-D07-QC |
| d07-25 | D07-QC-MATCH | `matchFacts`→`WrongmatchFacts` | 1 | G3-D07-QC |

## T-07（25）

| Case | Anchor | 变异 | 命中 | FAIL ID |
|---|---|---|---:|---|
| t07-01 | T07-M01 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-02 | T07-M02 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-03 | T07-M03 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-04 | T07-M04 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-05 | T07-M05 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-06 | T07-M06 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-07 | T07-M07 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-08 | T07-M08 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-09 | T07-M09 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-10 | T07-M10 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-11 | T07-M11 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-12 | T07-M12 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-13 | T07-M13 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-14 | T07-M14 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-15 | T07-M15 | RHS→`WrongPack` | 1 | G3-T07-MAP |
| t07-16 | T07-M15 | RHS 后追加 `EvidenceMapPack` | 1 | G3-T07-MAP |
| t07-17 | T07-M14 | RHS 后追加 `SearchIndexPack` | 1 | G3-T07-MAP |
| t07-18 | T07-REPLACEMENT | 删除 | 1 | G3-T07-REPLACEMENT |
| t07-19 | T07-REPLACEMENT | 完整原行重复一次 | 1 | G3-T07-REPLACEMENT |
| t07-20 | T07-REPLACEMENT | `正式取代`→`不得取代` | 1 | G3-T07-REPLACEMENT |
| t07-21 | T07-REPLACEMENT | `正式取代`→`并未正式取代` | 1 | G3-T07-REPLACEMENT |
| t07-22 | T07-REPLACEMENT | `正式取代`→`尚未正式取代` | 1 | G3-T07-REPLACEMENT |
| t07-23 | T07-REPLACEMENT | `正式取代`→`不应正式取代` | 1 | G3-T07-REPLACEMENT |
| t07-24 | T07-M02 | 删除完整 schema 行 | 1 | G3-T07-MAP |
| t07-25 | T07-M15 | 完整 query-contract 行重复一次 | 1 | G3-T07-MAP |

## T-08（39）

| Case | Anchor | 变异 | 命中 | FAIL ID |
|---|---|---|---:|---|
| t08-01 | T08-R04 | `replace_field_cell(T08-R04, module, M2)` + `replace_field_cell(T08-R04, package, SourceAssetPack)` | 各1 | G3-T08-TABLE |
| t08-02 | T08-R01 | Module `M4`→`M2` | 1 | G3-T08-TABLE |
| t08-03 | T08-R02 | Module `M4`→`M2` | 1 | G3-T08-TABLE |
| t08-04 | T08-R03 | Module `M4 / M6`→`M2` | 1 | G3-T08-TABLE |
| t08-05 | T08-R04 | Module `M4`→`M2` | 1 | G3-T08-TABLE |
| t08-06 | T08-R05 | Module `M4 / M7 / M6`→`M2` | 1 | G3-T08-TABLE |
| t08-07 | T08-R01 | Package→`SourceAssetPack` | 1 | G3-T08-TABLE |
| t08-08 | T08-R02 | Package→`SourceAssetPack` | 1 | G3-T08-TABLE |
| t08-09 | T08-R03 | Package→`SourceAssetPack` | 1 | G3-T08-TABLE |
| t08-10 | T08-R04 | Package→`SourceAssetPack` | 1 | G3-T08-TABLE |
| t08-11 | T08-R05 | Package→`SourceAssetPack` | 1 | G3-T08-TABLE |
| t08-12 | T08-S1-01 + T08-B1-SUPPLY | `replace_text(T08-S1-01, KnowledgeDataPack, SourceAssetPack)` + `replace_text(T08-B1-SUPPLY, KnowledgeDataPack, SourceAssetPack)` | 各1 | G3-T08-SEC1 + G3-T08-BLOCK |
| t08-13 | T08-S1-02 + T08-B2-SUPPLY | `replace_text(T08-S1-02, 由 KnowledgeDataPack 与 RuleIndexPack 供给, 由 SourceAssetPack 供给)` + `replace_text(T08-B2-SUPPLY, 由 KnowledgeDataPack 与 RuleIndexPack 供给, 由 SourceAssetPack 供给)`（参数保留原文反引号） | 各1 | G3-T08-SEC1 + G3-T08-BLOCK |
| t08-14 | T08-S1-03 + T08-B3-SUPPLY | `replace_text(T08-S1-03, EvidenceMapPack, SearchIndexPack)` + `replace_text(T08-B3-SUPPLY, EvidenceMapPack, SearchIndexPack)` | 各1 | G3-T08-SEC1 + G3-T08-BLOCK |
| t08-15 | T08-S1-01 | `由 KnowledgeDataPack 供给`→`由 KnowledgeDataPack 供给，并由 SourceAssetPack 供给`（保留反引号） | 1 | G3-T08-SEC1 |
| t08-16 | T08-S1-02 | `由 KnowledgeDataPack 与 RuleIndexPack 供给`→原文后追加`，并由 SourceAssetPack 供给`（保留反引号） | 1 | G3-T08-SEC1 |
| t08-17 | T08-S1-03 | `由 EvidenceMapPack 供给`→`由 EvidenceMapPack 供给，并由 SearchIndexPack 供给`（保留反引号） | 1 | G3-T08-SEC1 |
| t08-18 | T08-B1-SUPPLY | 原行后追加一行 `   - **供给子包**：由 `SourceAssetPack` 供给；` | 1 | G3-T08-BLOCK |
| t08-19 | T08-B2-SUPPLY | 原行后追加一行 `   - **供给子包**：由 `SourceAssetPack` 供给；` | 1 | G3-T08-BLOCK |
| t08-20 | T08-B3-SUPPLY | 原行后追加一行 `   - **供给子包**：由 `SearchIndexPack` 供给；` | 1 | G3-T08-BLOCK |
| t08-21 | T08-B1-HEAD | `最小盘面概念字典`→`Wrong概念字典` | 1 | G3-T08-BLOCK |
| t08-22 | T08-B2-HEAD | `MarkContentBinding`→`WrongMarkContentBinding` | 1 | G3-T08-BLOCK |
| t08-23 | T08-B3-HEAD | `EvidenceBundle`→`WrongEvidenceBundle` | 1 | G3-T08-BLOCK |
| t08-24 | T08-P01 | `由 M4 生产`→`由 M2 生产` | 1 | G3-T08-PROSE |
| t08-25 | T08-P04 | `KnowledgeDataPack`→`SourceAssetPack` | 1 | G3-T08-PROSE |
| t08-26 | T08-R01 | Module `M4`→`M4 / M5` | 1 | G3-T08-TABLE |
| t08-27 | T08-R02 | Module `M4`→`M4 / M5` | 1 | G3-T08-TABLE |
| t08-28 | T08-S1-03 + T08-B3-HEAD + T08-B3-SUPPLY | `delete_line(T08-S1-03)` + `delete_block(T08-B3-HEAD, #### 16.3.2)`；删除前另断言 T08-B3-SUPPLY 命中 1 次 | 各1 | G3-T08-SEC1 |
| t08-29 | T08-R04 | 删除完整 concept_id 表格行 | 1 | G3-T08-TABLE |
| t08-30 | T08-S1-01 | 删除“不含规则 DSL” | 1 | G3-T08-DSL |
| t08-31 | T08-S1-01 | 删除 `TAG_SYSTEM_DESIGN.md §12.2` | 1 | G3-T08-G4 |
| t08-32 | T08-P02 | `由 M4 结构化生产`→`由 M2 结构化生产` | 1 | G3-T08-PROSE |
| t08-33 | T08-P03 | `由 M4/M6 审核产出`→`由 M2 审核产出` | 1 | G3-T08-PROSE |
| t08-34 | T08-P05 | `M4/M7/M6`→`M2` | 1 | G3-T08-PROSE |
| t08-35 | T08-S1-01 | `最小盘面概念字典`→`Wrong概念字典` | 1 | G3-T08-SEC1 |
| t08-36 | T08-S1-02 | `MarkContentBinding`→`WrongMarkContentBinding` | 1 | G3-T08-SEC1 |
| t08-37 | T08-S1-03 | `EvidenceBundle`→`WrongEvidenceBundle` | 1 | G3-T08-SEC1 |
| t08-38 | T08-B1-LIMIT | 删除“不含规则 DSL” | 1 | G3-T08-DSL |
| t08-39 | T08-B1-LIMIT | 删除 `TAG_SYSTEM_DESIGN.md §12.2` | 1 | G3-T08-G4 |

`t08-28` 删除块时范围从 T08-B3-HEAD 起，到 `#### 16.3.2` 前止；命中前必须分别确认 HEAD 与 SUPPLY 各 1 次。

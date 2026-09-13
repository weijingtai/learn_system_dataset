# IMPL-07 G0 复审 R2（独立审查者 W4-R5）

- 复审对象：返工提交 `6e7f5f1`（docs(impl-07): address G0 four-check R1）后的 G0 文本，对照 R1（`f63ca89`）F1/S1/S2；impl-07 文件在 HEAD（`af17496`）与该提交无差异（后续两提交属 impl-06/act-13）。
- 核对基准：`pipeline/knowledge_extraction/assemble.py` 已验收代码与 `openspec/acceptance/run_all.sh` 实跑。

## R1 发现闭合核对

- F1｜闭合｜act/g0-01.yaml:42-53（validate_candidate_set）｜校验按 impl-05 真实键重写并注明「键逐字取已验收 assemble.py:637-651」——实测该行区间正是 `candidate_set` 顶层装配：15 个顶层键（含 `source_channels`）与合同必填清单逐字一致（assemble.py:637-651）；assertion 无 `subject`/`school_view_ids`、用 `school_ids`（assemble.py:427-445），pattern 恒发 `pat_` 号、无 `candidate_key`（assemble.py:484-500）——与合同要点逐字吻合。断言↔Pattern 关联改为「以 `patterns[].assertion_ids` 为唯一来源」（`assertion_to_patterns` 映射，供 g0-02 解析）；`subject_entity_id` 解析规则确定（恰 1 → 该 pat_，多 → 字典序最小，零 → null）；knowledge 断言的 `school_view_ids` 由 `school_views[].subject_entity_id`/`claim_refs` 反解。合成宿主同步：g0-04 contract 增「合成 candidate_set 段必须为 impl-05 已验收真实形状」+ 新具名用例 `test_synthetic_candidate_set_matches_impl05_shape`（断言无 subject/school_view_ids/candidate_key）；BDD 新增 G0.14。R03e 降级为防御分支并注明「当前上游不产出」（g0-02 contract、BDD G0.2、README §0.7 接口需求 5）——与第 64/65 条一致（impl-05 恒发号，assemble.py:484）。
- S1｜闭合｜act/g0-01.yaml:17-18｜canonical_json 增注「本包规范字节带尾部换行……不得用本函数与 M4 candidate_set 字节互比，也不得直接复用其哈希」。
- S2｜闭合｜ACT.yaml:48｜gates 补 `bash openspec/acceptance/m3-coverage.sh | tail -1  # == 开工基线`。

## 无新阻断核查

- 阈值：awk 实测各 ACT 具名用例 30/21/13/13/10，累计 **30/51/64/77/87** == TDD §G0.1 == ACCEPTANCE（已同步更新，且新增「F1/S1/S2 返工项」核对行）；用例增删与返工内容一一对应（g0-01 −2+4、g0-02 −1+4、g0-04 +1）。
- m7-assembler：10 PASS + 6 BLOCKED、`SUMMARY pass=10 fail=0 blocked=6`、exit 2 口径四处不变（ACT.yaml/TDD/g0-05/BDD G0.11）；run_all 基线 `pass=2 fail=1 blocked=8` 不变。
- 第 63–66 条仍落位：63（base 非 None/重复创世拒绝）、64（R02 保留 M4 号；R03e 仅防御分支从配置 `id_range` 取号、跳过占用、清单入 Snapshot）、65（§0.7 接口需求 1–5，新增第 5 条与 64 条自洽）、66（合成宿主 + synthetic_fixture + upstream_m6_real 恒 BLOCKED）均未被返工削弱；`basis_sha256` 已改为不引用不存在字段（`{name: nfc_key(name), recognition_rule_status}`）。
- 独立性与写范围不变：gate/acceptance 禁 import genesis、写范围仍仅 `pipeline/assembly/**` + m7-assembler.sh。

## 残留（建议级）

- S3｜建议｜act/g0-01.yaml:46 与 act/g0-02.yaml:15、README §0.7 第 5 条｜防御分支错误码三处不一致：g0-01 句式「为 null → SCH_002」未写「无 candidate_key」限定（宽严两读——按字面将连 null+candidate_key 也拒，使 R03e 与 `test_genesis_defensive_allocates_when_pattern_id_null` 不可达；其自身用例名已按「null 且无防御键 → 拒」消歧）；g0-02 前置拒绝与 README §0.7 写 SCH_001、g0-01 写 SCH_002。建议统一为「model 层：null 且无 candidate_key → SCH_002；有 candidate_key → 放行至 R03e」并统一 README 码值。

## 判定

**READY**（F1/S1/S2 全部闭合；阈值与具名用例累计实测一致；m7-assembler 与基线期望不变；第 63–66 条落位未削弱；残留仅 1 条建议级措辞/码值统一，不阻断派发。）

（审查者：W4-R5；以 HEAD `af17496` 只读核查；`git diff --check` 无输出。）

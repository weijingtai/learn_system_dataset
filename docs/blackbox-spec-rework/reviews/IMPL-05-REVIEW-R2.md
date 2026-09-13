# IMPL-05 四查复审 R2（独立审查者 W4-R5）

- 复审对象：返工提交 `d982dd6`（docs(impl-05): address four-check R1 and rulings 53-55）后的 `work-items/impl-05-knowledge/`，对照 R1（`1a7919e`）的 F1–F7 与 G7-RULINGS §9.7 第 53 条、§9.8 第 54/55 条。
- 方法：逐条以 diff 与 HEAD 文本核对闭合证据；重算用例阈值；跨包一致性另见 IMPL-00-W4G-REVIEW-R2。

## R1 发现闭合核对

- F1｜闭合｜act/00.yaml:33｜`canonical_json` 已补 `separators=(",", ":"), allow_nan=False` 并注明「与 README §5.3 固化默认逐字一致」，与 README.md:115 逐字相同；全包唯一口径成立，K4 金标哈希可比性恢复。
- F2｜闭合｜ACT.yaml:13,57、TDD.md:13,65、PROMPT-G1.md:39,48,68、ACCEPTANCE.md:9,22、README.md:393｜全部改为「末行 `fail=0` 且 exit 0，且 M4 五类型各自 PASS 行存在（第 54 条，不写死 pass 总数）」；`grep -rn 'pass=18|pass=24'` 在本包为 0。
- F3｜闭合｜README.md:148｜读方法清单改为 `list_step_run_events（StepRun 事件流，F3 订正）`，与 `service.py:125` 实际公开面一致。
- F4｜闭合｜README.md:148｜`human_events`、`processing_runs` 两类 SELECT 经第 55 条并入 impl-00 README §5.2 唯一缺口清单（impl-00 侧 a42259f 已实际写入 §5.2 第 2 条），包内不再出现「唯一清单」自相矛盾。
- F5｜闭合｜act/03.yaml:31｜contract 新增「输出形状不符（…任一非恰 1 个；fixture-only m3 即落此支）→ ExtractionRefused(code="REF_001", message 含「M3 未通过」）」，测试期望可由 contract 推出。
- F6｜闭合｜act/03.yaml:80｜新增具名用例 `test_submit_refused_after_m4_sealed`（先 run_m4 封存再 submit → begin 前拒绝、Ledger 行数不变），BDD 4.4「M4 已封存」分支有落点。
- F7｜闭合｜act/05.yaml:16,26｜W4 补 `edition_part_id=ep`，且新增 `ep` 的来源定义（processing_runs 表只读 SELECT，与 R3/R4 同源），符合 `service.py:1364-1377` 签名。
- 第 53 条｜闭合｜act/05.yaml:17(R2)、:24(W1)、:49｜键集放宽为「⊇ {schema_version,dispute_id,choice,rationale} 且 ⊆ 六键（另加 synthetic_fixture、actor_ref）」，`synthetic_fixture` 存在时必须 bool；W1 的 human_event 原样保留该标记并取裁决文件 actor_ref；显式写明「合成事件不得计为真实 expert_verified，也不得作为 M5/M8/任何发布级别判定的依据」；act/07 dispute_ruling 同步注明只读金标 choice；新增具名用例 `test_synthetic_ruling_event_retains_marker_not_expert_verified`（第 53 条「补具名用例断言」落实）。
- 第 55 条｜闭合｜README.md:456｜附录 A 裁决件改为六键 `{schema_version, dispute_id, choice, rationale, synthetic_fixture: true, actor_ref: fixture:mini_ed01}` 并注明不计入真实 expert_verified；act/00 tests_first 同步 appendix_a 落地说明；act/07 字节等同测试前提恢复成立。

## 阈值与覆盖性重算

- 具名用例累计（逐条点数）：act/00=9+7=16；act/01=25→41；act/02=24→65；act/03=4+12=16→**81**；act/04=14→**95**；act/05=13→**108**；act/06=12→**120**；act/07=11→**131**；act/08=5→**136**。与 TDD.md §1、各 act verify 注释、README §1（≥131）、ACCEPTANCE 覆盖性行完全一致；两处增量恰为本返工新增的具名用例，无多计少计。
- BDD 场景落点核对：新增用例分别对应 BDD 4.4（M4 已封存）与第 53 条标记保留断言；其余场景与 R1 相同，无新增缺口。

## 跨包一致性（与 impl-00 a42259f 联合核对）

- 附录 A 裁决件（六键）与 impl-00 act/05 规定的 fixture `m4/ruling_m4_d001.yaml` 键集、键序、取值逐字一致（`synthetic_fixture: true`、`actor_ref: fixture:mini_ed01`），双侧均声明与对方同步。
- check_interfaces 前提：本包 8 处引用全部为 `fail=0` 形式且不写死 pass 总数（第 54 条），与 impl-00 侧一致。
- `canonical_json` 与 impl-00 act/05 item 2 对 `m4/candidate_set.yaml` 的钉死口径为**同一函数规则**（逐字相同的 json.dumps 参数），candidate_set 字节在金标与实现间可比。
- 其余（grep=0 可达、SHA 基准、占位信封）见 IMPL-00-W4G-REVIEW-R2，均闭合。

## 残留（建议级）

- S1｜建议｜act/00.yaml:11、README.md:453-456｜字节等同测试（act/07 `test_tests_data_equals_fixture_gold`）依赖 appendix_a 与 fixture `m4/` 的 YAML **序列化形态**（flow/block、键序）完全一致：impl-05 侧为「逐字落附录 A」，impl-00 act/05 侧为「四键基础上追加两键」，内容一致但未明示 fixture 侧按附录 A 的同一 YAML 形态落盘。建议 impl-00 act/05 补一句「四金标 YAML 形态与键序逐字同附录 A/act/00 展开规则」（本包侧无需改动）。

## 判定

**READY**（F1–F7 与第 53/55 条全部闭合；阈值与具名用例累计逐一相符；跨包一致性成立；残留仅 1 条建议，不阻断派发。）

（审查者：W4-R5；以 HEAD `a42259f` 只读核查；`git diff --check` 无输出。）

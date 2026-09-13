# IMPL-00 W4G 前置 ACT 复审 R2（独立审查者 W4-R5）

- 复审对象：返工提交 `a42259f`（docs(impl-00): address W4G review R1）后的 `work-items/impl-00-interfaces/` act/12.yaml 与 act/05.yaml，对照 R1（`b401c61`）的 W1–W7 与 G7-RULINGS §9.7 第 52/53 条、§9.8 第 54/55 条。
- 方法：逐条以 diff 与 HEAD 文本核对闭合证据；对 INTERFACES.md 现状重算旧名残留覆盖面；跨包一致性另见 IMPL-05-REVIEW-R2。

## R1 发现闭合核对

- W1｜闭合｜act/05.yaml:20（item 4）、:27（V9）、:32（verify）｜SHA256SUMS 基准改为**相对 fixture 目录**（`<hex>  m4/<file>` / `<hex>  expected/m4.stage_package.yaml`），生成与复算均固定在 fixture CWD；V9 明确「在 `$FIX` 内复算」；verify 第 6 条 `(cd mini_ed01 && shasum -c m4/SHA256SUMS)` 与之同基准——三个消费方一致，不再有 File not found 分叉。
- W2｜闭合｜act/05.yaml:15-17（item 1）｜措辞改为「三件提交件逐字取附录 A；裁决件按 §52/§55 在四键上追加 `synthetic_fixture: true`、`actor_ref: fixture:mini_ed01` 两键」，并明示 impl-05 附录 A、act/00 appendix_a、act/07 字节等同期望已随 `d982dd6` 同步为同一六键内容、record_category_ruling 键集已按第 53 条放宽——交接闭环成立（本包侧核对见 IMPL-05-REVIEW-R2：六键逐字一致）。
- W3｜闭合｜act/12.yaml:46（新增 K 条）｜contract 增补 §3.15（`INTERFACES.md:321`）的 `model_run` 残留清理，并写明目标「全文件 `grep -cE 'candidate_batch|model_run|candidate_diff_report'` = 0 可达」。重算覆盖面：旧名现存 5 处（134、136、258、321、339）分别落 A（§4 行）、C（§2.4 卡片 129-143）、E（§3.2）、K（§3.15）——全覆盖，verify「旧名清零 = 0」可达。
- W4｜闭合｜act/05.yaml:19（item 2 钉死存储格式）、:29（V11）、:34（verify 循环）｜candidate_set.yaml 明示为 canonical JSON 字节且公式与 impl-05 act/00 修复后 `canonical_json` **逐字同一**（sort_keys/ensure_ascii=False/separators=(",", ":")/allow_nan=False）；V11 改为只探测含 `event_kind:` 的人工事件文件（命名约定 `m4/ruling_*.yaml`），verify 循环同步改为 `ruling_*.yaml`，`candidate_set.yaml` 不再参与——误击与口径漂移双风险消除。
- W5｜闭合｜act/05.yaml:21（item 3）｜expected/m4 信封补全 stage_package.schema.json 全部 required 键：`pkg_m4_…`/`rev_…`/`prun_…`/`srun_…` 固定占位 hex（合规 §8.1 正则）、最小占位 ArtifactRef、空 logs/failures；并注明「impl-05 act/07 golden_match 只比对 counts / content_sha256 / payload 四标量 / assertions (assertion_id, proposition)，不比对任何 ID/lineage/logs」——与 impl-05 act/07 golden_match 实际比对范围逐项一致，V5 schema 校验可达。
- W6｜闭合｜act/05.yaml:24（item 6）｜改为「m1–m3 判定结论不变——仍全 PASS、末行仍 `FIXTURE OK`；V5/V6 的 emit 文本按本条同步」，消除与自身 V5/V6 编辑的措辞矛盾。
- W7｜闭合｜act/12.yaml:24（C 条）｜§2.4 卡片冻结输入补 `corpus_package` 并注明「与 impl-05 act/04 frozen 7 项一致」——对账基准与实现契约一致。
- 第 54 条｜闭合｜act/12.yaml:45,62、ACCEPTANCE.md:39、ACT.yaml:76、README.md:25,128｜所有 Green 期望/门禁/派发核对均改为「末行 `fail=0` 且 exit 0，IF19–IF23 五个 PASS 行存在；不写死 pass 总数」；`test_summary_line_format` 同步改为不断言 pass 总数。残留的 `pass=<n>` 仅存在于已验收历史 ACT（impl-00/10）的输出格式描述与脚本 docstring，属格式占位符而非写死期望，第 54 条明确历史不回改。
- 第 55 条｜闭合｜README.md:119（§5.2 第 2 条）｜唯一缺口清单已并入 impl-05 的 `processing_runs`（act/03 取 technique_id）与 `human_events`（act/05 查已登记裁决）两类只读 SELECT，并注明经 §9.8 第 55 条。

## 阈值、可达性与覆盖性重算

- act/12：用例 13 = 现存 8（名字与 `tests/test_check_interfaces.py:58-96` 逐字一致）+ 新增 5，`≥ 13` 不变且可达；IF01–IF18 编号语义冻结 + IF19–IF24 显式编号，`fail=0` 且 IF19–IF23 PASS 行存在可计算。
- act/05：verify 11 项可达（fixture verify.sh 现基线实测 8 PASS + `FIXTURE OK`；页图在本机存在）；确定性 twice、SHA 复算（新基准）、`ruling_*.yaml` 合成标记扫描、热点未动、spans sha `ec6d77b9…44ef` 不变、`git diff --check` 全部为可执行判据；两 ACT 各 60 分钟 ≤110。
- 四金标数值与 impl-05 附录 A 及 spans.yaml 实测仍逐项吻合（counts、as_ 编号、offset [8,12]/[27,32]/[20,27]/[68,70]/[119,122]、rejected、disputes key/choice）。

## 跨包一致性

- 与 impl-05 `d982dd6` 的三处联动（附录 A 六键、act/00 appendix_a、act/07 字节等同）已在 item 1 声明并经 impl-05 侧核实落地。
- `check_interfaces` 前提两包同为 `fail=0` 形式、无写死 pass 数。
- candidate_set.yaml 的 canonical 口径与 impl-05 `canonical_json` 同一规则（逐字比对通过）。

## 残留（建议级）

- S1｜建议｜act/05.yaml:15-17｜字节等同测试的执行面还依赖 YAML 序列化形态一致：impl-05 侧为「逐字落附录 A」，本侧为「四键 + 追加两键」的描述式。建议补一句「四金标的 YAML 形态与键序逐字同附录 A（裁决件即附录 A 修订后六键片段的逐字复制）」，彻底消除 flow/block 风格歧义。

## 判定

**READY**（W1–W7 与第 52/54/55 条全部闭合；旧名清零与 SHA 基准经重算可达；跨包一致性成立；残留仅 1 条建议，不阻断执行。）

（审查者：W4-R5；以 HEAD `a42259f` 只读核查；`git diff --check` 无输出。）

# IMPL-00 W4G 前置 ACT 四查审查 R1（独立审查者 W4-R5）

- 审查对象：当前 HEAD（`8fb9189`）的 `docs/blackbox-spec-rework/work-items/impl-00-interfaces/act/12.yaml`（M4 闭集登记与 INTERFACES 对账）与 `act/05.yaml`（mini_ed01 m4 金标独占 ACT，含 `3f32700` 的 §52 合成标记修订）。
- 依据：G7-RULINGS §9.6 第 47–50 条、§9.7 第 51–52 条、第 53 条（跨包）；impl-05 定稿（`8cedae2`）README 附录 A 与 act/00/04/05/07；`INTERFACES.md` 现状、`check_interfaces.py` 与现存 `tests/test_check_interfaces.py`；`openspec/schemas/stage_package.schema.json`；fixture `mini_ed01/`（verify.sh 实跑基线 8 PASS + `FIXTURE OK`，页图在本机存在）。
- 只审不改；本报告为唯一写入文件。

## 一、忠实性

- act/12 依第 47/49/51 条：§4 M4 行整行替换为五行（名称与 impl-05 §6.1.1 提名逐字一致）、删旧名、§2.4/§3.1/§3.2/§3.10/§6 I-11 重写为薄结构与页块绝对坐标、M4 类型入必查清单、K2 前执行——逐项对应。
- 第 51 条前提实测成立：`char_start/char_end` 在 `pipeline/dataset_compiler/`、`pipeline/validation/`、`pipeline/corpus_compiler/` 与 impl-04 文档均为 0 处；`INTERFACES.md` 内恰 3 处（236/301/404）全在改写范围，verify「char_start=0」可达。
- act/05 依第 48/52 条：P4 独占（本波唯一 fixture 写者）、金标不由 impl-05 实现方生成（不 import `pipeline.knowledge_extraction`、不运行其代码，verify grep + on_fail）、`synthetic_fixture: true` + `actor_ref: fixture:mini_ed01` + m4/README(f) 声明「不计入真实 expert_verified、不得进入发布级别判定」+ V11 + on_fail 缺失即停——第 52 条三要素（标记、作者、声明）齐备。
- 忠实性发现：W2、W3、W7。

## 二、覆盖性

- act/12：用例 13 = 现有 8（`test_if01_passes_on_repo_copy` 等，名字与现存 `tests/test_check_interfaces.py:58-96` 逐字一致）+ 新增 5；Red（改 INTERFACES 前 IF19–IF23 FAIL）先于 Green；IF01–IF18 编号语义冻结，`REQUIRED_TYPES`/`M4_TYPES` 分列防编号漂移，`pass=24` 可计算可达（18+6）。
- act/05：Red（m4 文件齐备前 verify FAIL）→ Green；verify 覆盖确定性 twice、`FIXTURE OK`、`PASS ≥ 11`（现基线实测 8，V9/V10/V11 增 3；页图存在故可达）、SHA 复算、合成标记扫描、热点未动、spans sha 冻结、`git diff --check`。
- 两 ACT 均 60 分钟 ≤110。

## 三、可执行性

- act/12 写范围仅 `INTERFACES.md`、`check_interfaces.py`、`tests/__init__.py`、`tests/test_check_interfaces.py`——与「只含 INTERFACES/check_interfaces/tests」要求一致；commit.add 同；on_fail 禁改 schemas/fixture/ledger。
- act/05 写范围独占：仅 `m4/*`（四输入金标 + candidate_set.yaml + build_expected_m4.py + SHA256SUMS + README）+ `expected/m4.stage_package.yaml` + `verify.sh`；不改 `tools/build_fixture.py`、不碰 `expected/m1..m3`/`manifest.yaml`/`spans.yaml`/`pages`/`source`/`anomalies`；spans sha 冻结判据实测值 `ec6d77b9…44ef` 正确。
- 金标数值与 impl-05 附录 A 及 spans.yaml 实测逐项吻合：counts {2,0,0,0,2,1,1,1}；`as_qizheng_000001`「宋錢如璧撰」（s02 [8,12]、s04 [27,32]）、`000002`「三辰通載三十卷」（s04 [20,27]）；身宮 s12 [68,70]、官祿宮 s19 [119,122]；rejected 1（assertion/b/2/TXT_001）；disputes m4_d001 key 与 choice a。V10 的 quote 复算（含 B 路 item2 `錢如璧撰述` 除外条款）与 Span 文本一致。
- 依赖顺序 act/12 → act/05 与第 48 条「同批起草、四查后执行」一致；`depends_on: [impl-00/12]` 合理（登记先于金标落地）。
- 可执行性发现：W1、W4、W5。

## 四、独立性

- 两 ACT 写范围互斥（INTERFACES 侧 vs fixture 侧）；act/05 是本波唯一 fixture 写者（P4）；不与 impl-08（orchestrator/contract_registry 实现，进行中）重叠。
- 防同错同过：金标由 act/05 独立手写/独立生成器产出，禁止 import 或运行 impl-05 代码；V10 以 spans.yaml 独立复算 quote；V9 独立复算 sha；impl-05 K4 的 golden_match 以该目录为 `--gold-dir`，两侧互为独立对照。
- 测试宿主：`build_expected_m4.py` stdlib only、无 uuid/时间/随机、两次运行字节比对。

## 发现（编号｜严重度｜文件:行号｜问题｜依据 文件:行号｜修改建议）

- W1｜阻断｜act/05.yaml:20（item 4）vs :32｜SHA256SUMS 路径基准自相矛盾：合同规定「`<hex>  <相对仓库根路径>`」，而 verify 第 6 条在 `cd pipeline/corpus/_fixture/mini_ed01` 下执行 `shasum -a 256 -c m4/SHA256SUMS`——仓库根相对路径在该 CWD 下必报 No such file；V9（verify.sh 内）同理取决于 CWD。两者必有一个不可达｜act/05.yaml:4（item 4 原文）、:32（verify）；对照 `shasum -c` 以 CWD 解析路径的语义｜统一以 fixture 目录为基准（条目写 `m4/<file>`），V9 与 verify 第 6 条均在 `$FIX`（fixture 目录）内执行 `shasum -c`；或改为仓库根基准并把两处消费方都固定在仓库根执行——二选一，两处同步。
- W2｜阻断｜act/05.yaml:17｜`ruling_m4_d001.yaml` 按 §52 追加 `synthetic_fixture`/`actor_ref` 后不再与 impl-05 README 附录 A「逐字」一致，而 impl-05 act/07 的 `test_tests_data_equals_fixture_gold` 要求 `tests/data/appendix_a` 四文件与 fixture `m4/` 同名文件**字节相同**（含裁决件），impl-05 act/00 又按附录 A「逐字」落 appendix_a（四键）——两 ACT 按现文执行后 K4 该用例必 FAIL；act/05 的交接只覆盖了第 53 条的 contract 放宽，未覆盖附录 A/act/00 appendix_a/act/07 字节等同的联动｜act/05.yaml:15-17；impl-05 act/00.yaml:10、act/07.yaml:64（test_tests_data_equals_fixture_gold）、README.md:456（附录 A 裁决件四键）｜act/05 措辞改为「三件提交件逐字取附录 A；裁决件按 §9.7 第 52 条在四键上追加两键」，并把「impl-05 附录 A 裁决样例补两键 + act/00 落地说明同步」登记进交接（随第 53 条合并返工）。
- W3｜阻断｜act/12.yaml:67｜旧名清零 `grep -cE 'candidate_batch|model_run|candidate_diff_report' INTERFACES.md # 0` 不可达：`INTERFACES.md:321`（§3.15「不在本包范围」）残留 `model_run`，而 contract A–K 未覆盖该节，执行后 grep 计数 =1 → verify FAIL → on_fail 停手｜INTERFACES.md:321；act/12.yaml:15-44（contract 覆盖面）｜contract 增补 §3.15 行改写（删除 `model_run` 或注明其随 D-01/P6 退出提名），或把该 verify 的旧名 grep 限定为 §4/§2.4/§3.2 改写范围（如按行区间或先过滤）。
- W4｜重要｜act/05.yaml:27、:33｜V11 与 verify 循环以 `event_kind:|dispute_id:` 探测「人工裁决/签发类金标」，但 `m4/candidate_set.yaml` 的 disputes 条目亦含 `dispute_id` 键：该文件若按 YAML 书写会被误标 MISSING；合同仅暗示其为 canonical JSON 字节（「其字节即被哈希对象」），未钉死存储格式与 canonical 口径（separators/ensure_ascii），与 impl-05 R1 的 F1（canonical_json 两处定义不一致）联动｜act/05.yaml:18、27、33；impl-05 act/01.yaml:76（candidate_bytes = canonical_json）｜V11/verify 循环限定为 `event_kind:`（或仅扫 `ruling_*.yaml`）；并在合同明示 candidate_set.yaml 内容为 canonical JSON 字节且口径与 impl-05 修复后的 `canonical_json` 完全一致。
- W5｜重要｜act/05.yaml:19（item 3）｜`expected/m4.stage_package.yaml` 经 V5 扩展后按 `stage_package.schema.json` 校验，required 含 `stage_package_id`、`artifact_revision_id`、`manifest.processing_run_id/step_run_id/input_artifacts/output_artifacts`、`lineage.upstream_artifacts/transformations`、`logs`、`failures`；m4 真实 ID 运行期随机（impl-05 act/04 用 `ids.new_id`），expected 只能占位，但合同只列 payload/counts/content_sha256/validation.passed，未给占位规则，也未注明 impl-05 act/07 golden_match 不比对标识字段｜act/05.yaml:19、23；openspec/schemas/stage_package.schema.json（required 实测）；impl-05 act/07.yaml:37-38（golden_match 比对范围）｜item 3 补「信封含全 required 键；`pkg_m4_`/`rev_` 用固定占位 hex；lineage/logs/failures 最小占位；impl-05 golden_match 不比对 stage_package_id/artifact_revision_id/manifest.input_artifacts」。
- W6｜建议｜act/05.yaml:22｜「m1–m3 判定与输出字节不变」与第 6 条自身对 V5/V6 的 emit 文本变更（`m1/m2/m3` → `m1/m2/m3/m4`）矛盾｜act/05.yaml:23-24｜改为「m1–m3 判定结论不变（仍全 PASS、末行 FIXTURE OK），V5/V6 的 emit 文本按第 6 条同步」。
- W7｜建议｜act/12.yaml:24｜§2.4 卡片冻结输入缺 `corpus_package`：impl-05 act/04 frozen 为 {m3 包, corpus_package, corpus_spans, technique_profile} + 全部提交件共 7 项，act/07 inputs_frozen 同口径｜impl-05 act/04.yaml:22、act/07.yaml:22｜卡片冻结输入补 `corpus_package`，保持对账基准与实现契约一致。

## 判定

**REWORK**（阻断 3：W1、W2、W3；重要 2：W4、W5；建议 2：W6、W7。）

总评：两个 ACT 的裁决落位（第 47–52 条）、写范围纪律、合成标记三要素与金标数值本身全部正确；阻断集中在合同文本的自洽性（SHA 路径基准、旧名清零范围、裁决件「逐字」与字节等同测试的联动），修复均为局部文本修订，不动摇包结构。W2/W4 需与 impl-05 的第 53 条返工合并处理。

（审查者：W4-R5；以 HEAD `8fb9189` 只读核查；`git diff --check` 无输出。）

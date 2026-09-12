# impl-09：M1 Source Intake + M2 Digitization & Correction 真实最薄接入（§9、§10、§10.1、§22.1）

状态：`DRAFT`（起草 Agent 产出，待主 Agent 裁决 §4 后改写为 READY；未写 PROMPT 与 ACCEPTANCE）

## 1. 目标

把目前只由 `pipeline/ledger/fixture_ingest.py` 从 fixture 常量**模拟灌入**的 m1、m2 两个阶段，换成读取真实素材的最薄 Module：

1. **M1（`pipeline/source_intake/`）**：从真实页图目录（`ocr/data_work/sanche_pages/page_NNN.png`）和一份申报件读入字节，计算 SHA-256 与 PNG 尺寸；把页图作为 `source_asset` 写入 Ledger 的本地 Object Store；生成与 fixture `manifest.yaml` 同形的 `source_manifest` 修订并封存。Work、Edition、EditionPart 身份来自申报件，不新增 ID 前缀。
2. **M2（`pipeline/digitization/`）**：**不调用 OCR 引擎**，只登记 `ocr/data_work` 里已有的 OCR 结果。每页登记为一个 `ocr_page` 修订。异常页的人工终态来自用户亲笔的决定表，逐条走 §7.1 的 `await_human → record_human_event → resume`，登记为 `human_event`。然后由独立实现的 M2 Gate 按 §10.1 放行，产出 `ocr_page_set` 与 m2 StagePackage。
3. **来源不可区分**：M3（`pipeline/corpus_compiler/`）零改动，读本包产物与读 fixture_ingest 产物走同一路径。用前三页做判据：真实 M1→M2→M3 产出的 `corpus_spans` 字节必须等于 fixture 金标 `spans.yaml`。
4. **真实前十页跑通**：page_001..010 走通 M1→M2→M3（结构层），这是 §22.3 阶段 1「真实前十页上各跑通一次」中 M1–M3 段的判据。
5. **素材缺失**：页图或 OCR 工作根缺失时，打印 `BLOCKED_SOURCE_ASSET_MISSING <路径>`，退出码 3，不写 Ledger，不伪造任何字节或哈希。

本包是 **intake_only** 画像：人工校对完成度、OCRProfile、电子文本清洗都不做，一律在验收脚本中报 `BLOCKED`（见 D-09-05、D-09-10）。

## 2. 完成判据（本包唯一的「做完」定义，按 §4 推荐项书写；裁决不同则由主 Agent 改写）

```bash
export LC_ALL=en_US.UTF-8; PY=.venv/bin/python
$PY -m unittest discover -s pipeline/source_intake/tests -t . 2>&1 | tail -1   # OK
$PY -m unittest discover -s pipeline/digitization/tests -t . 2>&1 | tail -1    # OK
bash openspec/acceptance/m1-replay.sh; echo exit=$?
#   本机有十张页图：5 行 PASS + BLOCKED epub_txt_replay + SUMMARY pass=5 fail=0 blocked=1；exit=2
#   缺任一页图：若干行 BLOCKED_SOURCE_ASSET_MISSING <路径> + SUMMARY pass=0 fail=0 blocked=1；exit=3
bash openspec/acceptance/m2-export-integrity.sh; echo exit=$?
#   页图 + OCR 工作根 + 申报件 + 用户决定表齐全：6 PASS + 3 BLOCKED（ocr_profile/proofreading/text_sanitization）
#     SUMMARY pass=6 fail=0 blocked=3；exit=2
#   缺申报件或用户决定表：5 PASS + BLOCKED real10_chain + 3 BLOCKED；SUMMARY pass=5 fail=0 blocked=4；exit=2
#   缺页图或 OCR 工作根：BLOCKED_SOURCE_ASSET_MISSING 行；exit=3
bash openspec/acceptance/m3-coverage.sh >/dev/null; echo exit=$?   # 回归：仍为 2（impl-02 README:13）
bash openspec/acceptance/run_all.sh | tail -1                       # 回归：仍为 SUMMARY pass=2 fail=1 blocked=8（本包不改）
```

这两份脚本是 §19.0 已登记的 M1、M2 差距判据（规格 905–906 行，修复后应 exit 0）。本包只闭合「PNG 派生页图 + 既有 OCR JSON」这部分，所以返回 **2**，差距仍记为未关闭。这与 m3-coverage 的先例一致（impl-02 README:17）。

## 3. 依据（只读来源，文件:行号）

- 规格 `openspec/learn-system-blackbox-architecture.md`
  - §2 第 7 条（新修订不可覆盖、entity_id 复用）:37；§3 EditionPart 定义:59
  - §5 PendingQueue「M2 异常页与低置信字」:119–120；§6.1 Part Gate 与失败为零:149
  - §7 StepRequest 字段:187–193；「只能读取冻结 Artifact，不得读工作目录最新文件」:207；§7.1 人工事件写回与 resume_token:211–220
  - §8 StagePackage 六件:232–243；§8.1 entity_id 与 artifact_revision_id:257–261；UUIDv4 发号:288；非法格式:306
  - §8.2 ReviewDecision 八类:355–364；Artifact 状态与迁移:386–404
  - §9 M1 输入输出与 Object Store:442–457
  - §10 M2 链路、必留项、OCRProfile、清洗、Gate:459–480；§10.1 三终态与放行规则:482–494
  - §11 扫描来源 Span 回到页码/字框/原图:511；§16 坐标系同源:714；SourceAssetPack 三档:717–723
  - §17 Object Store、权利范围、事务序列:821–836；§17.1 Checkpoint 落盘粒度与恢复:843–846
  - §19 M1/M2 差距行:875–876；§19.0 m1-replay / m2-export-integrity:905–906
  - §20 十一条:937–947；§22.1 首纵切三元组与素材缺失:966–969；§22.2 纵切终点:974–976；§22.3 阶段 1 判据:991；§22.4 M2 不入首纵切:998
- `openspec/legacy-storage-transition.md`：OCR 页 JSON 与 logs 决议「迁移」:23；LegacyImportReport:16；首纵切素材可移植性警告:65–67
- `openspec/ocr-profile-parameterization.md`：人工抽样正确率门槛:68–70；每次 OCR StepRun 必存项:74–82；最少代码边界:88–94
- `openspec/id-prefix-registry.md`：只引用已登记前缀、新增流程:93–97（本包不新增前缀）
- `openspec/schemas/stage_package.schema.json`、`step_request.schema.json`、`step_result.schema.json`、`artifact_ref.schema.json`
- `pipeline/ledger/fixture_ingest.py`：阶段输出类型:43–47；m1 任务名 `ingest_source`:54；m2 每页任务、人工事件内容:179–199；每 task 一个 Checkpoint、human_decisions 累积:217–252
- `pipeline/ledger/service.py`：`RUN_ARTIFACT_TYPES`:66；`create_processing_run`:319；`put_artifact`（`prev_revision_id`、`rights_scope`）:442；`put_run_artifact`:528；`seal_revision`:599；`supersede_revision`:678；`register_stage_package`:718；`record_transformation`:777；`await_human`:885；`record_human_event`:922；`resume`:965；`finish_step_run`:1132；`fail_step_run`:1187；已封存阶段拒写 Checkpoint:1280–1286；`write_checkpoint`:1364
- `pipeline/corpus_compiler/inputs.py`（M3 对 m1/m2 的解析规则，**本包输出契约的对账基准**）：m1:26–55；m2:58–95；ocr_page_set:98–118；technique_id:121–124
- `pipeline/corpus_compiler/step.py`：M3 输入契约 C2–C4（ocr_pages[].page/sha256、terminal_states 严格相等、人工事件顶层 page）:468–523
- `pipeline/corpus_compiler/compiler.py`：终态闭集:24；known_unrecognizable 页有行即拒:108–111；impl-02 README:36（排除页规则）；impl-02 act/01.yaml:29、:33（ss_ 句序 >99 → ID_001）、:35（字框按 parent 收集）
- fixture `pipeline/corpus/_fixture/mini_ed01/`：`manifest.yaml`（顶层键与 source_assets 形状）、`anomalies.yaml`、`expected/m1|m2.stage_package.yaml`（payload、counts、content_sha256）；`verify.sh`:363–365（m2 content_sha256 规则）、:403–422（页图哈希与 PNG 尺寸校验）；`tools/build_fixture.py`:106–125（引号规则）、:165–208（异常证据取键子集）、:270（build_manifest）
- OCR 工具（只读）：`ocr/src/gujiorc/core/models.py`（PageResult/CharBox，orig_char 永不覆盖）；`core/anomaly.py`（assess_layout 四信号、register_anomaly 形状）；`core/audit.py`:11–17（审计 action 闭集）；`core/storage.py`:51–55（页 JSON 以 `indent=2, ensure_ascii=False` 写出）；`ocr/HANDOFF_OCR_FIXES.md`:245–266（page_010 盘面页登记，弧线切分未实现）；`ocr/run_sanche10.sh`（**第一步 `rm -rf data_work/data … logs`，严禁执行**）

## 4. 待主 Agent 裁决

每条都给出选项、推荐与理由。「推荐」只是起草者意见，不是定案。ACT 按推荐项书写，裁决不同时由主 Agent 改写对应 ACT。

### D-09-01 宿主目录与模块划分
规格 §9、§10（442–480）与 §19（875–876）都没有给出 M1、M2 的宿主目录名。
- A：两个包 `pipeline/source_intake/`（M1）与 `pipeline/digitization/`（M2），与 `pipeline/corpus_compiler/` 平级，各自有 CLI、Gate、验收模块。
- B：单包 `pipeline/intake/`，下设 m1、m2 子模块。
- C：挂进 `ocr/` 工具旁路。这违反 §2 第 2 条独立 Module，而且 ocr 有自己的 venv 与 PaddleOCR 依赖。
- **推荐 A**：与 §5 的八个 Module 一一对应；两个 Gate 独立；将来 EPUB/TXT 清洗可直接落进 digitization。

### D-09-02 EditionPart / Work / Edition 身份与申报件落点
EditionPart 用 `art_<32hex>`，必须跨重跑稳定（§8.1:257），且只能用 uuid4 发号（§8.1:288），不能按内容派生 uuid5。Work 没有登记前缀：登记册 §3.1 只有 `src_`，而 `pipeline/registry/works/_TEMPLATE.yaml` 里的 `work_<简称>` 未登记。
- A：申报件 YAML 进 Git（只含元数据，不含受版权限制的内容）。由主 Agent 一次性用 uuid4 生成 art_ 并写入：source_id、work_title、edition_note、technique_id、rights_status、release_policy、edition_part{artifact_id,label,pages}、asset_root_ref、derivation。落点 `pipeline/registry/intake/src_sanche_ed01/part_p001_p010.submission.yaml`。
- B：M1 每次新发号，并按 (source_id, label) 在 Ledger 查找复用。Ledger 没有这个查询接口，要改 impl-01。
- C：首次发号后写回 `var/`（不进 Git，克隆后身份丢失）。
- **推荐 A**。补充三点：
  - 真实前十页的 EditionPart 与 fixture 的 `art_…e1`（前三页）是两个不同的 Part，只各自出现在临时 Ledger 中。
  - §22.2:974 称「卷一，取 page_001..010」，但 §3:59 优先按卷界划 Part，而前十页并非完整卷一。建议 label 写「卷一·前十页（page_001–page_010，连续页区间）」。
  - Work 身份沿用 `src_<work>` 的 `<work>` 段加 work_title，不新增前缀。

### D-09-03 人工终态决定表的作者与落点
§10.1 要求异常页的终态由人工决定，`known_unrecognizable` 必须附理由与证据（486–488）。实测 OCR 工作根里只有机器登记的 `anomalies.jsonl`（page_002 `no_text`、page_010 `irregular_layout`），**没有任何人工终态记录**；fixture 的 `decided_by: fixture` 只对前三页宿主有效。
- A：用户亲笔写 YAML 决定表进 Git（`…/part_p001_p010.m2_decisions.yaml`，每条含 page、terminal_state、reason、decided_by、note）。执行者与验收脚本只读它；缺失时 `real10_chain` 报 BLOCKED。
- B：在 FastAPI + Vue 校对工具里加终态 UI。超出最薄形态，且 §10:476 要求沿用现有工具。
- C：主 Agent 或执行者代填。这等于伪造人工决定。
- **推荐 A**。起草者、执行者都不得写真实决定表；执行者只在 tempfile 里构造测试用决定表。

### D-09-04 page_010 盘面页的终态路径
page_010 的原始 OCR 有 119 行、359 个字框，四个异常信号全中（`ocr/HANDOFF_OCR_FIXES.md`:245–266）。现有 M3 与它有两处冲突：
- M3 对「known_unrecognizable 但有行」的页直接拒绝（compiler.py:108–111）。
- ss_ 句序只有两位（§8.1:276），119 行会触发 ID_001（impl-02 act/01.yaml:33）。

选项：
- A：M2 先按原字节封存原始 `ocr_page` 修订；再以 `prev_revision_id` 派生一个「排除修订」（lines、chars 置空，`extra.m2_exclusion` 记原哈希与原行数、字数）；然后 `supersede_revision(原始, 派生)`（service.py:678），Checkpoint 引用派生修订。M3 零改动；原始 OCR 仍可按修订号精确重放（§8.2:392）。
- B：改 M3 规则，允许有行的 known_unrecognizable 页被排除。这要改 impl-02 契约与 Gate 判定。
- C：用户在 OCR 工具里人工转录后标 `manually_transcribed`。行数仍可能超过 99，M3 发号溢出。
- D：标 `deferred`。M2 Gate 阻断，§22.3:991「真实前十页跑通」不可达。
- **推荐 A**。风险：页内可识别的「三辰通載卷第一」等标题会随排除一起不进 CorpusPackage，须由用户在决定表 reason 中写明。

### D-09-05 M2 Gate 画像（校对完成度）
§10:480 要求「该 EditionPart 的校对和清洗任务必须全部完成」。实测十页共 2,757 个字框，其中 2,746 个 `pending`、11 个 `unrecognized`；人工编辑只有 page_001、page_004 两页，共 46 条审计事件。严格执行的话，真实前十页过不了 Gate。而 §22.4:998 写明 M2 不入首纵切、直接消费现有 JSON。
- A：`gate_profile: intake_only`。只判异常页终态、证据、页身份、排除一致性与字框结构；`proofreading: not_evaluated`；验收报 BLOCKED。照 impl-02 `structural_only` 的先例（impl-02 README:34）。
- B：全部字框为 verified 或 corrected 才放行。需要用户校对约 2,800 字。
- C：按 OCRProfile 抽样实际正确率 ≥95% 放行（ocr-profile-parameterization.md:68–70）。需要人工真值集，尚不存在。
- **推荐 A**。gate_profile 写入配置修订，M5/M8 可据此拒绝 `PUBLIC_RELEASE`。

### D-09-06 §7「只读冻结输入」与工作目录读取的边界
§7:207 禁止读工作目录的「最新文件」，但 M1 的页图目录、M2 的 OCR 工作根都在 Ledger 之外。
- A：把二者视为本 Module 的外部摄入边界。begin 前一次读入全部字节，并把逐文件 sha256 快照写进配置修订（该修订被 StepRequest 冻结）。begin 后只写这些已读入的字节。M2 在 begin 后再复核一次工作根哈希，漂移即以 `input_contract` 失败封存。
- B：先由一个独立登记步骤把 OCR 文件写成 Artifact，M2 StepRun 再冻结它们。Ledger 的 `put_run_artifact` 只允许 configuration、technique_profile（service.py:66、:548），要改 impl-01。
- C：不处理。
- **推荐 A**。

### D-09-07 新 artifact_type
Ledger 只校验 `^[a-z][a-z0-9_]*$`，没有类型登记表。已在用的类型：configuration、source_manifest、ocr_page、ocr_page_set、human_event、validation_report、step_log、failure_report、stage_package、corpus_*。本包需要新增：
- `source_asset`：页图原字节，对应 §22.1:967「登记到本地 Object Store」。
- `ocr_anomaly_log`：`logs/anomalies.jsonl` 原样字节。
- `ocr_audit_log`：`logs/audit.jsonl` 原样字节。
- `ocr_edit_history`：`logs/edit_history/<page>.json` 原样字节，有则登记。

选项：
- A：新增以上四类；质量报告嵌入 `validation_report`，不另设类型。
- B：合并为单一 `ocr_log`。Artifact 没有 role 字段，合并后无法区分。
- C：不登记日志。违反 §10:474「完整审计日志」与 legacy-storage-transition:23「迁移」。
- **推荐 A**。另请主 Agent 决定是否建立 artifact_type 登记表（目前不存在，各包各自约定）。

### D-09-08 source_manifest、ocr_page_set 内容形状与 m1/m2 payload
fixture 的 m1/m2 payload 含仓库路径（`source_manifest_path`、`ocr_pages[].path`、`anomalies_path`）。M3 不读 payload，只读：
- source_manifest 内容键（compiler.py:76–92、:201–203）；
- ocr_page_set 的 `ocr_pages[].page/sha256` 与 `terminal_states`（step.py:468–506）。

选项：
- A：source_manifest 的顶层键集合与顺序同 fixture `manifest.yaml` 逐字一致：`files: []`，`conversion` 记 M1 工具与 path_ref 列表，`content_status: machine_extracted` 保留。ocr_page_set 取 fixture 键的超集：path/anomalies_path 改记 OCR 工作根相对路径，每页另加 `artifact_revision_id`。m1/m2 StagePackage payload 以修订号取代路径，照 impl-02 以 `spans_revision_id` 取代 `spans_path` 的先例（impl-02 act/03.yaml:54）。
- B：payload 完全照抄 fixture。路径会指向不存在或无关的 fixture 文件，溯源错误。
- C：为 m1/m2 payload 另立 Schema。需要新 Schema，超出本包。
- **推荐 A**。附问：`content_status` 在来源清单上语义含糊，保留（形状一致）还是删去，请一并裁决。

### D-09-09 人工决定写回路径、decision_type 与 deferred
fixture_ingest 只 `put_artifact` 人工事件并写进 Checkpoint（fixture_ingest.py:226–247），没有走 §7.1 的 `await_human / record_human_event / resume`（规格 220）。
- A：单进程完整走 §7.1。每个有终态的页：put 并 seal human_event → `await_human([页修订])` → `record_human_event` → `resume` → 写 Checkpoint。决定表含 `deferred` 时，全部页登记完后 `await_human([deferred 页修订])`，停在 `awaiting_human`，不产出 ocr_page_set 与 StagePackage；resume_token 不落盘，续跑由后续包以 `supersede_step_run` 完成。
- B：遇 deferred 直接 `fail_step_run`（记为 Gate 失败）。
- C：照抄 fixture_ingest，不走 §7.1。
- `decision_type` 子选项：A1 传 None（§8.2 八类中没有「终态裁定」）；A2 传 `review_source_fidelity`。
- **推荐 A + A1**。awaiting_human 正是 §5 PendingQueue「M2 异常页」队列的语义来源。

### D-09-10 OCRProfile 缺失与「原始 OCR / 校订修订」分离
§10:476 要求批量 StepRun 读取冻结的 OCRProfile 修订，ocr-profile-parameterization.md:74–82 列出了每次必存项。现状：没有 Profile；页 JSON 被 Web UI 原地修改（字级 orig_char 保留，但 split/merge 前的原框只存在于 edit_history 撤销栈）。
- A：配置修订记 `ocr_profile_revision_id: null`，以及从页 JSON `extra` 观测到的 `bleed_thresh`、`col_gap_thresh`；validation_report 记 `ocr_profile: not_captured`；验收报 BLOCKED。
- B：本包实现最薄 OCRProfile YAML 与 Schema。要新增 Schema，而且要重跑 OCR 才有意义。
- C：忽略。
- **推荐 A**。

### D-09-11 验收脚本命名与 CLI 退出码
§19.0:905–906 已登记 `m1-replay.sh`、`m2-export-integrity.sh`。
- A：本包新建这两份 §19.0 脚本，均返回 2（照 m3-coverage 先例）；真实前十页判定放在 m2-export-integrity 的 `real10_chain` 项。
- B：另建 `intake-real10.sh`，§19.0 两脚本留待纵切后。
- C：两者都建。
- **推荐 A**。`run_all.sh` 本包不改（理由见 §10）。

附：CLI 中 `WriterLocked` 本包用退出码 4，而 M3 CLI 用 3（impl-02 act/03.yaml:70）。这样 3 专指素材或宿主缺失。是否统一，请裁决。

### D-09-12 与 M3 输入解析的接口风险（需 impl-02 负责方确认）
- (a) `resolve_m3_inputs` 汇总该 Part **全部** m2 Checkpoint 的页修订与终态，不按 StepRun 过滤（inputs.py:83–95）。若 M2 出现「awaiting_human 后被 supersede 的旧运行」，旧终态会混进来，导致 C3 严格比对失败。
- (b) m1 解析取首个 `ingest_source` 任务，不校验 m1 StepRun 是否 succeeded（inputs.py:30–55）。
- (c) ss_ 句序两位上限（见 D-09-04）。

选项：
- A：本包在 begin 前拒绝「同一 Part 已有任何 m1 或 m2 运行」（不支持续跑），保证每个 Part 各只有一条运行链。同时登记后续项：续跑包与 M3 inputs 按「最新 succeeded StepRun」过滤配套落地。
- B：本包立即改 impl-02 的 inputs.py。越界，而且 impl-02 返工正在进行。
- C：不处理。
- **推荐 A**。

### D-09-13 字框与行文本不一致
实测：page_001 有 2 行、page_004 有 1 行的 `line.text` 不等于其子字框拼接；page_006 有 1 个、page_010 有 3 个孤儿字框（parent 不指向任何行）。M3 以 line.text 切 Span、以 parent 收字框（impl-02 act/01.yaml:35），不一致会让字框锚点与原文对不上。
- A：M2 Gate 只把它记为警告写进 `validation_report.quality`，不阻断（intake_only）；M5 的 G3 落地时再升级为阻断。
- B：阻断 Gate，由用户在 OCR 工具修正。
- C：M2 自动以字框重算 line.text。这是静默改文，违反 §11:500「不再静默纠正文义」与 §10:478 的精神。
- **推荐 A**。

### D-09-14 权利、准入决定与源 PDF 派生关系
§9:452 要求记录「来源说明、权利和准入决定」；§17:834 要求每个 Artifact 记权利范围。页图派生自本机 `~/Downloads` 下的 PDF（ocr/run_sanche10.sh），该 PDF 不进仓，也没有哈希记录。
- A：权利状态与发布策略取自申报件（沿用 fixture 已登记的文本「文字公版；扫描件分发权 unconfirmed」）；source_asset 以 `rights_scope="internal"` 写入；准入决定只记在配置修订。申报件的 `derivation.parent_sha256` 置 null，并在 note 写明未登记，不得伪造。
- B：M1 额外登记一条准入 human_event，M1 进入 awaiting_human 等用户决定。
- C：不记。
- **推荐 A**。补登源 PDF 哈希留给纵切后。

## 5. 上游输入契约（本包消费什么）

### 5.1 M1

| 输入 | 形状 | 来源 | 缺失时 |
|---|---|---|---|
| 页图目录 `--asset-dir` | `<page>.png`；PNG 签名 + IHDR；页名 `^page_[0-9]{3,4}$` | 本机 `ocr/data_work/sanche_pages/`（被 `ocr/.gitignore` 忽略，legacy §6） | 全部缺失路径各打印一行 `BLOCKED_SOURCE_ASSET_MISSING`，exit 3，零写入 |
| 申报件 YAML `--submission` | 顶层键闭集 `source_id, work_title, edition_note, technique_id, rights_status, release_policy, edition_part{artifact_id,label,pages}, asset_root_ref, derivation{parent_kind,parent_ref,parent_sha256,note}` | D-09-02 | `M1 REFUSED`，exit 2 |
| Ledger | 无上游修订；同一 Part 不得已有 m1 Checkpoint（D-09-12） | — | `M1 REFUSED`，exit 2 |

### 5.2 M2

| 输入 | 形状 | 来源 | 缺失时 |
|---|---|---|---|
| m1 `source_manifest` 修订 | m1 Checkpoint 中 `task_id=="ingest_source"`、status succeeded 的修订恰 1 个；artifact_type `source_manifest`；sealed；m1 StepRun succeeded | 本包 M1（或 fixture_ingest 灌入的 m1，形状相同） | `M2 REFUSED`，exit 2 |
| OCR 工作根 `--ocr-root` | `data/<page>.json`（PageResult.to_dict：必含 page、image、width、height、lines、chars）；`logs/anomalies.jsonl`（必需，register_anomaly 形状）；`logs/audit.jsonl`（必需，audit.log_event 形状）；`logs/edit_history/<page>.json`（可选） | 本机 `ocr/data_work/`（Git 忽略；legacy-storage-transition:23） | exit 3 |
| 决定表 YAML `--decisions` | `schema_version: "1.0.0"`、`edition_part_artifact_id`、`entries[{page, terminal_state∈三终态, reason, decided_by, note?}]` | 用户亲笔（D-09-03） | 异常页缺决定 → `M2 REFUSED`（列出页名），exit 2，零写入 |

## 6. 对下游的输出契约（与 fixture_ingest 灌入形状对账）

「M3 消费」一列按 `pipeline/corpus_compiler/inputs.py` 与 `step.py` C2–C4 核对。

| 对象 | fixture_ingest 灌入 | 本包真实产出 | M3 消费 | 等价判据（ACT） |
|---|---|---|---|---|
| ProcessingRun | fixture 常量 `prun_…f1`，edition_run | M1 新建 edition_run（uuid4），M2/M3 沿用 | m2 StepRun 的 processing_run_id | 06 |
| 配置修订 m1 | `{"stage":"m1","tool","tool_version"}` | 另加 `submission`、`asset_snapshot` | 否（stage 键由 Ledger 推导） | 01 |
| m1 Checkpoint | 1 个：`ingest_source` | 页数 + 1 个：`asset_page_NNN`… → `ingest_source`（末个） | 是：只取 `ingest_source` | 01、06 |
| `source_manifest` 内容 | fixture `manifest.yaml` 原字节 | 顶层键与顺序同 fixture；`source_assets` 值与 fixture 逐项相等（前三页）；`files: []`；`conversion` 记 M1 | 是：source_id、work_title、technique_id、edition_part、source_assets[].page/sha256 | 00、06、07 |
| `source_asset` | 无 | 每页一个，页图原字节，rights_scope internal | 否（M8 SourceAssetPack 将用） | 01、07 |
| m1 Transformation | `ingest_source`，输入 [] | 同名，输出 [manifest + 各 asset] | 否 | 01 |
| m1 StagePackage | payload 含 `source_manifest_path` | payload 用 `source_manifest_revision_id` 与 `source_asset_revision_ids`；counts `{pages, source_assets}`；content_sha256 = sha256(manifest 字节) | 否 | 01、07 |
| m2 StepRun 冻结输入 | [source_manifest] | [source_manifest] | 否 | 04 |
| m2 Checkpoint | 每页 1 个：task_id = 页名、terminal_state、human_decisions 累积 | 同左 | 是：页修订、终态、末个 Checkpoint 的 human_decisions | 04、06 |
| `ocr_page` 内容 | fixture pages/*.json 原字节 | OCR 工作根页 JSON 原字节；known_unrecognizable 且有行的页另有派生排除修订（prev 指向原始，原始 superseded） | 是：lines、chars、sha256 | 02、04、06 |
| `human_event` 内容 | anomalies.yaml 条目 JSON：page、terminal_state、layout_type、evidence、decided_by、note | 同名键值 + reason、decision_sheet_sha256、raw_page_sha256；经 record_human_event 登记 | 是：顶层 page | 02、04 |
| `ocr_page_set` 内容 | expected m2 payload JSON：ocr_pages[page,path,sha256]、anomalies_path、terminal_states | 超集：每页另加 artifact_revision_id；path 为 OCR 工作根相对路径 | 是：ocr_pages[].page/sha256（有效修订哈希）、terminal_states | 02、04、06 |
| 日志 | `step_log` 一条 | `step_log` + `ocr_anomaly_log` + `ocr_audit_log` + `ocr_edit_history`（有则） | 否 | 04、08 |
| m2 Transformation | `digitize_pages`，输出 [ocr_page_set] | 同名，输出 [ocr_page_set, 各有效页修订, 日志修订]，human_event_revision_ids = 人工事件 | 是：输出中唯一的 ocr_page_set | 04 |
| m2 StagePackage | counts `{ocr_pages, lines, chars, anomalies}`；content_sha256 = sha256(按页名排序的页哈希以 `\n` 连接 + `\n`) | 同规则（按有效修订计）；前三页与 expected m2 的 counts、content_sha256 逐值相等 | 否 | 02、06、08 |

对 M5、M6、M8 的附带承诺（供并行草案对账）：
- `source_assets[].width/height` 取自 PNG IHDR，与页 JSON 的 width/height 由 M2 Gate 核对一致，满足 §16:714 坐标系同源；
- `source_asset` 可按 sha256 从 Object Store 取回字节，这是 SourceAssetPack `derived_page_images_only` 与 `reference_and_hash_only` 的前提（§16:717–723、§20 第 8 条）；
- validation_report 的 `gate_profile: intake_only`、`proofreading: not_evaluated`、`ocr_profile: not_captured`，供 M5/M8 做 fail-closed 判定。

## 7. 范围

写（执行者）：`pipeline/source_intake/**`（新建）、`pipeline/digitization/**`（新建）、`openspec/acceptance/m1-replay.sh`（新建）、`openspec/acceptance/m2-export-integrity.sh`（新建）。

写（非执行者，裁决后）：申报件由主 Agent 写（D-09-02）；决定表由用户写（D-09-03）。

禁止：
- 改 `openspec/acceptance/run_all.sh`、`m3-coverage.sh`、规格正文、`openspec/schemas/**`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`pipeline/registry/**`、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`；
- 写 `ocr/` 下任何文件，包括 `ocr/data_work`；**执行 `ocr/run_sanche10.sh`（会 `rm -rf` OCR 结果与审计日志）**；调用 PaddleOCR 或任何 OCR 引擎；
- 调用任何模型 API；新增依赖（不得用 PIL，PNG 尺寸用 struct 读 IHDR）；新增 ID 前缀；
- 伪造页图、哈希或人工决定；执行者代写真实决定表；
- 测试写 `var/` 或 fixture；
- 生产代码读取 fixture 路径（验收模块只经 `--fixture` 参数读取）；
- 执行者写台账或 ACCEPTED。

## 8. 目录规划（落地后）

```text
pipeline/source_intake/
  __init__.py        M1_TOOL / M1_TOOL_VERSION / 任务名常量
  errors.py          IntakeRefused、SourceAssetMissing
  serialize.py       dump_manifest_yaml（64 位十六进制加双引号，私有 Dumper）
  submission.py      load_submission（申报件闭集校验）
  assets.py          png_size、read_assets、unlisted_assets
  manifest.py        build_source_manifest、manifest_bytes（纯函数）
  step.py            run_m1（§17 事务序列）
  __main__.py        python -m pipeline.source_intake
  acceptance.py      m1-replay 判定
  tests/             helpers.py test_manifest.py test_step.py test_acceptance.py
pipeline/digitization/
  __init__.py        M2_TOOL / 版本 / GATE_PROFILE / 终态常量 / 人工审计 action
  errors.py          DigitizationRefused、OcrWorkMissing
  ocr_work.py        read_ocr_work、snapshot_matches
  decisions.py       load_decisions
  plan.py            required_terminal_pages、excluded_page_bytes、plan_digitization（纯函数）
  gate.py            evaluate_m2_gate（独立实现，不 import plan/decisions/ocr_work）
  inputs.py          resolve_m2_inputs（Ledger 读接口）
  step.py            run_m2（§17 事务 + §7.1 人工事件）
  __main__.py        python -m pipeline.digitization
  acceptance.py      m2-export-integrity 判定
  tests/             helpers.py test_plan.py test_gate.py test_step.py test_step_failures.py test_parity.py test_acceptance.py
openspec/acceptance/m1-replay.sh
openspec/acceptance/m2-export-integrity.sh
```

## 9. 现状调研（起草时实测，2026-09-11，只读）

OCR 工作根 `ocr/data_work/`（Git 忽略）：`data/page_001..010.json`、`sanche_pages/page_001..010.png`、`logs/anomalies.jsonl`（2 条）、`logs/audit.jsonl`（46 条）、`logs/progress.json`、`logs/edit_history/page_001.json|page_004.json`。page_001..003 的页 JSON 与 fixture `pages/` **逐字节相同**；三张页图哈希与 fixture manifest 相同。

| 页 | 行 | 字框 | 最长行字数 | pending / unrecognized | source=manual | 孤儿字框 | text≠字拼接 | 审计事件 | 异常登记 |
|---|---|---|---|---|---|---|---|---|---|
| page_001 | 4 | 37 | 17 | 32 / 5 | 5 | 0 | 2 | 41 | — |
| page_002 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 | no_text |
| page_003 | 39 | 193 | 14 | 193 / 0 | 0 | 0 | 0 | 0 | — |
| page_004 | 82 | 339 | 11 | 337 / 2 | 2 | 0 | 1 | 5 | — |
| page_005 | 67 | 283 | 9 | 283 / 0 | 0 | 0 | 0 | 0 | — |
| page_006 | 67 | 304 | 9 | 303 / 1 | 0 | 1 | 0 | 0 | — |
| page_007 | 73 | 441 | 14 | 441 / 0 | 0 | 0 | 0 | 0 | — |
| page_008 | 84 | 567 | 7 | 567 / 0 | 0 | 0 | 0 | 0 | — |
| page_009 | 49 | 234 | 14 | 234 / 0 | 0 | 0 | 0 | 0 | — |
| page_010 | **119** | 359 | 11 | 356 / 3 | 0 | 3 | 0 | 0 | irregular_layout（4 信号） |

全部页 JSON：`width=1203`、`height=1654`，`image` 为 `data_work/sanche_pages/<page>.png`，`extra` 含 `bleed_thresh`、`col_gap_thresh`。

页图 SHA-256（`shasum -a 256 ocr/data_work/sanche_pages/*.png`；执行时不一致即停手上报，不得改哈希）：

```text
page_001 e46bffa38119df1bb03f5a38e4f3f99405a476ba5d7b6a7c489956ccf2e58e65
page_002 aa5301d98c230a875eeb0b8d8d071393e4d15546d4f352cfb53747af1590f753
page_003 3c138fc9f32d2cfefe029d62dec2a9a0ce0f095c373af41a8a98f4c8f8afb268
page_004 b880043e64456923894992666605d772f7ec21a271d829aab5ab547923dd91bb
page_005 fdf295ca44b0868aa6b7b5d26a47844b8d2351ad2c22374f7741af13106e80d4
page_006 32e1be9ef0b2ed93afe55c0a4e69d26188fb9089c48bdc053d948ebbeb665ef5
page_007 5ee9aa8f7ac470a7e7171baca882b7047f966f603d258991fe2423441d62481a
page_008 b399085760c207b391d26086fb48ace14ce74412eb6f93e3caaca32369aa8159
page_009 64f25a81b80be8b66e487d5ec459dd7de40c81e7beafe36534d01ea128051fdf
page_010 de0ce92faeadd4870d4ae15fee8ae31cea3dcd9deab904e69fe8db11a1d84367
```

已验证的序列化事实：fixture `manifest.yaml` 经 `yaml.safe_load` 再用「私有 SafeDumper 子类，仅对 `^[0-9a-f]{64}$` 字符串加双引号，参数同 build_fixture.dump_yaml」写出，**字节完全相同**（2087 字节），且不污染全局 `yaml.SafeDumper`。ACT 00 的往返金标测试以此为据。

起草时基线：`pipeline/ledger` 测试 OK（74）；`run_all.sh` → `SUMMARY pass=2 fail=1 blocked=8`；fixture `verify.sh` → `FIXTURE OK`（本机有前三页页图）。

## 10. §20 与 §19.0 受益条目

| 条目 | 本包贡献 | run_all.sh 状态变化 |
|---|---|---|
| 20.1 Part 严格按 M1–M6 Gate | M1、M2 首次有真实 Gate 与「未通过不得流入」（M3 拒绝 awaiting_human 的 M2） | 不变：仍 BLOCKED（Local Orchestrator、M4–M6） |
| 20.2 从最近 Checkpoint 恢复 | M2 每页一个 Checkpoint、人工事件经 §7.1 登记，可被 `recover_from_checkpoint` 复用 | 不变：已 PASS（fixture 宿主） |
| 20.3 语义转换记录齐全 | 真实 M1/M2 的 Transformation 记录输入、输出、工具、配置、校验、人工决定 | 不变：已 PASS；是否把真实路径纳入 20.3 留待主 Agent |
| 20.4 双向追溯 | 原始页图字节进入 Object Store，span 的 `image_sha256` 可解析回原图，补上追溯最上游一段 | 不变：仍 BLOCKED（M8） |
| 20.8 SourceAssetPack 受控引用可解析 | 提供可由本地 Object Store 解析的页图引用、SHA-256、页标识、权利范围 | 不变：仍 BLOCKED（M8） |
| 20.10 换 OCR 不改相邻接口 | M2 输出接口（ocr_page/ocr_page_set）与引擎无关，M3 零改动的等价判据即其雏形 | 不变：仍 BLOCKED（Contract Registry） |
| §19.0 m1-replay / m2-export-integrity | 退出码由 127 变 2 | — |
| §22.3 阶段 1「真实前十页跑通」 | 闭合 M1→M2→M3 段（`real10_chain`） | — |

结论：§20 没有任何一条会因 M1/M2 最薄接入而由 BLOCKED 变 PASS，本包不改 `run_all.sh`，理由与 impl-02 决定 8 相同（impl-02 README:41）。

## 11. 与其他模块的接口假设（供并行草案对账）

1. M3 `resolve_m3_inputs` 与 `run_m3(service, edition_part_id, *, batch_size=10)` 的签名与规则以 impl-02 act/03.yaml 为准。本包 ACT 04、06、08 依赖 impl-02 `ACCEPTED`（含返工 ACT 05）。
2. M3 不区分来源：M3 只读 source_manifest 内容、m1 `ingest_source` 任务、m2 每页 Checkpoint、末个 m2 Checkpoint 的 human_decisions、m2 Transformation 输出中唯一的 ocr_page_set。本包保证这五处与 fixture_ingest 同形。
3. 每个 EditionPart × Stage 在本包只有一条运行链（D-09-12）；续跑与 M3 按 StepRun 过滤须配套另包。
4. M3 编译器把「known_unrecognizable ⇒ 有效修订 0 行」当作前提（compiler.py:108–111）。本包以派生排除修订满足它（D-09-04）。
5. M5（impl-03）若实现 G1/G3：页图哈希取 `source_manifest.source_assets[].sha256` 并可从 Object Store 取回字节；字框取有效 `ocr_page` 修订；原始 OCR 取派生修订的 `prev_revision_id`。
6. M8（impl-04）SourceAssetPack：读取 m1 StagePackage payload 的 `source_asset_revision_ids` 与 manifest 的 `release_policy`、`rights_status`；本包不做分发权判断。
7. Review Console（M6）只读显示 M2 的扫描与字框：以 `ocr_page` 有效修订加 `source_asset` 为数据源。CorrectionRequest 回流 M2 不在本包。
8. 若 Local Orchestrator 以 `run_status/stage_progress` 呈现 PendingQueue：M2 的 `awaiting_human` StepRun 的 `await_human` 事件 payload 就是「M2 异常页」队列。

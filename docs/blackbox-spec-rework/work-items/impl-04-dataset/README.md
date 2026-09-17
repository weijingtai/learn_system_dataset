# impl-04：M8 Dataset Compilation（§16）首切片——证据尾链发布包

状态：`READY_FOR_REVIEW`（W2-D 定稿 2026-09-12，依 `G7-RULINGS.md` §1 原则 P1–P9 与 §2 impl-04 裁决表；未经实现；派发前置见 §5.6）

## 1. 目标

在 `pipeline/dataset_compiler/` 落地规格 §16 M8 的**最小可判首切片**。输入是 Artifact Ledger 中已封存的 M3 StagePackage（impl-02 `run_m3` 真实产出）及其血缘上的 M1 清单、M2 OCR 页，外加经薄 M1 登记进 Object Store 的派生页图。首切片确定性编译以下内容，每个子包都是独立 Artifact：

- `SourceAssetPack`（`derived_page_images_only`）
- `EvidenceMapPack`：只闭合 SourceSpan → SourceAnchor → OcrPage/字框 → SourceAsset 页这**尾部四段**；KnowledgeEntry/Assertion/EvidenceLink 三段标 `not_compiled`
- `ReleaseManifest`：子包哈希清单、来源与修订对账、消费级别、水印与已知缺陷披露
- `ValidationReport`：独立实现的 fail-closed 发布 Gate
- `PublicationPackage` 与 m8 StagePackage

消费级别只签发 `INTERNAL_DEMO`。`DEV_SEARCH`/`PUBLIC_RELEASE` 进入 StepRun 后以 `admission` 失败封存，不降级、不重试。M4/M6/M7 与知识链前三段在首纵切内一律判 BLOCKED，不伪造（P1）。

完成判据（本包唯一的「做完」定义）：

```bash
export LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/dataset_compiler/tests -t . 2>&1 | tail -1
# 期望：OK（用例 ≥ 124；本机页图存在，不得出现 skipped）
bash openspec/acceptance/m8-span-identity.sh; echo exit=$?
# 期望：7 行 PASS（run_succeeded span_key_unique legacy_collision_exposed span_page_binding anchor_to_page_image glyph_closure reverse_index）
#       + 1 行 BLOCKED mentions_mapping + SUMMARY pass=7 fail=0 blocked=1；exit=2
.venv/bin/python -m pipeline.dataset_compiler.acceptance --fixture pipeline/corpus/_fixture/mini_ed01 --check publication; echo exit=$?
# 期望：8 PASS + BLOCKED knowledge_chain + SUMMARY pass=8 fail=0 blocked=1；exit=2
FIXTURE_ASSET_ROOT=/nonexistent bash openspec/acceptance/m8-span-identity.sh; echo exit=$?
# 期望（D3 裁决）：首行 BLOCKED m8_acceptance BLOCKED_SOURCE_ASSET_MISSING …；exit=3
bash openspec/acceptance/run_all.sh | tail -1
# 期望：SUMMARY pass=2 fail=1 blocked=8（ACT 08 之后 20.4/20.8 仍为 BLOCKED，只改写原因；D6）
```

退出码纪律（`m8-span-identity.sh`、`acceptance.py`、CLI 一致）：**0** 全部 PASS；**1** 任一判定 FAIL 或验收准备/运行/判定抛异常；**2** 无 FAIL 但有 BLOCKED（差距未关闭）；**3** 宿主缺失（缺 fixture、缺本机页图、缺 `.venv`/依赖）——与 impl-02 `m3-coverage.sh` 先例一致（`impl-02-corpus/README.md:40`）。

`m8-span-identity.sh` 是 §19.0 已登记的「M8 映射键碰撞」判据（`openspec/learn-system-blackbox-architecture.md:912`）。本包关闭**键身份**部分，但 concept→span 的 mentions 映射依赖 M4，所以脚本返回 **2**，差距仍记为未关闭。

## 2. 依据（只读来源，文件:行号）

- 裁决 `docs/blackbox-spec-rework/G7-RULINGS.md` §1（P1–P9）、§2（impl-04 裁决表）
- 规格 `openspec/learn-system-blackbox-architecture.md`：
  - §4 KnowledgeEntry 只能由 M8 从已审核对象编译（86–94）
  - §6.2 ReleaseRun（153–169）；§7 只读冻结输入（181–207）；§8 信封（232–251）
  - §8.1 `pkg_<stage>`（298）、`rel_`（299）、EvidenceLink 双标识（265）、`ent_`（318）
  - §8.2 内容成熟度（335–347）；§11.1 `evidence_level`，glyphbox 为「四点坐标」（523–528）
  - §13.1 G3（600）、G6 延至 M8（603）、G7 延至 M8（604）
  - §16 M8：冻结五项输入（661–668）、消费级别（670–678）、子包树（682–695）、ReleaseManifest（697）、子包必须独立 Artifact（699）、EvidenceMapPack 七段链与坐标同源及一票否决（703–715）、SourceAssetPack 三档与首纵切档（717–723）、GraphProjectionPack（725）、AnchorContractPack（727–734）、QueryContractPack（745–751）
  - §17 事务（836）；§17.1 每 task 一个 Checkpoint（843）；§18 页 → Release 反查（859）
  - §19 M8 行（882）、M4 行（878）、测试宿主匮乏行（890）；§19.0 判据（912）
  - §20 总则（935）、20.4（940）、20.8（944）、20.9（945）、20.11（947）
  - §22.1 首纵切 INTERNAL_DEMO + derived_page_images_only（968）；§22.2 纵切终点子包（979）；§22.3（991）；§22.4 顺序理由（997–1000）
- `openspec/id-prefix-registry.md`：`pkg_`（43）、`rel_`（44）、`ent_`（61）、使用规则（93）、社区 `anc_`（76）
- `pipeline/DATASET_ACCEPTANCE_STANDARD.md`：三级别（42）、fail-closed（46）、G3（67、70）、G7（95–99）
- `impl-00-interfaces/INTERFACES.md`：§4 artifact_type 临时闭集（317 起）、§1.2 StagePackage 信封、§2.8 M8 卡片、§5 批次与写入热点
- `openspec/legacy-storage-transition.md`：rag 索引「span key 碰撞和错链」（27）；页图不得伪造（65–67）
- `pipeline/rag/build_index.py:133-138`：`span_map[source_id][int(sNN)] = span_id`，丢了页号，这是碰撞根因
- fixture `pipeline/corpus/_fixture/mini_ed01/`：
  - `manifest.yaml:5-6`：`rights_status` 含「扫描件分发权 unconfirmed」、`release_policy: derived_page_images_only`
  - `spans.yaml`：43 条（page_001 4 条、page_003 39 条）
  - `README.md:16`：「不得作为知识来源、证据来源或发布输入引用」
- Ledger：
  - `pipeline/ledger/service.py`：`RUN_ARTIFACT_TYPES`（66）、`create_processing_run` 只接受 `edition_run`/`release_run`（319–345）、`begin_step_run` 由配置推导 stage（369–371）、`put_artifact(rights_scope=…)`（442–457）、`register_stage_package` 登记类型 `stage_package`（718–774，753）、`finish_step_run`（1132–1185）、`write_checkpoint`（1364–1398）
  - `pipeline/ledger/store.py`：`size_bytes`（42）、`transformation_inputs`（139–144）
  - `pipeline/ledger/fixture_ingest.py`：阶段输出类型（40–46）、`ocr_page`（193）；`pipeline/ledger/acceptance.py:77` `_frozen_inputs` 先例
- impl-02：`act/01.yaml:35-38`（corpus_spans 结构）、`act/03.yaml:17`（只读 SELECT 先例）、`act/03.yaml:49-58`（m3 包结构）、`act/05.yaml:26-29`（异常分层）、`README.md:40`（退出码纪律）；`ACCEPTANCE.md:5.3`（登记的下游约束：只接受 succeeded 上游包）
- `openspec/acceptance/run_all.sh`：20.4（212）、20.8（272）

**起草时实测的事实（2026-09-11，本机；2026-09-12 复核不变）**：

- `run_all.sh` → `SUMMARY pass=2 fail=1 blocked=8`。
- `ocr/data_work/sanche_pages/page_001..003.png` 存在；fixture 页 JSON 与清单尺寸都是 1203×1654。
- 43 条 span 的字框共 230 个，全部在页框内。
- 其中 2 条 span 的文本与其字框拼接不一致（「框」按 `source_anchor.chars` 全部条目计，含空字符框；5/16 是拼接后的**非空字符数**）：
  - `ss_sanche_ed01_p0001_s03`：文本 6 字 / 字框 8 个（其中空字符框 3 个）/ 拼接后非空字符 5
  - `ss_sanche_ed01_p0001_s04`：文本 17 字 / 字框 18 个（其中空字符框 2 个）/ 拼接后非空字符 16
- 按 `build_index.py` 的 `(source_id, sNN)` 规则给 fixture 的 43 条 span 取键，会塌缩为 **39 键、4 组碰撞**。宿主本身就能复现 §19 登记的缺陷类别。

## 3. 范围

写（ACT 逐个限定）：

- `pipeline/dataset_compiler/**`（新建，含 `shim/` 与 `tests/`）
- `openspec/acceptance/m8-span-identity.sh`（ACT 07 新建）
- `openspec/acceptance/run_all.sh`（**仅 ACT 08**，仅 20.4/20.8 两段与一个辅助函数，依 D6/P4）

禁止：

- 改规格正文、`openspec/schemas/**`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、其他 work-items
- 在同一波内由本包之外的 ACT 写 `openspec/acceptance/run_all.sh`：W3 内只有本包 ACT 08 可写（P4）
- 新增依赖；新增 ID 前缀（只用已登记的 `rel_`、`pkg_m8_`、`art_`、`rev_`、`prun_`、`srun_`，首切片不发 `ent_`）
- 调用任何模型 API（P6）
- 生产代码读 fixture 路径或工作目录文件（唯一例外是 D2 的薄 M1 页图登记 `shim/m1_shim_source_assets.py`，它的职能是 Source Intake）
- 合成或伪造与 fixture 哈希同值的页图
- 把任何 BLOCKED 写成 PASS
- 执行者写台账或 `ACCEPTED`

## 4. 主 Agent 决定（执行者不重议）

本节取代原 §4 的待裁决清单；全部 14 条均已由主 Agent 裁决，理由随条列出。未单列的细节默认采纳草稿推荐。

- **D1 上游缺席时的输入策略 → A 尾链首切片**。只冻结 M3 StagePackage 及其血缘输入与页图；EvidenceMapPack 前三段标 `not_compiled`，不注入合成知识；`fixture README.md:16` 的「发布输入引用」冲突按**附带口径**豁免：仅在临时 Ledger 内编译、评判包为 `INTERNAL_DEMO`、验收后删除、不落盘不分发（P1）。理由：不伪造知识，全部判定都有真实来源；M4/M6/M7 与知识链前三段在首纵切内以 BLOCKED 表达。
- **D2 页图登记的薄 M1 → A，文件与 CLI 名显式标 `m1_shim`**。文件 `pipeline/dataset_compiler/shim/m1_shim_source_assets.py`，CLI `python -m pipeline.dataset_compiler.shim.m1_shim_source_assets`，`SHIM_TOOL = "pipeline.dataset_compiler.shim.m1_shim"`；README 登记「impl-09 M1 落地后替换」。不改 impl-01 已验收的 `fixture_ingest.py`（P9）。理由：薄 M1 是本包唯一读文件的生产代码，职能属 M1 Source Intake，名字必须自证临时性。
- **D3 缺页图退出码 → A 退出 3**。`m8-span-identity.sh` 与 CLI 打印 `BLOCKED_SOURCE_ASSET_MISSING <path_ref…>` 并退出 3；禁止合成同哈希页图。理由：页图缺失时 `run_m8` 无法开始，没有「部分判定」可跑，与缺 fixture 同类。
- **D4 新 artifact_type → A 提名通过**。新增 `source_asset_page`、`source_asset_register`、`source_asset_pack`、`evidence_map_pack`、`release_manifest`、`publication_package`；复用 `configuration`、`validation_report`、`step_log`、`failure_report`、`stage_package`。**这些新名字已在 `impl-00-interfaces/INTERFACES.md` §4 临时闭集登记**（W2-C 登记 ACT）；实现前以 `python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py` 核对（末行 `I00-IF SUMMARY pass=18 fail=0` 且 exit 0），未登记的类型名实现不得使用。理由：artifact_type 唯一登记处是 INTERFACES §4，同一时刻只有一路写。
- **D5 子包 Schema → A 代码草案**。子包内容以代码内草案契约表达，`schema_version: "0.1.0-draft"`；准入层对 `PUBLIC_RELEASE` 以 `draft_schema` 拒绝；首纵切不向 `openspec/schemas/` 新增文件（L0 四份不动）（P3）。
- **D6 `run_all.sh` 20.4/20.8 → A 单独 ACT**（act/08）。两条改为执行 m8 判定：判定 FAIL → `FAIL`；否则 `BLOCKED 前置缺失: M4 Knowledge Extraction；<已判定段>`；**永不 PASS**；`SUMMARY` 保持 `pass=2 fail=1 blocked=8`。本包 act/08 是 W3 内唯一允许写 `run_all.sh` 的 ACT（P4）。
- **D7 §16 五项冻结输入的载体 → A**：发布范围、消费级别、`min_app_version`、`release_id` 写入 m8 配置修订；ReleasePolicy 与权利取 M1 清单修订的 `release_policy`/`rights_status`；TechniqueProfile 只有 `technique_profile_id="qizheng"` 字符串，ReleaseManifest 写 `technique_profile_version: null`；CanonicalKnowledgeSnapshot 由 M3 StagePackage 代替（D1）。
- **D8 M8 的 ProcessingRun 归属 → A**。每次 `run_m8` 新建 `release_run`（§6.2:153-169）。跨多 EditionPart 的 Release 需改 Ledger，首切片不涉及。
- **D9 `source_release` 定义 → A，但 `source_verified` 不算 release 级（主 Agent 加裁）**。`source_release = "release"` 当且仅当 `content_status` 全为 `expert_verified`；含 `deprecated` 拒绝；其余 `dev`。理由：`source_verified` 只表示原文与出处已核对（§8.2:341），不等于专家签发。
- **D10 INTERNAL_DEMO 隔离/水印/披露的数据形态 → A**。每条 entry `watermark`；ReleaseManifest `watermark{required,text}`；`isolation: internal_only`、`authoritative: false`、`completeness_claim: partial`；`known_defects` 用代码闭集；全部修订 `rights_scope="internal"`。水印文案**采用草案**：`INTERNAL_DEMO｜机器转录，未经人工校对｜不得作为知识来源或权威依据`。
- **D11 文本多于字框、坐标格式 → A**。该 2 条降级为 `highlight_level: line_bbox` 并登记 `glyph_text_mismatch` 披露；字框原样搬运 `{x,y,w,h}`，同源性以页 JSON 宽高 = 清单宽高 = PNG 头宽高判定。PUBLIC_RELEASE 准入层实现时追加该项拒绝。
- **D12 `min_app_version` → A**。可选 semver 参数：INTERNAL_DEMO 允许 `null`；PUBLIC_RELEASE 记 `min_app_version_unset` 并拒绝。
- **D13 重跑与多 Release → A**。首切片拒绝第二次 m8（「M8 已封存」），在 AnchorContractPack 批次再议。
- **D14 首切片子包集合 → A**。EvidenceMapPack + SourceAssetPack + ReleaseManifest + ValidationReport；QueryContractPack（D14-B）与 SearchIndexPack（D14-C）留到关闭 `mentions_mapping` 时与 M4 mentions 一起做，KnowledgeDataPack 随 M4–M7 落地。

## 5. 已固化默认（原起草默认，裁决后固化为「主 Agent 决定」，执行者不重议）

1. **消费级别闭集**：`INTERNAL_DEMO`/`DEV_SEARCH`/`PUBLIC_RELEASE`，其他值（含小写）在 begin 之前以 `SCH_002` 拒绝且无写入。合法但不满足准入的级别在 begin 之后以 `admission` 失败封存（§17:836）。准入判定先于任何子包编译，失败运行不留任何子包修订，也不以低级别自动重试。
2. **四个 task，每个 task 一个 m8 Checkpoint**（§17.1:843），顺序：`source_asset_pack` → `evidence_map_pack` → `release_manifest` → `validation_report`。
3. **身份键**：EvidenceMapPack 的 `entries` 以完整 `span_id` 为键，禁止 `(source_id, sNN)`。`span_id` 中的 `p<4位>`/`s<2位>` 必须等于 `page` 页号与 `line_index+1`（§19:882）。反向索引 `page_index` 覆盖清单全部页，排除页值为 `[]`。
4. **哈希无环**：ReleaseManifest 只含两个内容子包的哈希与输入对账；ValidationReport 校验 ReleaseManifest；PublicationPackage 与 StagePackage 汇总全部。`canonical_hash` = 按 pack_type 排序的 `[pack_type, sha256]` 列表的规范化 JSON 的 sha256。
5. **规范化 JSON**：`sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False`，UTF-8。`normalized_sha256` 递归去掉以 `artifact_revision_id` 结尾的键，用于比对两个独立 Ledger 的编译结果。
6. **Gate 独立**：`gate.py` 不 import `packs`/`canonical`/`levels`/`step`，从页 JSON 与清单重算。`acceptance.py` 不 import `packs`/`gate`，不读 `run_m8` 返回的 gate。
7. **异常分层**照搬 impl-02 `act/05.yaml:26-29`：begin 之前的解析、拒绝原样外抛；begin 之后分 `input_contract`/`admission`/`compile`/`publication_gate`/`internal` 五类失败封存。
8. **输入解析**：沿 M3 StagePackage 的 `manifest.input_artifacts` 反查 M1 清单与 M2 页修订，不再遍历 m1/m2 Checkpoint，信任链与血缘一致。`stage_package` 修订、`frozen_inputs`、`transformation_inputs` 经 `reader.store.conn` 只读 SELECT；**只接受所属 StepRun `succeeded` 的包**（P5）。
9. **测试宿主**：依赖真实页图的集成测试用 `skipUnless(assets_available())`，本机必须 0 skipped。合成 PNG 只能配合合成清单用于 shim 单元测试，不得与 fixture 哈希同值。
10. **派发分组**：
    - **K1 = ACT 00–02**：纯函数，可立即派发，只依赖 D1/D4/D5/D9/D10/D11 裁决。
    - **K2 = ACT 03–06**：Ledger。前置 impl-02 `ACCEPTED`，以及 D2/D3/D7/D8/D12/D13。
    - **K3 = ACT 07–08**：验收与 run_all。前置 D3/D6。

## 6. 上游输入契约（本包假设，供并行草案对账）

| 来源 | artifact_type | 本包读取的字段 | 依据 |
|---|---|---|---|
| M3 | `stage_package`（stage `m3`，sealed） | `stage_package_id`、`validation.passed == true`、`payload.spans_revision_id`、`payload.excluded_pages`、`payload.gate_profile`、`manifest.content_sha256`（== corpus_spans 字节哈希）、`manifest.input_artifacts`（含 `source_manifest`×1、`ocr_page_set`×1、`ocr_page`×N） | impl-02 `act/03.yaml:49-58`；`service.py:753` |
| M3 | `corpus_spans` | `source_id`、`edition_part_artifact_id`、`evidence_level`、`content_status`、`span_count`、`spans[].{span_id,page,line_index,start_offset,end_offset,text,source_anchor{page,image_sha256,line_id,bbox,chars[char_index,glyph_id,char,box]}}` | impl-02 `act/01.yaml:35-38` |
| M1 | `source_manifest` | `source_id`、`technique_id`、`rights_status`、`release_policy`、`edition_part{artifact_id,pages}`、`source_assets[].{page,sha256,width,height,path_ref}` | fixture `manifest.yaml` |
| M2 | `ocr_page` | `page`、`width`、`height`、`lines[].{id,box,text}`、`chars[].{id,parent,char,box}` | `fixture_ingest.py:193` |
| M2 | `ocr_page_set` | 只作存在性与血缘对账 | `fixture_ingest.py:45` |
| 薄 M1（本包 ACT 03） | `source_asset_page`（PNG 字节，`rights_scope=internal`） | m1 Checkpoint `task_id = source_asset_<page>` | D2 |

M8 找 M3 的规则：`list_checkpoints(ep,"m3")` → 恰一个 succeeded 的 StepRun → 该 StepRun 下恰一个 sealed 的 `stage_package` 修订；**只接受 `succeeded` 的包**（P5，`impl-02/ACCEPTANCE.md:5.3`）。`fixture_ingest` 灌入的 m3 包没有 `spans_revision_id`，必须拒绝。

首切片**不消费**：M4 CandidatePackage、M5 ValidationPackage、M6 ReviewedEditionPackage、M7 CanonicalKnowledgeSnapshot、TechniqueProfile 修订。

## 7. 对下游的输出契约

**artifact_type 闭集（D4/P2）**：本包只使用 §4 已批准的新名字（`source_asset_page`、`source_asset_register`、`source_asset_pack`、`evidence_map_pack`、`release_manifest`、`publication_package`）与复用名（`configuration`、`validation_report`、`step_log`、`failure_report`、`stage_package`）。这 6 个新名字已在 `impl-00-interfaces/INTERFACES.md` §4 闭集登记并与本包逐字一致；实现前以 `python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py` 核对（末行 `I00-IF SUMMARY pass=18 fail=0` 且 exit 0），未登记的类型名实现不得使用。

- **子包内容**（全部规范化 JSON；`schema_version: "0.1.0-draft"`）：
  - `source_asset_pack`：`pack_type`、`source_id`、`edition_part_artifact_id`、`content_level`、`rights_status`、`pages[].{page,asset_artifact_revision_id,sha256,size,width,height}`
  - `evidence_map_pack`：
    - 包级字段：`pack_type`、`source_id`、`edition_part_artifact_id`、`evidence_level`、`content_status`、`chain_segments`（= `["SourceSpan","SourceAnchor","OcrPage","SourceAsset"]`）、`knowledge_chain: "not_compiled"`、`span_count`、`page_index{页:[span_id]}`、`excluded_pages`
    - `entries{span_id: entry}`，每条 entry 含 `span_id,page,line_index,start_offset,end_offset,text,quote_sha256,content_status,watermark,line_id,bbox,glyphs[],glyph_text_equal,highlight_level,frame{width,height},image_sha256,ocr_page_artifact_revision_id,source_asset_artifact_revision_id`
  - `release_manifest`：`manifest_type`、`release_id`（`rel_`）、`consumption_level`、`source_release`、`release_scope{edition_part_ids}`、`technique_id`、`technique_profile_version: null`、`schema_versions`、`packs[].{pack_type,artifact_revision_id,sha256,size}`、`canonical_hash`、`input_reconciliation[].{artifact_revision_id,artifact_type,sha256}`、`min_app_version`、`watermark{required,text}`、`isolation`、`completeness_claim`、`authoritative`、`known_defects[].{code,detail}`、`retired_anchors: []`
  - `validation_report`（M8）：`gate_profile: "m8_first_slice"`、`consumption_level`、`admission`、`passed`、`checks{名:{ok,detail}}`、`failed_checks`、`knowledge_chain: "not_evaluated"`、`anchor_migration: "not_evaluated"`
  - `publication_package`：`release_id`、`consumption_level`、`release_manifest_revision_id`、`validation_report_revision_id`、`packs{evidence_map_pack,source_asset_pack}`、`canonical_hash`
- **m8 StagePackage**（`pkg_m8_<32hex>`，过 `stage_package.schema.json`）：
  - `payload{release_id,consumption_level,release_manifest_revision_id,publication_package_revision_id,canonical_hash,knowledge_chain}`
  - `manifest.counts{spans,pages,source_assets,glyph_highlights,line_bbox_highlights,packs}`；fixture 上为 `{43,3,3,41,2,2}`
  - `manifest.content_sha256` = release_manifest 字节哈希
  - `lineage.upstream_artifacts` 含 `artifact_kind: stage_package` 的 m3 包引用与 M1 清单引用
- **CLI**：
  - `python -m pipeline.dataset_compiler --root <ledger_root> --edition-part <art_id> --level <LEVEL> [--min-app-version X.Y.Z]`：`M8 OK|FAILED|REFUSED`，退出 0/1/2/3
  - `python -m pipeline.dataset_compiler.shim.m1_shim_source_assets --root … --edition-part … --asset-root …`：`ASSETS OK|FAILED|REFUSED` 或 `BLOCKED_SOURCE_ASSET_MISSING`，退出 0/1/2/3
- **APP mock / 注解社区消费提示**：
  - 按 `span_id` 取 entry，`highlight_level` 决定逐字框还是整行框，`frame` 与页图像素同源，页图按 `source_asset_artifact_revision_id` 从 Object Store 解析。
  - 首切片不产出 AnchorContractPack，社区 `anc_` 锚点（`id-prefix-registry.md:76`）暂不能绑定 Release 的迁移契约。

## 8. 与其他模块、并行草案的接口假设

1. **impl-02（M3）**：J3 返工（`act/05.yaml`）后 `run_m3` 的输出契约与 §6 表一致且不再变动。本包 K2 以 impl-02 `ACCEPTED` 为前置，`test_step` 使用 `ingest(stages=("m1","m2")) → run_m3`。**只接受所属 StepRun `succeeded` 的 m3 包**（P5）。
2. **impl-03（M5，并行定稿）**：
   - 首切片 M8 不消费 ValidationPackage；G3 的 span/锚点检查在本包 Gate 中独立重做，允许与 M5 重复。
   - M5 落地后，M8 冻结输入追加 m5 StagePackage，准入追加「m5 passed」。
   - G6 复验、G7 其余部分（专家签发核验等）归 M8 后续批次（§13.1:603-604）。
   - 假设 M5 不产出 EvidenceMapPack 同构结构。
3. **M4/M6/M7（未来）**：
   - 假设 CanonicalKnowledgeSnapshot 以独立 artifact_type 封存，内含 `as_` Assertion。
   - EvidenceLink 同时记录目标 `entity_id` 与所见 `artifact_revision_id`（§8.1:265）；KnowledgeEntry 用 `ent_` 由 M8 发号（§4:94、registry:61）。
   - 届时 EvidenceMapPack 在现有 `entries` 前补三段，`knowledge_chain` 改为 `compiled`，现有键不变。
4. **Ledger（impl-01）**：
   - 无按 StepRun 读 StagePackage 的公开方法，本包只读 SELECT。
   - 修订大小列名为 `size_bytes`；`put_run_artifact` 只接受两种类型；ProcessingRun 只绑一个 EditionPart。
   - 本包不改 Ledger。
5. **Local Orchestrator 缺席**：由脚本顺序驱动 `ingest → run_m3 → register_source_assets → run_m8`（§22.4:1000）。
6. **并行编码 Agent**：本包只写 §3 所列路径，与 impl-02 J3 的写集（`pipeline/corpus_compiler/**`）不相交；ACT 08 与任何改 `run_all.sh` 的批次互斥，派发前需确认无并发改动（P4）。
7. **上游数据问题（需登记给 M2/M3 负责人）**：fixture 有 2 条 span 文本比 OCR 字框多 1 字（§2 实测）。impl-02 结构 Gate 没有校验「字框拼接 == 文本」，这是字框级证据的真实缺口。本包只做披露与降级（D11），不修上游。

## 9. `run_all.sh` 影响分析

| 条目 | 现状 | 本包后 | 理由 |
|---|---|---|---|
| 20.4 | BLOCKED（M8） | **BLOCKED**（M4 Knowledge Extraction；改写说明，m8 判定 FAIL 时变 FAIL；ACT 08） | 发布物↔原始页双向可判，但候选/驳回项/正式知识不存在（§20:940） |
| 20.8 | BLOCKED（M8） | **BLOCKED**（同上；ACT 08） | SourceAssetPack 及其关系可判，引用可由 Object Store 解析；但缺「结构化知识」（§20:944） |
| 20.6 | BLOCKED（M8） | 不变 | KnowledgeEntry 未编译 |
| 20.9 | BLOCKED（M8） | 不变 | GraphProjectionPack 不在首切片 |
| 20.11 | BLOCKED（M8） | 不变 | 单 Release，无 IdentityMigrationMap（D13） |
| 20.1/20.5/20.10 | BLOCKED | 不变 | 与 M8 无关 |

`SUMMARY` 保持 `pass=2 fail=1 blocked=8`。§19.0 `m8-span-identity.sh` 由 127 变为 2；变为 0 需要 M4 mentions 与 SearchIndexPack（D14-C），或者 D1-B。

## 10. 目录规划（落地后）

```text
pipeline/dataset_compiler/
  __init__.py          M8_TOOL / M8_TOOL_VERSION / CONSUMPTION_LEVELS / SUPPORTED_LEVELS / SUB_PACK_SCHEMA_VERSION
  errors.py            DatasetRefused
  canonical.py         canonical_bytes / sha256_hex / quote_sha256 / strip_revision_ids / normalized_sha256
  levels.py            derive_source_release / evaluate_admission（纯函数）
  packs.py             png_size / build_source_asset_pack / build_evidence_map_pack / compute_known_defects / build_release_manifest（纯函数）
  gate.py              evaluate_publication（纯函数，不依赖 packs/canonical/levels）
  shim/__init__.py     SHIM_TOOL / SHIM_TOOL_VERSION
  shim/m1_shim_source_assets.py  register_source_assets + CLI（薄 M1，D2；impl-09 M1 落地后替换）
  inputs.py            resolve_m8_inputs（Ledger 只读）
  step.py              run_m8（§17 事务序列）
  __main__.py          python -m pipeline.dataset_compiler
  acceptance.py        span_identity 与 publication 两组判定
  tests/               _ledger_helpers.py test_canonical.py test_levels.py test_packs.py test_gate.py test_shim.py
                       test_inputs.py test_step.py test_step_failures.py test_cli.py test_acceptance.py
openspec/acceptance/m8-span-identity.sh
openspec/acceptance/run_all.sh（ACT 08 只改 20.4/20.8）
```

## 11. §W8 返工设计（草案，待主 Agent 裁决）

依据 `G7-RULINGS.md` 第 100 条 D1/D2/D8 与第 106 条 D5，本节起草 W8 阶段 M8 数据集编译模块（`pipeline/dataset_compiler`）从「OCR 尾链首切片」向「真书电子文本（《乾元秘旨》）全链发布」演进的返工设计草案。
本节仅做架构设计与契约分析，不编写实现代码，不越权裁决未决点。

### 11.1 输入改读 M7 Snapshot

- **现状（文件:行号）**：
  1. `pipeline/dataset_compiler/inputs.py:52-95`（`_resolve_m3`）：M8 目前仅通过 `list_checkpoints(edition_part_id, "m3")` 读取 M3 的 StagePackage，并强依赖 `payload.spans_revision_id`；
  2. `pipeline/dataset_compiler/inputs.py:97-138`（`_resolve_pages`）：强制从 M3 包的 `manifest.input_artifacts` 反查 `ocr_page_set`（恰 1 个）与 `ocr_page`（至少 1 个），页名严格校验为 `page_\d{3,4}`；
  3. `pipeline/dataset_compiler/inputs.py:141-164`（`_resolve_assets`）：强制从 m1 Checkpoint 的 `source_asset_` 任务收集 `source_asset_page` 修订；
  4. `pipeline/dataset_compiler/inputs.py:167-215`（`resolve_m8_inputs`）：整体验收输入完全绑定 OCR 扫描路线与 M3 首切片，未消费任何 M4/M6/M7 知识产物；
  5. `pipeline/assembly/genesis.py:275-285`：M7 创世汇编产出的 Snapshot `knowledge.editions[]` 仅有 `{source_id, work_key, reviewed_edition_package_revision_id, reviewed_edition_revision_id, stage_package_id, edition_part_artifact_ids, edition_complete}`，缺失 `evidence_level` 与 `corpus_spans_revision_id`。
- **设计**：
  1. **冻结输入清单**：依据规格 §16:661-666，M8 冻结输入第一项改读 CanonicalKnowledgeSnapshot Revision（`canonical_snapshot`）。完整冻结清单包括：
     - `canonical_snapshot` Revision；
     - 发布范围（`release_scope`，即 `edition_part_ids` 清单）；
     - `technique_profile`（如 `qizheng` 技法配置）；
     - `release_policy`（`reference_and_hash_only` 或 `derived_page_images_only`）；
     - 目标消费级别（`consumption_level`: `INTERNAL_DEMO` / `DEV_SEARCH` / `PUBLIC_RELEASE`）；
     - 血缘支持：M7 `assembly_package` 及沿 lineage 反查的 M6 `reviewed_edition_package`、M3 `corpus_package`、M2 清洗产物（`raw_text`、`cleaned_text_revision`、`deterministic_patch_set`、`sanitization_report`）与 M1 `source_manifest`。
  2. **契约统一在上游与分派机制**：依据第 100 条 D2，`resolve_m8_inputs` 保持为统一入口函数，不另为电子文本写独立入口分支。读取流程：
     - 首先加载 `canonical_snapshot`，从 `snapshot.knowledge.editions[0]`（或 M3 `corpus_spans`）读取 `evidence_level`；
     - 若 `evidence_level == "glyphbox_level"`：分派至 OCR 扫描线逻辑，解析 `ocr_page_set`、`ocr_page` 与 `source_asset_page`；
     - 若 `evidence_level == "offset_level"`：分派至电子文本线逻辑，解析 M2 产物（`raw_text`、`cleaned_text_revision`、`deterministic_patch_set`、`sanitization_report`）与 M1 `source_manifest` 中的 SourceAsset 元数据。
  3. **Snapshot 补字段**：依第 106 条 D4，M7 Snapshot 的 `knowledge.editions[]` 补充 `evidence_level` 与 `corpus_spans_revision_id`。M8 输入解析层可直接通过 Snapshot 定位底层语料切片，无需跨层越权猜测。
- **依据**：
  - 规格 `openspec/learn-system-blackbox-architecture.md` §16:661-666（M8 冻结五项输入）；
  - `docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md` §2.8（M8 卡片，:195-200）；
  - `docs/blackbox-spec-rework/G7-RULINGS.md` 第 100 条 D2（契约统一在上游，下游按证据级别分派，不另写一套入口）、第 100 条 D8（改读 M7 Snapshot）、第 106 条 D4（Snapshot `editions[]` 补 `evidence_level` 与 `corpus_spans_revision_id`）。
- **未决点**：
  - 未决点 Q-M8-04：M8 输入中 Snapshot 粒度是以 Technique 为单位聚合的多 EditionPart 单 Snapshot，还是单 EditionPart 对应独立 Snapshot？

### 11.2 知识链前三段 KnowledgeEntry → Assertion → EvidenceLink

- **现状（文件:行号）**：
  1. `pipeline/dataset_compiler/packs.py:32`：`CHAIN_SEGMENTS = ["SourceSpan", "SourceAnchor", "OcrPage", "SourceAsset"]`，尾链仅定义了后四段；
  2. `pipeline/dataset_compiler/packs.py:261-262`：`evidence_map_pack` 固定写入 `"chain_segments": CHAIN_SEGMENTS, "knowledge_chain": "not_compiled"`；
  3. `pipeline/dataset_compiler/gate.py:30-31` 与 `:393-405`：Gate 检查项 `knowledge_chain` 恒为 `{"ok": None, "status": "not_evaluated"}`；
  4. `pipeline/assembly/genesis.py:317-367`：M7 创世汇编产出的 Snapshot 虽已有 `patterns[]` 与 `assertions[]`（:391-430），但 M8 从未读取和组装它们；
  5. `pipeline/assembly/genesis.py:401-418`：M7 对证据偏移在局部与绝对值间存在混用（已由第 106 条 D1 裁决要求修复为 I-11 绝对偏移）。
- **设计**：
  1. **编译规则与产物字段**：
     - 输出子包由原先的 2 个扩充为包含 `KnowledgeDataPack`（`knowledge_data_pack.json`）与完整无损 `EvidenceMapPack`（`evidence_map_pack.json`）。
     - `KnowledgeDataPack` 编译规则：从 Snapshot 的 `knowledge` 提取对象，组装：
       - `entries[]`：`{entry_id, subject_entity_id, title, assertion_ids, school_view_ids, content_status, mark_binding}`；
       - `assertions[]`：`{assertion_id, proposition, subject_entity_id, status}`；
       - `school_views[]` 与 `conflict_groups[]`。
     - `EvidenceMapPack` 编译规则：七段链完整闭合（KnowledgeEntry → Assertion → EvidenceLink → SourceSpan → SourceAnchor → offset尾段/OcrPage → SourceAsset）。
     - `EvidenceLink` 字段严格依 INTERFACES:235【I-11】：`{source_span_id, support_type, start_offset, end_offset, quote, quote_sha256}`，其中 `start_offset/end_offset` 为绝对偏移（与 M3 `corpus_spans` 同一坐标系）。
  2. **与 M6 审核后内容状态的关系及 INTERNAL_DEMO 水印披露（§16.1）**：
     - 状态继承：M8 继承 Snapshot 中由 M6 审定或机器抽取的 `content_status`（如 `machine_extracted` / `source_verified` / `cross_model_reviewed` / `expert_verified`），不提级、不合成；
     - 消费级别准入：
       - `INTERNAL_DEMO`：允许 `machine_*` 状态进入，但必须隔离（`isolation: "internal_only"`）、打水印（Entry 与 EvidenceMap entry 标记 `watermark: true`）、`ReleaseManifest` 中启用水印（`watermark{required: true, text: ...}`），并在 `known_defects` 中披露 `machine_content` 等，禁止声称权威（`authoritative: false`）或完备；
       - `DEV_SEARCH`：要求可判定内容至少为 `cross_model_reviewed`；
       - `PUBLIC_RELEASE`：所有断言必须为 `expert_verified`，机器记录不得泄露。
  3. **Gate 判定机制（闭环与不得绕过 Assertion）**：
     - 检查项 1（`chain_closure`）：遍历 `KnowledgeDataPack.entries`，断言每个 entry 拥有至少 1 个 `assertion_id`，且该 ID 存在于 `KnowledgeDataPack.assertions` 中；
     - 检查项 2（`assertion_evidence_closure`）：遍历 `KnowledgeDataPack.assertions`，断言每个 assertion 拥有至少 1 条 EvidenceLink，且其引用的 `source_span_id` 在底料语料中存在；
     - 检查项 3（`no_assertion_bypass`）：验证所有 EvidenceLink 必须从属于明确的 Assertion。严禁存在由 KnowledgeEntry 直接链接到 SourceSpan 的 EvidenceLink；
     - 检查项 4（`entry_assertion_reachability`）：断言无孤儿断言（每个 Assertion 至少被一个 KnowledgeEntry 引用），任一悬空或断裂立即导致 Gate fail-closed 阻断签发。
- **依据**：
  - 规格 §16:703-715（七段固定顺序证据链、每个 KnowledgeEntry 至少追溯到一个 Assertion、EvidenceLink 不得绕过 Assertion、一票否决）；§16.1:670-678（消费级别准入门槛与披露）；
  - `INTERFACES.md` §3.9（`knowledge_data_pack.schema.json`，:296-299）、§3.10（`evidence_map_pack.schema.json`，:300-303）、【I-11】（:416）；
  - `G7-RULINGS.md` 第 100 条 D1、D8、第 106 条 D1。
- **未决点**：
  - 未决点 Q-M8-01：KnowledgeEntry 的主体选取规则（Pattern 为主 / Concept 为主 / 双轨制）。
  - 未决点 Q-M8-03：在 `reference_and_hash_only` 发布策略下，EvidenceMapPack 与 EvidenceLink 是否允许包含原文 `quote` 字符切片，还是只保留 `quote_sha256` 与偏移？

### 11.3 KnowledgeEntry 主体与 `ent_` 发号（提案）

- **现状（文件:行号）**：
  1. `openspec/learn-system-blackbox-architecture.md:318`：冻结 `ent_<32hex>` 格式，UUIDv4 家族，语义为 `entry_id`，跨 Release 保号，退役写入 `IdentityMigrationMap`；
  2. `docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md:203`：明确保留未定义项——「KnowledgeEntry 主体选 Concept 还是 Pattern 的规则（86 只说『一个 Concept 或 Pattern』）」；
  3. `docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md:298`：`knowledge_data_pack.schema.json` 草案中定义 `entries[].subject_entity_id: conceptId|patternId`；
  4. `pipeline/assembly/genesis.py:317-367`：M7 当前创世 Snapshot 包含 `patterns[]`（但 `concept_id` 为 `None`，rules 为空）与 `concepts[]`（仅名称别名），未合成统一发布词条。
- **设计（候选方案与权衡）**：
  - **候选 1：以 Pattern（格局）为主体，Concept 为辅助**
    - *机制*：每个经审核的 Pattern 编译为一个 `KnowledgeEntry`（`subject_entity_id = pat_...`），条目标题取 Pattern 名称，汇聚其名下的 `assertion_ids` 与 `school_view_ids`；
    - *对规格与本书数据后果*：《乾元秘旨》「天官」「七煞」两节核心内容皆为星曜格局推步断语（如「天官会紫气」「七煞逢吉化权」），以 Pattern 为主体能精确映射术数推步的核心断语；但对于纯概念名词（如星曜本质属性说明）在无格局时无法独立成词条。
  - **候选 2：以 Concept（概念）为主体，Pattern 挂载于 Concept 之下**
    - *机制*：以星曜概念（如「天官」「七煞」）为主体（`subject_entity_id = c_...` 或 `tc_...`），Pattern 作为子模式；
    - *对规格与本书数据后果*：词条结构类似传统百科，但古籍中大量断言涉及多星交会（例如天官与紫气合论），强行归属单一 Concept 会破坏对等性；且 M7 当前 `patterns[].concept_id` 为 `None`，缺乏显式归属。
  - **候选 3：双轨制（PatternEntry 与 ConceptEntry 并列，由 `subject_entity_id` 区分）（推荐）**
    - *机制*：`subject_entity_id` 既可指向 `pattern_id` 也可指向 `concept_id`（完全符合 INTERFACES:298 契约）。凡 M7 Snapshot 中拥有断言的 Pattern 生成格局词条；凡拥有定义性释义或概念引用的 Concept 生成概念词条。
    - *推荐理由*：兼顾术数文献「名词概念检索」与「格局断语推步」两种场景；且与 M7 创世现状无缝契合，无需强求 M7 在汇编期完成 Pattern 到 Concept 的排他绑定。
  - **`ent_` 发号规则与确定性保障**：
    - *格式*：严格依 §8.1:318 为 `ent_<32hex>`（32位小写十六进制）；
    - *确定性生成*：为满足编译纯函数与多次运行字节确定一致的要求（`packs.py:3`），禁止在生产运行时调用随机 `uuid4()`。提案采用基于命名空间的确定性派生：`ent_id = "ent_" + hashlib.md5(f"{technique_id}:{subject_entity_id}".encode("utf-8")).hexdigest()` 或 UUIDv5；
    - *跨 Release 身份延续与 IdentityMigrationMap（§16:727-734）*：
      - 单一技法在不同 Release 重新编译时，相同 `subject_entity_id` 始终派生出相同的 `ent_` 标识，保证客户端外挂注解（`anc_`）不因重新编译而漂移；
      - 若后续 Release 发生 Pattern 合并（merged）、拆分（split）或废弃（retired），在 `AnchorContractPack.identity_migration_map` 中记录身份演变。首个 Release（创世）无前序 Release，`identity_migration_map.entries` 为空列表。
- **依据**：
  - 规格 §4:86-94（KnowledgeEntry 定义）、§8.1:318（`ent_` 格式与身份）、§16:727-734（AnchorContractPack 与 IdentityMigrationMap）；
  - `INTERFACES.md` §2.8（:203）、§3.9（:298）、§3.12（:310）；
  - `G7-RULINGS.md` 第 106 条 D5。
- **未决点**：
  - 未决点 Q-M8-01：主 Agent 裁决采纳候选 1、候选 2 还是候选 3。
  - 未决点 Q-M8-02：`ent_` 确定性发号算法采用 UUIDv5 还是确定性哈希派生。

### 11.4 `reference_and_hash_only` 发布包内容

- **现状（文件:行号）**：
  1. `pipeline/dataset_compiler/packs.py:77-82`：代码硬编码校验 `if manifest["release_policy"] != "derived_page_images_only": raise DatasetRefused("发布策略未实现，需 derived_page_images_only")`；
  2. `pipeline/dataset_compiler/levels.py:100-101`：准入校验 `if release_policy != "derived_page_images_only": unmet.add("release_policy_not_implemented")`；
  3. `pipeline/dataset_compiler/packs.py:98-116`：SourceAssetPack 硬编码包含每一页的尺寸与页图对象修订 `asset_artifact_revision_id`；
  4. `pipeline/dataset_compiler/packs.py:232`：EvidenceMapPack entry 中直接内嵌 `text: span["text"]`。
- **设计**：
  1. **SourceAssetPack 发布包内容**：
     - 严格遵循 `INTERFACES.md` §3.11（:304-307）：
       - `pack_type`: `"source_asset_pack"`
       - `policy`: `"reference_and_hash_only"`
       - `assets[]`: 每一项仅包含 `{source_id, page, sha256, width: null, height: null, ref: {object_store: "local", path_ref: ...}, rights_note: ..., bytes_included: false}`；
     - **明确不包含任何扫描图像二进制，也不包含任何古籍原文正文字节**。
  2. **EvidenceMapPack 发布包内容**：
     - 承载完整的引用与偏移证据链，但**明确剥离古籍原文文本**：
       - 保留字段：`entry_id`, `assertion_id`, `evidence_link`（含 `source_span_id`, `start_offset`, `end_offset`, `quote_sha256`, `support_type`）；
       - 尾部锚点字段：清洗文本偏移、patch 映射关系、原始文本偏移区间及底本 SourceAsset `sha256`；
       - **不含正文**：`text` 字段置为 `null` 或不输出；`quote` 不输出字面量，仅保留 `quote_sha256`；
       - 客户端使用方式：客户端在获得合法底本时，在本地通过 `path_ref` + `sha256` 匹配底本，结合偏移与 patch 换算完成高亮展示，发布包自身杜绝版权文本泄漏。
  3. **与 `derived_page_images_only` 分支并存设计**：
     - `levels.py:100` 放行 `reference_and_hash_only`，不再判 `release_policy_not_implemented`；
     - `packs.py` 的 `build_source_asset_pack` 根据 `manifest["release_policy"]` 分派：
       - `derived_page_images_only`：要求 `bytes_included: true`，校验 Object Store 图像修订与宽高；
       - `reference_and_hash_only`：强制 `bytes_included: false`，宽高为 `None`，只校验底本元数据与 `sha256`。
- **依据**：
  - 规格 §16:717-723（三种权利级别定义，721 明确 `reference_and_hash_only` 只携带引用、SHA-256、页标识和权利说明）；
  - `INTERFACES.md` §3.11（:304-307）；
  - `G7-RULINGS.md` 第 76 条 D1、第 100 条 D8、第 101 条。
- **未决点**：
  - 未决点 Q-M8-03：EvidenceMapPack 在 `reference_and_hash_only` 策略下，`quote` 与 `text` 字段是直接移除、置为 `null` 还是有其他表示方式？

### 11.5 offset 证据链尾段

- **现状（文件:行号）**：
  1. `pipeline/dataset_compiler/packs.py:32`：当前尾段写死为 `["SourceSpan", "SourceAnchor", "OcrPage", "SourceAsset"]`；
  2. `pipeline/dataset_compiler/packs.py:177-183`：通过 `parse_span_identity` 强制解析页号与行号（`_p\d{4}_s\d{2}`）；
  3. `pipeline/dataset_compiler/packs.py:195-245`：强制读取 `anchor["bbox"]`、`anchor["chars"]`，与 `ocr_page`、`source_asset` 进行坐标比对；
  4. `pipeline/dataset_compiler/gate.py:145-207`：`check_glyph_anchor_closure`、`check_ocr_page_binding`、`check_coordinate_frame` 均为 OCR 字框专属检查。
- **设计**：
  1. **证据链尾段定义转换（第 81 条）**：
     - OCR 路线尾段：`SourceSpan` → `SourceAnchor` → `OcrPage`（字框坐标） → `SourceAsset`（页图像）；
     - 电子文本路线尾段：`SourceSpan`（`ss_<work>_ed<NN>_o<NNNNNNN>`） → 清洗文本偏移（`start_offset, end_offset`） → `DeterministicPatchSet` 映射 → 原始文本偏移（`raw_start, raw_end`） → `RawText` 修订 → `SourceAsset`（底本 SHA-256）。
  2. **对应位置与字段映射**：
     - `SourceSpan`：承载清洗文本中的切片标识，ID 锚定原始偏移（第 78 条）；
     - `SourceAnchor`（第 78 条七键）：承载 `{raw_text_revision_id, raw_start, raw_end, cleaned_text_revision_id, start_offset, end_offset, quote_sha256}`，取代 OCR 的 `line_id/bbox/chars`；
     - 替代 `OcrPage` 的环节：`DeterministicPatchSet` 与 `SanitizationReport`。证明清洗文本与原始底本文字的双向可逆换算关系，以及生僻字/保留字符的对账依据；
     - 替代页图 `SourceAsset` 的环节：`RawText` 对应的 SourceAsset 文件 `file_sha256`。
  3. **包内表达**：
     - 在 `EvidenceMapPack` 中，当 `evidence_level == "offset_level"` 时，`chain_segments` 声明为：`["KnowledgeEntry", "Assertion", "EvidenceLink", "SourceSpan", "SourceAnchor", "DeterministicPatchSet", "RawText", "SourceAsset"]`。
- **依据**：
  - 规格 §11.1:527-528（`offset_level` 证据级别定义）；
  - `G7-RULINGS.md` 第 78 条 D3（字符偏移定位与锚点七键）、第 81 条（电子文本可追踪证据链模型）、第 102 条 Q4、第 103 条 D1。
- **未决点**：
  - 未决点 Q-M8-07：`chain_segments` 是否保持统一抽象名（如用 `SourceAnchor` 统一代表定位层），还是显式区分为两组枚举？

### 11.6 GraphProjectionPack 格式草案（§16:725）

- **现状（文件:行号）**：
  1. `openspec/learn-system-blackbox-architecture.md:725`：要求「GraphProjectionPack 与移动端数据必须来自同一 CanonicalKnowledgeSnapshot，并共享 release_id、canonical_hash、实体 ID 和关系 ID」；
  2. `docs/blackbox-spec-rework/work-items/impl-00-interfaces/INTERFACES.md:203` 与 `:322`：明确将 GraphProjectionPack 格式列为「首切片外未定义」与「不在本包范围」；
  3. `pipeline/dataset_compiler/step.py:362-375`：M8 发布包生成清单中未包含 GraphProjectionPack；
  4. `openspec/acceptance/run_all.sh:333`：20.9 判定为硬编码的 `BLOCKED`。
- **设计（格式草案）**：
  1. **元数据绑定**：
     - `pack_type`: `"graph_projection_pack"`；
     - `schema_version`: `"0.1.0-draft"`；
     - `release_id`: 与 PublicationPackage 及 ReleaseManifest 严格一致；
     - `canonical_hash`: 严格等于 CanonicalKnowledgeSnapshot 的 `meta.canonical_hash`；
     - `consumption_level`: 显式标注目标级别。
  2. **节点格式（`nodes[]`）**：
     - `node_id`: 实体 ID（`pat_...`, `c_...`, `as_...`, `sv_...`，与 KnowledgeDataPack 严格一致）；
     - `kind`: `pattern` | `concept` | `assertion` | `school_view`；
     - `label`: 中文展示名称；
     - `content_status`: 状态枚举；
     - `watermark`: bool（`INTERNAL_DEMO` 下 machine 条目为 true）；
     - `properties`: 扩展属性字典。
  3. **边格式（`edges[]`）**：
     - `edge_id`: 确定性标识；
     - `source`: 源实体 ID；
     - `target`: 目标实体 ID；
     - `relation`: 语义关系，闭集为：
       - `has_assertion`（Pattern → Assertion）；
       - `belongs_to_concept`（Assertion/Pattern → Concept）；
       - `in_conflict_group`（SchoolView → ConflictGroup）；
       - `qualifies` / `opposes` / `supports`（Assertion 间关系）；
     - `content_status` 与 `watermark`。
  4. **确定性排序与哈希**：
     - `nodes` 严格按 `node_id` 字典序升序；
     - `edges` 严格按 `(source, relation, target)` 字典序升序；
     - 规范化 JSON 序列化后计算 SHA-256，登记入 `ReleaseManifest.packs`。
  5. **示意片段（以《乾元秘旨》「天官」「七煞」为例，示意，非金标）**：
     ```json
     {
       "schema_version": "0.1.0-draft",
       "pack_type": "graph_projection_pack",
       "release_id": "rel_018f9e74e27670008000000000000001",
       "canonical_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
       "consumption_level": "INTERNAL_DEMO",
       "nodes": [
         {
           "node_id": "as_qizheng_000101",
           "kind": "assertion",
           "label": "天官客曜遇吉神福禄尤甚",
           "content_status": "machine_extracted",
           "watermark": true,
           "properties": {"layer": "general"}
         },
         {
           "node_id": "as_qizheng_000102",
           "kind": "assertion",
           "label": "七煞照命主兵权杀伐",
           "content_status": "machine_extracted",
           "watermark": true,
           "properties": {"layer": "general"}
         },
         {
           "node_id": "c_qizheng_qisha",
           "kind": "concept",
           "label": "七煞",
           "content_status": "machine_extracted",
           "watermark": true,
           "properties": {"imagery": "凶杀"}
         },
         {
           "node_id": "c_qizheng_tianguan",
           "kind": "concept",
           "label": "天官",
           "content_status": "machine_extracted",
           "watermark": true,
           "properties": {"imagery": "客曜"}
         },
         {
           "node_id": "pat_qizheng_000001",
           "kind": "pattern",
           "label": "天官朝元格",
           "content_status": "machine_extracted",
           "watermark": true,
           "properties": {"recognition_rule_status": "not_captured"}
         }
       ],
       "edges": [
         {
           "edge_id": "e_018f9e74e27670008000000000000001",
           "source": "as_qizheng_000101",
           "target": "c_qizheng_tianguan",
           "relation": "belongs_to_concept",
           "content_status": "machine_extracted",
           "watermark": true
         },
         {
           "edge_id": "e_018f9e74e27670008000000000000002",
           "source": "as_qizheng_000102",
           "target": "c_qizheng_qisha",
           "relation": "belongs_to_concept",
           "content_status": "machine_extracted",
           "watermark": true
         },
         {
           "edge_id": "e_018f9e74e27670008000000000000003",
           "source": "pat_qizheng_000001",
           "target": "as_qizheng_000101",
           "relation": "has_assertion",
           "content_status": "machine_extracted",
           "watermark": true
         }
       ],
       "node_count": 5,
       "edge_count": 3
     }
     ```
- **依据**：
  - 规格 §16:689、§16:725（GraphProjectionPack 契约约束）；
  - `INTERFACES.md` §2.8（:198）、§4（:357）；
  - `G7-RULINGS.md` 第 100 条 D1、D8、第 106 条 D5。
- **未决点**：
  - 未决点 Q-M8-05：`edge_id` 生成机制（UUIDv5 派生 vs 确定性三元组拼接）。

### 11.7 M8 Gate 变化

- **现状（文件:行号）**：
  1. `pipeline/dataset_compiler/gate.py:16-31`：固化 14 个检查项常量 `_CHECK_NAMES`；
  2. `pipeline/dataset_compiler/gate.py:110-120`（`check_span_page_binding`）：使用 `_SPAN_TAIL_RE` 强核对 span_id 的页号和行号；
  3. `pipeline/dataset_compiler/gate.py:145-207`：包含 `check_glyph_anchor_closure`、`check_ocr_page_binding`、`check_source_asset_binding`、`check_coordinate_frame`，均针对 OCR 字框与页图像素尺寸；
  4. `pipeline/dataset_compiler/gate.py:393-405`（`check_knowledge_chain`）：恒为 `not_evaluated`；
  5. `pipeline/dataset_compiler/gate.py:434`：`knowledge_chain` 直接硬编码返回 `"not_evaluated"`。
- **设计**：
  1. **`knowledge_chain` 实评检查项清单**：
     - `chain_closure`: 校验每个 KnowledgeEntry 至少链接 1 个 Assertion，每个 Assertion 至少拥有 1 个 EvidenceLink，引用闭合且无断裂；
     - `no_assertion_bypass`: 校验 EvidenceLink 不得绕过 Assertion 直接关联 KnowledgeEntry；
     - `quote_hash_integrity`: 校验每个 EvidenceLink 的 `quote_sha256` 准确反映引文字符串；
     - `content_status_admission`: 校验知识链各节点的成熟度状态是否符合消费级别准入。
  2. **offset 档替代页绑定与字框检查的项**：
     - 检查项依据 `evidence_level` 进行分派（或细分子检查）：
       - 当 `evidence_level == "glyphbox_level"`：保持现有 4 项 OCR 检查；
       - 当 `evidence_level == "offset_level"`：
         1. `offset_anchor_continuity`: 校验 Span 的 `start_offset/end_offset` 在清洗文本范围内，无非法重叠；
         2. `patch_reversible`: 校验 `DeterministicPatchSet` 能够准确在原始偏移与清洗偏移间双向映射；
         3. `raw_text_binding`: 校验原始偏移对应的文本切片与原始 `RawText` 逐字相符，且 `RawText` 的 SHA-256 与 SourceAsset 清单一致；
         4. `sanitization_disclosure`: 依第 103 条 D1，检查禁止字符是否已与 `sanitization_report` 逐条对账并按规定披露。
  3. **新增 GraphProjection 校验**：
     - `graph_projection_closure`: 校验 GraphProjectionPack 中的 `release_id`、`canonical_hash` 与 Snapshot 及 ReleaseManifest 严格相等，节点/边集合与 KnowledgeDataPack 严格同构。
- **依据**：
  - 规格 §16:703-715（发布 Gate fail-closed 一票否决）；
  - `INTERFACES.md` §3.3（:261-274）、【I-11】、【I-12】；
  - `G7-RULINGS.md` 第 100 条 D5、D8、第 103 条 D1、第 106 条 D1。
- **未决点**：
  - 未决点 Q-M8-08：Gate 检查名清单（`_CHECK_NAMES`）如何优雅兼容两套证据级别。

### 11.8 验收面

- **现状（文件:行号）**：
  1. `openspec/acceptance/m8-span-identity.sh:11-12`：写死 `FIXTURE_DIR` 为 `mini_ed01`，`FIXTURE_ASSET_ROOT` 为 `sanche_pages`；
  2. `openspec/acceptance/m8-span-identity.sh:58-60`：仅执行 `--check span_identity`；
  3. `openspec/acceptance/run_all.sh:267,280,327,333`：20.4、20.6、20.8、20.9 均硬编码或条件判定为 `BLOCKED`。
- **设计**：
  1. **`m8-span-identity.sh` 电子文本路线分流**：
     - 引入环境变量分流：`EVAL_ROUTE=${EVAL_ROUTE:-ocr}`；
     - **第 97 条铁律**：显式变量分流、互不回落。
       - 若 `EVAL_ROUTE=text`（或设置了 `FIXTURE_TEXT_DIR`），指向《乾元秘旨》电子文本宿主（`pipeline/corpus/_fixture/qianyuan_w8`）。宿主缺失时退出码严格为 3（BLOCKED），绝不自动回退到 `mini_ed01`；
       - 若未指定（默认），保持原 OCR 路径与行为完全不变。
  2. **`run_all.sh` 20.4 / 20.6 / 20.8 / 20.9 转判条件**：
     - **20.4**（发布物↔原始证据双向可追溯）：当前因「候选/驳回项/正式知识未产出」BLOCKED。转判条件：M8 读 M7 Snapshot，编译出包含前三段的 EvidenceMapPack，并在 Gate 中通过 `chain_closure` 实评，双向索引全覆盖且无悬空；
     - **20.6**（Pattern 与 KnowledgeEntry 编译）：当前因「KnowledgeEntry 编译未实现」BLOCKED。转判条件：KnowledgeEntry 经 M7 正式 Pattern/Concept 聚合发号，支持 `not_captured` 语义并输出至 KnowledgeDataPack；
     - **20.8**（结构化知识与 SourceAssetPack 引用完整）：当前因「缺结构化知识」BLOCKED。转判条件：KnowledgeDataPack、EvidenceMapPack、SourceAssetPack（支持 `reference_and_hash_only`）编译成功且在 ReleaseManifest 中完成输入对账；
     - **20.9**（GraphProjectionPack 投影）：当前因「GraphProjectionPack 未实现」BLOCKED。转判条件：GraphProjectionPack 按照草案格式生成，节点/边完备且与 Snapshot 共享 `canonical_hash`。
- **依据**：
  - 规格 §20:940-945（20.4、20.6、20.8、20.9 判定条目）；
  - `G7-RULINGS.md` 第 97 条（显式分流、不回落）、第 100 条 D8、D9。
- **未决点**：
  - 未决点 Q-M8-06：电子文本宿主环境变量命名与判定入口参数。

### 11.9 ACT 拆分建议

依据依赖顺序与修改范围，建议将 M8 返工拆分为 6 个独立执行与验收的 ACT：

1. **ACT 09：`GraphProjectionPack` 纯函数编译器与契约草案**
   - *写范围*：`pipeline/dataset_compiler/packs.py`、`pipeline/dataset_compiler/tests/test_packs.py`；
   - *用例名*：`test_build_graph_projection_pack_structure`、`test_graph_projection_nodes_edges_sorted`、`test_graph_projection_canonical_hash_matches_snapshot`、`test_graph_projection_watermark_flagging`；
   - *用例与阈值估计*：新增约 12 条用例，套件累计达到 136 条。
2. **ACT 10：`reference_and_hash_only` 策略与 offset 证据链纯函数组装**
   - *写范围*：`pipeline/dataset_compiler/packs.py`、`pipeline/dataset_compiler/levels.py`、`pipeline/dataset_compiler/tests/test_packs.py`、`test_levels.py`；
   - *用例名*：`test_reference_and_hash_only_admission_allowed`、`test_build_source_asset_pack_reference_and_hash_only`、`test_build_evidence_map_pack_offset_chain`、`test_reference_and_hash_only_omits_raw_text`；
   - *用例与阈值估计*：新增约 15 条用例，套件累计达到 151 条。
3. **ACT 11：知识链前三段（KnowledgeEntry/Assertion/EvidenceLink）组装与 `ent_` 确定性发号**
   - *写范围*：`pipeline/dataset_compiler/packs.py`、`pipeline/dataset_compiler/canonical.py`、`pipeline/dataset_compiler/tests/test_packs.py`；
   - *用例名*：`test_ent_uuid5_deterministic_generation`、`test_build_knowledge_data_pack_entries`、`test_evidence_link_absolute_offset_binding`、`test_knowledge_chain_internal_demo_watermark`；
   - *用例与阈值估计*：新增约 16 条用例，套件累计达到 167 条。
4. **ACT 12：M8 独立 Gate 升级（知识链实评与 offset 校验）**
   - *写范围*：`pipeline/dataset_compiler/gate.py`、`pipeline/dataset_compiler/tests/test_gate.py`；
   - *用例名*：`test_gate_evaluates_knowledge_chain_closure`、`test_gate_rejects_assertion_bypass`、`test_gate_offset_anchor_continuity`、`test_gate_sanitization_disclosure_checked`、`test_gate_graph_projection_checked`；
   - *用例与阈值估计*：新增约 18 条用例，套件累计达到 185 条。
5. **ACT 13：M8 Ledger 事务与输入改读 M7 Snapshot**
   - *写范围*：`pipeline/dataset_compiler/inputs.py`、`pipeline/dataset_compiler/step.py`、`pipeline/dataset_compiler/tests/test_inputs.py`、`test_step.py`；
   - *用例名*：`test_resolve_m8_inputs_from_snapshot`、`test_resolve_m8_inputs_dispatches_by_evidence_level`、`test_run_m8_offset_level_internal_demo_succeeds`、`test_run_m8_packs_sealed_and_checkpoints`；
   - *用例与阈值估计*：新增约 16 条用例，套件累计达到 201 条。
6. **ACT 14：M8 验收面扩展与 `run_all.sh` 20.4/20.6/20.8/20.9 转判（独占 ACT，P4）**
   - *写范围*：`pipeline/dataset_compiler/acceptance.py`、`openspec/acceptance/m8-span-identity.sh`、`openspec/acceptance/run_all.sh`；
   - *用例名*：`test_acceptance_text_route_runs_and_verifies`、`test_acceptance_text_route_missing_blocks_exit_3`；
   - *用例与阈值估计*：新增约 10 条用例，套件累计达到 211 条；推动 20.4/20.6/20.8/20.9 依据实际产出转判。

### 11.10 未决点汇总表

| 编号 | 问题 | 候选方案 | 推荐 | 需谁裁决 |
|---|---|---|---|---|
| Q-M8-01 | KnowledgeEntry 主体选取原则 | A: 以 Pattern 为主体<br>B: 以 Concept 为主体<br>C: 双轨制（Pattern 与 Concept 均可为主体，依 `subject_entity_id` 区分） | **推荐 C**（符合 INTERFACES:298，兼顾概念字典与命理断语） | 主 Agent |
| Q-M8-02 | `ent_` 发号算法与跨 Release 延续 | A: UUIDv5（以 `technique_id:subject_entity_id` 为命名空间派生，纯函数确定性）<br>B: 号段确定性自增分配（如 `ent_qizheng_000001`，需维护分配器）<br>C: 运行时 UUIDv4 随机（破坏编译幂等，不推荐） | **推荐 A**（天然幂等，跨 Release 同对象不漂移） | 主 Agent |
| Q-M8-03 | `reference_and_hash_only` 下 EvidenceMapPack 是否保留 `quote`/`text` 字符串 | A: 彻底剔除（不输出字段，客户端仅通过 offset 与底本核对）<br>B: 字段置为 `null`<br>C: 保留短引文 `quote`，仅剔除全文 `text` | **推荐 B**（保持 Schema 键集稳定，同时杜绝文本泄露） | 主 Agent |
| Q-M8-04 | M8 输入中 M7 Snapshot 的粒度与形式 | A: 单 Technique 唯一定位一个 Snapshot（内含多个 Edition/EditionPart）<br>B: 单个 EditionPart 对应一个独立 Snapshot | **推荐 A**（符合规格 §16:699 与第 63 条 R1 裁决） | 主 Agent |
| Q-M8-05 | GraphProjectionPack 中边的 `edge_id` 生成规则 | A: 确定性三元组哈希（如 `e_` + sha256(source:relation:target)[:32]）<br>B: 顺序数字号段（如 `e_000001`）<br>C: 边不发独立 ID，仅以 `(source, relation, target)` 标识 | **推荐 A**（满足全局 ID 规范与跨 Release 稳定性） | 主 Agent |
| Q-M8-06 | `m8-span-identity.sh` 电子文本路线的环境变量名称 | A: `EVAL_ROUTE=text`（配 `FIXTURE_TEXT_DIR`）<br>B: `M8_ROUTE=offset`<br>C: 仅通过 `FIXTURE_DIR` 路径特征隐式推导（违反第 97 条，不推荐） | **推荐 A**（显式分流、语义清晰） | 主 Agent |
| Q-M8-07 | offset 证据链在 `EvidenceMapPack` 中的 `chain_segments` 声明 | A: 显式写为 `["KnowledgeEntry", "Assertion", "EvidenceLink", "SourceSpan", "SourceAnchor", "DeterministicPatchSet", "RawText", "SourceAsset"]`<br>B: 维持 7 段抽象名（用 `SourceAnchor` 代指 offset 锚点层） | **推荐 A**（如实反映证据链完整性，便于 Gate 逐段核对） | 主 Agent |
| Q-M8-08 | M8 Gate 中检查项清单（`_CHECK_NAMES`）组织形式 | A: 拆分为 `_COMMON_CHECKS` + `_GLYPHBOX_CHECKS` / `_OFFSET_CHECKS`<br>B: 保持单一列表，检查项内部根据 `evidence_level` 自动分派子检查 | **推荐 B**（对上游输出结构保持一致，减少调度复杂度） | 主 Agent |

### 11.11 主 Agent 裁决与更正（2026-09-16，G7-RULINGS 第 107 条）

本节覆盖 §11.1–§11.10 中与之冲突的内容；实现以第 107 条为准。

| 未决点 | 裁定 |
|---|---|
| Q-M8-01 主体 | **C 双轨**；主体只来自 Snapshot 中已审定的显式引用，**不推断**；无主体 assertion 不生成 entry、计入 `known_defects` |
| Q-M8-02 `ent_` | **UUIDv4**（规格 §8.1:318）；发号表（`subject_entity_id → entry_id`）作为冻结输入，step 层分配、纯函数层只读；**否决 UUIDv5/md5 派生** |
| Q-M8-03 正文 | **B**：`reference_and_hash_only` 下 `quote`、`source_span.text` 置 `null` |
| Q-M8-04 Snapshot 粒度 | **A** 一 Technique 一 Snapshot |
| Q-M8-05 边身份 | **C** 不发边 ID，以 `(source, relation, target)` 为身份（【I-10】不新增前缀）|
| Q-M8-06 验收变量 | `ELECTRONIC_TEXT_FIXTURE_DIR`（第 97 条既有），缺失 BLOCKED **exit 2** |
| Q-M8-07 链段 | **保持七段、恰 7 键**；第 6/7 段按级别分派：offset 为 `text_mapping{raw_text_revision_id, cleaned_text_revision_id, patch_set_revision_id, raw_start, raw_end}` 与 `source_asset{page, sha256}` |
| Q-M8-08 检查名 | 单一闭集，每项声明适用级别，不适用输出 `not_applicable` |

更正：

1. §11.6 示意片段中的书中文句（如「天官朝元格」）**两路抽取均无，属编造**，前缀 `c_`、`e_` 亦非规格前缀——该示意作废，实现以 INTERFACES 登记后的 schema 为准，示意不得引用任何书中文句。
2. §11.8 宿主路径更正为 `pipeline/corpus/_fixture/qianyuan_ed01_text`；宿主缺失为 BLOCKED **exit 2**；变量名见上表。
3. §11.2 中 `isolation`、`authoritative` 等未登记键删除，用已登记的 `watermark`、`known_defects` 表达。
4. ACT 顺序：**新增 ACT 08（impl-00 登记）置首**；ACT 13 须待 8.5（M7 Snapshot 补 `evidence_level`、`corpus_spans_revision_id`）验收后开工。


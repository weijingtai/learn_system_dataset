# impl-04：M8 Dataset Compilation（§16）首切片——证据尾链发布包

状态：`DRAFT`（起草 Agent 2026-09-11；§4 共 14 条待主 Agent 裁决；未经 `wjt-react`；不得派发）

## 1. 目标

在 `pipeline/dataset_compiler/` 落地规格 §16 M8 的**最小可判首切片**。输入是 Artifact Ledger 中已封存的 M3 StagePackage（impl-02 `run_m3` 真实产出）及其血缘上的 M1 清单、M2 OCR 页，外加经薄 M1 登记进 Object Store 的派生页图。首切片确定性编译以下内容，每个子包都是独立 Artifact：

- `SourceAssetPack`（`derived_page_images_only`）
- `EvidenceMapPack`：只闭合 SourceSpan → SourceAnchor → OcrPage/字框 → SourceAsset 页这**尾部四段**；KnowledgeEntry/Assertion/EvidenceLink 三段标 `not_compiled`
- `ReleaseManifest`：子包哈希清单、来源与修订对账、消费级别、水印与已知缺陷披露
- `ValidationReport`：独立实现的 fail-closed 发布 Gate
- `PublicationPackage` 与 m8 StagePackage

消费级别只签发 `INTERNAL_DEMO`。`DEV_SEARCH`/`PUBLIC_RELEASE` 进入 StepRun 后以 `admission` 失败封存，不降级、不重试。

完成判据（本包唯一的「做完」定义；带「D3」标记的依 §4 D3 推荐）：

```bash
export LC_ALL=en_US.UTF-8
.venv/bin/python -m unittest discover -s pipeline/dataset_compiler/tests -t . 2>&1 | tail -1
# 期望：OK（用例 ≥ 125；本机页图存在，不得出现 skipped）
bash openspec/acceptance/m8-span-identity.sh; echo exit=$?
# 期望：7 行 PASS（run_succeeded span_key_unique legacy_collision_exposed span_page_binding anchor_to_page_image glyph_closure reverse_index）
#       + 1 行 BLOCKED mentions_mapping + SUMMARY pass=7 fail=0 blocked=1；exit=2
.venv/bin/python -m pipeline.dataset_compiler.acceptance --fixture pipeline/corpus/_fixture/mini_ed01 --check publication; echo exit=$?
# 期望：8 PASS + BLOCKED knowledge_chain + SUMMARY pass=8 fail=0 blocked=1；exit=2
FIXTURE_ASSET_ROOT=/nonexistent bash openspec/acceptance/m8-span-identity.sh; echo exit=$?
# 期望（D3）：首行 BLOCKED m8_acceptance BLOCKED_SOURCE_ASSET_MISSING …；exit=3
bash openspec/acceptance/run_all.sh | tail -1
# 期望：SUMMARY pass=2 fail=1 blocked=8（ACT 08 之后 20.4/20.8 仍为 BLOCKED，只改写原因；D6）
```

`m8-span-identity.sh` 是 §19.0 已登记的「M8 映射键碰撞」判据（`openspec/learn-system-blackbox-architecture.md:912`）。本包关闭**键身份**部分，但 concept→span 的 mentions 映射依赖 M4，所以脚本返回 **2**，差距仍记为未关闭，与 impl-02 `m3-coverage.sh` 的先例一致（`impl-02-corpus/README.md:17`）。

## 2. 依据（只读来源，文件:行号）

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
- `openspec/legacy-storage-transition.md`：rag 索引「span key 碰撞和错链」（27）；页图不得伪造（65–67）
- `pipeline/rag/build_index.py:133-138`：`span_map[source_id][int(sNN)] = span_id`，丢了页号，这是碰撞根因
- fixture `pipeline/corpus/_fixture/mini_ed01/`：
  - `manifest.yaml:5-6`：`rights_status` 含「扫描件分发权 unconfirmed」、`release_policy: derived_page_images_only`
  - `spans.yaml`：43 条（page_001 4 条、page_003 39 条）
  - `README.md:16`：「不得作为知识来源、证据来源或发布输入引用」
- Ledger：
  - `pipeline/ledger/service.py`：`RUN_ARTIFACT_TYPES`（66）、`create_processing_run` 单 edition_part（319–345）、`begin_step_run` 由配置推导 stage（369–371）、`put_artifact(rights_scope=…)`（442–457）、`register_stage_package` 登记类型 `stage_package`（718–774，753）、`finish_step_run`（1132–1185）、`write_checkpoint`（1364–1398）
  - `pipeline/ledger/store.py`：`size_bytes`（42）、`transformation_inputs`（139–144）
  - `pipeline/ledger/fixture_ingest.py`：阶段输出类型（40–46）、`ocr_page`（193）；`pipeline/ledger/acceptance.py:77` `_frozen_inputs` 先例
- impl-02：`act/01.yaml:35-38`（corpus_spans 结构）、`act/03.yaml:17`（只读 SELECT 先例）、`act/03.yaml:49-58`（m3 包结构）、`act/05.yaml:26-29`（异常分层）、`README.md:40`（退出码纪律）
- `openspec/acceptance/run_all.sh`：20.4（212）、20.8（272）

**起草时实测的事实（2026-09-11，本机）**：

- `run_all.sh` → `SUMMARY pass=2 fail=1 blocked=8`。
- `ocr/data_work/sanche_pages/page_001..003.png` 存在；fixture 页 JSON 与清单尺寸都是 1203×1654。
- 43 条 span 的字框共 230 个，全部在页框内。
- 其中 2 条 span 的文本比字框多 1 字：
  - `ss_sanche_ed01_p0001_s03`：6 字 / 5 框
  - `ss_sanche_ed01_p0001_s04`：17 字 / 16 框
- 按 `build_index.py` 的 `(source_id, sNN)` 规则给 fixture 的 43 条 span 取键，会塌缩为 **39 键、4 组碰撞**。宿主本身就能复现 §19 登记的缺陷类别。

## 3. 范围

写（ACT 逐个限定）：

- `pipeline/dataset_compiler/**`（新建，含 `shim/` 与 `tests/`）
- `openspec/acceptance/m8-span-identity.sh`（ACT 07 新建）
- `openspec/acceptance/run_all.sh`（仅 ACT 08，仅 20.4/20.8 两段与一个辅助函数，依 D6）

禁止：

- 改规格正文、`openspec/schemas/**`、fixture 目录、`pipeline/ledger/**`、`pipeline/corpus_compiler/**`、`PLAN.md`、`HANDOFF.md`、`SUBAGENT_TODO.md`、其他 work-items
- 新增依赖；新增 ID 前缀（只用已登记的 `rel_`、`pkg_m8_`、`art_`、`rev_`、`prun_`、`srun_`，首切片不发 `ent_`）
- 调用任何模型 API
- 生产代码读 fixture 路径或工作目录文件（唯一例外是 D2 的薄 M1 页图登记，它的职能是 Source Intake）
- 合成或伪造与 fixture 哈希同值的页图
- 把任何 BLOCKED 写成 PASS
- 执行者写台账或 `ACCEPTED`

## 4. 待主 Agent 裁决

每条给出选项、**推荐**与理由；未裁决前，ACT 草案按「推荐」写入，裁决不同则由主 Agent 改 ACT。

**D1 上游 M4–M7 缺席时 M8 的输入策略**（§16:661-662 冻结 CanonicalKnowledgeSnapshot；§16:705-713 七段链；§22.4:997）
- A 尾链首切片：只冻结 M3 StagePackage 及其血缘输入与页图；EvidenceMapPack 只闭合后四段，前三段 `knowledge_chain: not_compiled`；不产出 KnowledgeDataPack。
- B 金标注入：新增 fixture 期望产物（最小 Concept/Pattern/Assertion/EvidenceLink），以「薄 M7」StepRun 写入 Ledger 作为 Snapshot，M8 编全链。代价：
  - 需要新 fixture 文件；
  - EvidenceLink 无登记前缀（§8.1:265 只要求双标识）；
  - `pat_` 需先经 Contract Registry 登记（`id-prefix-registry.md:60`）；
  - 与 fixture `README.md:16`「不得作为知识来源…或发布输入引用」直接冲突。
- C 等 M4–M7 实现后再做 M8：违背 §22.4 首纵切顺序。
- **推荐 A**：不伪造知识，全部判定都有真实来源；B 可在裁决后另起 ACT 09+。
- **附带冲突**：A 同样触及 `README.md:16`「发布输入引用」的字面。请裁定「仅在临时 Ledger 内编译、INTERNAL_DEMO、验收后删除、不落盘不分发」是否豁免。

**D2 页图进入 Ledger 的「薄 M1」放在哪**（§16:723；§22.1:968；§22.3:991「手工登记 SourceAsset」；`fixture_ingest.py` 注释第 3 条称不读页图）
- A `pipeline/dataset_compiler/shim/source_assets.py`：独立 m1 StepRun、每页一个 task/Checkpoint、登记 `source_asset_page` 修订，不登记第二个 m1 StagePackage。
- B 扩展 `pipeline/ledger/fixture_ingest.py` 的 `asset_root` 钩子：改 impl-01 已验收文件，m1 Checkpoint 数变化会波及 `pipeline/ledger/acceptance.py` 的链长判据（20.2）。
- C 首切片改用 `reference_and_hash_only`：与 §16:723、§22.1:968、`manifest.yaml:6` 冲突，需要改规格。
- **推荐 A**：不碰已验收模块；shim 是本包唯一读文件的生产代码，职能属 M1，在文件与 CLI 名上显式标明。

**D3 本机缺页图时 M8 验收的退出码**（`README.md:40` 退出码纪律；`legacy-storage-transition.md:67`）
- A 退出 3（宿主缺失），打印 `BLOCKED m8_acceptance BLOCKED_SOURCE_ASSET_MISSING <path_ref…>`。
- B 退出 2（BLOCKED），其余判定照跑。
- C 合成页图：禁止。
- **推荐 A**：页图缺失时 `run_m8` 无法开始，没有「部分判定」可跑。缺的是宿主素材，与缺 fixture 同类。

**D4 新 artifact_type**（Ledger 只校验 `^[a-z][a-z0-9_]*$`，`service.py:442-457`；仓库无 artifact_type 登记册）
- 新增：`source_asset_page`、`source_asset_register`、`source_asset_pack`、`evidence_map_pack`、`release_manifest`、`publication_package`。
- 复用：`configuration`、`validation_report`、`step_log`、`failure_report`、`stage_package`。
- A 按上表批准。B 改名（例如按子包驼峰名去大小写）。C 先建 artifact_type 登记册再用。
- **推荐 A**，并建议主 Agent 决定是否补一张登记表（与 ID 前缀登记册同形）。

**D5 子包 Schema**（子包在 `openspec/schemas/` 中均无 Schema；§8:244-251 只冻结四份 L0；`openspec/schemas/verify.sh:28` 以 glob 做元 Schema 校验）
- A 代码内草案契约，`schema_version: "0.1.0-draft"`；准入层对 `PUBLIC_RELEASE` 以 `draft_schema` 拒绝。
- B 本包新增 `openspec/schemas/m8_*.schema.json` 与 examples（需授权改 schemas 目录）。
- C 只写文档契约。
- **推荐 A**：知识链三段未定型，现在冻结必然返工；fail-closed 保证草案进不了正式发布。

**D6 `run_all.sh` 20.4/20.8 怎么变**（§20:935、940、944）
- A 单独 ACT 08：两条改为执行 m8 判定。判定 FAIL → `FAIL`；否则 `BLOCKED 前置缺失: M4 Knowledge Extraction；<已判定段>…`；**永不 PASS**。
- B 不改，保持静态 BLOCKED。
- C 判 PASS：假绿，因为 20.4 缺候选/驳回项/正式知识，20.8 缺「结构化知识」。
- **推荐 A**：回归可被发现，`SUMMARY` 不变。20.6/20.9/20.11 不动。

**D7 §16 五项冻结输入的载体**（§16:661-666；`service.py:66` put_run_artifact 只允许 configuration/technique_profile）

| 输入项 | 选项 A 的载体 |
|---|---|
| 发布范围、消费级别、`min_app_version`、`release_id` | 写入 m8 配置修订 |
| ReleasePolicy 与权利 | 取 M1 清单修订的 `release_policy`/`rights_status`（随清单冻结） |
| TechniqueProfile | 只有 `technique_profile_id="qizheng"` 字符串，ReleaseManifest 写 `technique_profile_version: null` |
| CanonicalKnowledgeSnapshot | 由 M3 StagePackage 代替（D1） |

- A 按上表。B 新增 `release_policy` artifact_type 并放行 put_run_artifact（改 Ledger）。C 由 Contract Registry 提供（L2' 未实现）。
- **推荐 A**。

**D8 M8 的 ProcessingRun 归属**（§6.2:153-167；`service.py:319-345` 只接受单个 edition_part_id）
- A 每次 `run_m8` 新建 `release_run`。B 复用 M3 所在的 `edition_run`。
- **推荐 A**，符合 §6.2。另注：跨多个 EditionPart 的 Release 需要改 Ledger，首切片不涉及。

**D9 `source_release` 的定义**（§16:697 与 DATASET:99 只说 `dev` 必须拒绝，未定义来源；`build_index.py:167` 写死 `dev`）
- A 由内容成熟度推导：全部 ∈ {`expert_verified`,`source_verified`} → `release`；含 `deprecated` → 拒绝；其余 → `dev`。
- B 配置显式参数：可被人为改写，违背 §16:668。
- C 取上游包字段：上游无此字段。
- **推荐 A**。另请裁定 `source_verified` 是否算 release 级（它只表示原文与出处已核对，§8.2:341）。

**D10 INTERNAL_DEMO「隔离并水印、披露缺陷、不得声称完备权威」的数据形态**（§16:676；DATASET:42、95）
- A 数据层落地：
  - 每条 entry `watermark: true`；ReleaseManifest `watermark{required,text}`；
  - `isolation: internal_only`、`authoritative: false`、`completeness_claim: partial`；
  - `known_defects` 用代码闭集 `excluded_page`/`glyph_text_mismatch`/`knowledge_chain_not_compiled`/`machine_content`/`rights_unconfirmed`/`semantic_not_evaluated`；
  - 全部修订 `rights_scope="internal"`。
- B 只在渲染时加水印：客户端可绕过，违背 §16:668。
- **推荐 A**。水印文案草案「INTERNAL_DEMO｜机器转录，未经人工校对｜不得作为知识来源或权威依据」待定。

**D11 文本字数多于字框、坐标格式**（§16:714 坐标同源；§11.1:528「四点坐标」对 fixture `{x,y,w,h}`）
- A 该 2 条降级为 `highlight_level: line_bbox`（整行框高亮），登记 `glyph_text_mismatch` 披露；字框原样搬运 `{x,y,w,h}`，同源性以页 JSON 宽高 = 清单宽高 = PNG 头宽高判定。
- B 所有级别 fail-closed：fixture 上连 INTERNAL_DEMO 都无法签发。
- C 用 LCS 对齐猜缺失字框：启发式，违背 §16:733「不得猜测」的精神。
- **推荐 A**。PUBLIC_RELEASE 准入层实现时追加该项拒绝。上游问题见 §8 第 7 条。

**D12 `min_app_version` 没有取值来源**（§16:697 必含；DATASET:99）
- A 可选 semver 参数：INTERNAL_DEMO 允许 `null`；PUBLIC_RELEASE 记 `min_app_version_unset` 并拒绝。
- B 必填，fixture 验收填占位值：等于伪造。
- C 等规格补定义。
- **推荐 A**。

**D13 重跑与多 Release**（§17.1:842 一条 EditionPart×Stage Checkpoint 链；20.11 需要两个 Release）
- A 首切片拒绝第二次 m8（「M8 已封存」）。
- B 允许同一 EditionPart 多次 m8 StepRun、形成多个 Release：需先裁定 Checkpoint 链语义与 `IdentityMigrationMap`。
- **推荐 A**，在 AnchorContractPack 批次再议。

**D14 首切片子包集合与 §22.2:979 不一致**（§22.2 列 KnowledgeDataPack + EvidenceMapPack + SourceAssetPack + QueryContractPack）
- A EvidenceMapPack + SourceAssetPack + ReleaseManifest + ValidationReport。
- B 追加 QueryContractPack 草案：只有 `getSourceSpan` 有数据，`getEntry`/`searchKnowledge`/`matchFacts` 空转。
- C 追加 SearchIndexPack 精确索引（`span_id → text/quote_sha256`），直接替代 rag 碰撞索引。
- **推荐 A**。C 留到关闭 `mentions_mapping` 时与 M4 mentions 一起做；KnowledgeDataPack 随 D1-B 或 M4–M7 落地。

## 5. 起草默认（裁决后固化为「主 Agent 决定」，执行者不重议）

1. **消费级别闭集**：`INTERNAL_DEMO`/`DEV_SEARCH`/`PUBLIC_RELEASE`，其他值（含小写）在 begin 之前以 `SCH_002` 拒绝且无写入。合法但不满足准入的级别在 begin 之后以 `admission` 失败封存（§17:836「失败也必须封存」）。准入判定先于任何子包编译，失败运行不留任何子包修订，也不以低级别自动重试。
2. **四个 task，每个 task 一个 m8 Checkpoint**（§17.1:843），顺序：`source_asset_pack` → `evidence_map_pack` → `release_manifest` → `validation_report`。
3. **身份键**：EvidenceMapPack 的 `entries` 以完整 `span_id` 为键，禁止 `(source_id, sNN)`。`span_id` 中的 `p<4位>`/`s<2位>` 必须等于 `page` 页号与 `line_index+1`，这是「修好解析后链到错误页」的防线（§19:882）。反向索引 `page_index` 覆盖清单全部页，排除页值为 `[]`。
4. **哈希无环**：ReleaseManifest 只含两个内容子包的哈希与输入对账；ValidationReport 校验 ReleaseManifest；PublicationPackage 与 StagePackage 汇总全部。`canonical_hash` = 按 pack_type 排序的 `[pack_type, sha256]` 列表的规范化 JSON 的 sha256。
5. **规范化 JSON**：`sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False`，UTF-8。`normalized_sha256` 递归去掉以 `artifact_revision_id` 结尾的键，用于比对两个独立 Ledger 的编译结果。
6. **Gate 独立**：`gate.py` 不 import `packs`/`canonical`/`levels`/`step`，从页 JSON 与清单重算。`acceptance.py` 不 import `packs`/`gate`，不读 `run_m8` 返回的 gate。
7. **异常分层**照搬 impl-02 `act/05.yaml:26-29`：begin 之前的解析、拒绝原样外抛；begin 之后分 `input_contract`/`admission`/`compile`/`publication_gate`/`internal` 五类失败封存。
8. **输入解析**：沿 M3 StagePackage 的 `manifest.input_artifacts` 反查 M1 清单与 M2 页修订，不再遍历 m1/m2 Checkpoint，信任链与血缘一致。`stage_package` 修订、`frozen_inputs`、`transformation_inputs` 经 `reader.store.conn` 只读 SELECT。
9. **测试宿主**：依赖真实页图的集成测试用 `skipUnless(assets_available())`，本机必须 0 skipped。合成 PNG 只能配合合成清单用于 shim 单元测试，不得与 fixture 哈希同值。
10. **派发分组**：
    - K1 = ACT 00–02：纯函数，可立即派发，只依赖 D1/D4/D5/D9/D10/D11 裁决。
    - K2 = ACT 03–06：Ledger。前置 impl-02 `ACCEPTED`，以及 D2/D3/D7/D8/D12/D13。
    - K3 = ACT 07–08：验收与 run_all。前置 D3/D6。

## 6. 上游输入契约（本包假设，供并行草案对账）

| 来源 | artifact_type | 本包读取的字段 | 依据 |
|---|---|---|---|
| M3 | `stage_package`（stage `m3`，sealed） | `stage_package_id`、`validation.passed == true`、`payload.spans_revision_id`、`payload.excluded_pages`、`payload.gate_profile`、`manifest.content_sha256`（== corpus_spans 字节哈希）、`manifest.input_artifacts`（含 `source_manifest`×1、`ocr_page_set`×1、`ocr_page`×N） | impl-02 `act/03.yaml:49-58`；`service.py:753` |
| M3 | `corpus_spans` | `source_id`、`edition_part_artifact_id`、`evidence_level`、`content_status`、`span_count`、`spans[].{span_id,page,line_index,start_offset,end_offset,text,source_anchor{page,image_sha256,line_id,bbox,chars[char_index,glyph_id,char,box]}}` | impl-02 `act/01.yaml:35-38` |
| M1 | `source_manifest` | `source_id`、`technique_id`、`rights_status`、`release_policy`、`edition_part{artifact_id,pages}`、`source_assets[].{page,sha256,width,height,path_ref}` | fixture `manifest.yaml` |
| M2 | `ocr_page` | `page`、`width`、`height`、`lines[].{id,box,text}`、`chars[].{id,parent,char,box}` | `fixture_ingest.py:193` |
| M2 | `ocr_page_set` | 只作存在性与血缘对账 | `fixture_ingest.py:45` |
| 薄 M1（本包 ACT 03） | `source_asset_page`（PNG 字节，`rights_scope=internal`） | m1 Checkpoint `task_id = source_asset_<page>` | D2 |

M8 找 M3 的规则：`list_checkpoints(ep,"m3")` → 恰一个 succeeded 的 StepRun → 该 StepRun 下恰一个 sealed 的 `stage_package` 修订。`fixture_ingest` 灌入的 m3 包没有 `spans_revision_id`，必须拒绝。

首切片**不消费**：M4 CandidatePackage、M5 ValidationPackage、M6 ReviewedEditionPackage、M7 CanonicalKnowledgeSnapshot、TechniqueProfile 修订。

## 7. 对下游的输出契约

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
  - `python -m pipeline.dataset_compiler.shim.source_assets --root … --edition-part … --asset-root …`：`ASSETS OK|FAILED|REFUSED` 或 `BLOCKED_SOURCE_ASSET_MISSING`，退出 0/1/2/3
- **APP mock / 注解社区消费提示**：
  - 按 `span_id` 取 entry，`highlight_level` 决定逐字框还是整行框，`frame` 与页图像素同源，页图按 `source_asset_artifact_revision_id` 从 Object Store 解析。
  - 首切片不产出 AnchorContractPack，社区 `anc_` 锚点（`id-prefix-registry.md:76`）暂不能绑定 Release 的迁移契约。

## 8. 与其他模块、并行草案的接口假设

1. **impl-02（M3）**：J3 返工（`act/05.yaml`）后 `run_m3` 的输出契约与 §6 表一致且不再变动。本包 K2 以 impl-02 `ACCEPTED` 为前置，`test_step` 使用 `ingest(stages=("m1","m2")) → run_m3`。
2. **impl-03（M5，并行起草）**：
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
6. **并行编码 Agent**：本包只写 §3 所列路径，与 impl-02 J3 的写集（`pipeline/corpus_compiler/**`）不相交；ACT 08 与任何改 `run_all.sh` 的批次互斥，派发前需确认无并发改动。
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
  shim/source_assets.py  register_source_assets + CLI（薄 M1，唯一读文件的生产代码）
  inputs.py            resolve_m8_inputs（Ledger 只读）
  step.py              run_m8（§17 事务序列）
  __main__.py          python -m pipeline.dataset_compiler
  acceptance.py        span_identity 与 publication 两组判定
  tests/               _ledger_helpers.py test_canonical.py test_levels.py test_packs.py test_gate.py test_shim.py
                       test_inputs.py test_step.py test_step_failures.py test_cli.py test_acceptance.py
openspec/acceptance/m8-span-identity.sh
openspec/acceptance/run_all.sh（ACT 08 只改 20.4/20.8）
```

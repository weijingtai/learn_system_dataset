# ACCEPTANCE：impl-04 M8 Dataset Compilation 首切片（证据尾链发布包）

本文件只写**审查要点与判据**，不写任何验收结论；结论与验收记录由主 Agent 填写（§5）。

## 0. 转译审查要点（主 Agent 四查）

- **忠实性**：`README.md` §1 目标、`BDD.md` 1–9、各 `act/*.yaml` 的 contract 与 `G7-RULINGS.md` §1 P1–P9、§2 impl-04 裁决表逐条对应。
  - D1/P1：只冻结 M3 StagePackage 及血缘输入与页图；EvidenceMapPack 只闭合尾链四段，`knowledge_chain: not_compiled`；M4/M6/M7 与前三段一律 BLOCKED，不注入合成知识。
  - D2/P9：薄 M1 在 `shim/m1_shim_source_assets.py`，文件名与 CLI 名显式标 `m1_shim`，README 登记「impl-09 M1 落地后替换」；不改 impl-01 已验收的 `fixture_ingest.py`。
  - D3：缺页图报 `BLOCKED_SOURCE_ASSET_MISSING` 并退出 3；禁止合成同哈希页图。
  - D4/P2：新 artifact_type（`source_asset_page`、`source_asset_register`、`source_asset_pack`、`evidence_map_pack`、`release_manifest`、`publication_package`）已在 `INTERFACES.md` §4 闭集登记（与 §4 表逐字一致）；实现前以 `python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py` 核对（末行 `I00-IF SUMMARY pass=18 fail=0`、exit 0）；实现中不得出现闭集外类型名。
  - D5/P3：子包内容为代码草案，`schema_version: "0.1.0-draft"`；`PUBLIC_RELEASE` 以 `draft_schema` 拒绝；不新增 `openspec/schemas/` 文件。
  - D6/P4：20.4/20.8 由本包唯一 ACT 08 接线，永不 PASS；`SUMMARY` 保持 `pass=2 fail=1 blocked=8`。
  - D9 加裁：`source_verified` 不算 release 级，`source_release == "release"` 仅当 `content_status` 全为 `expert_verified`。
  - D10/D11：水印文案逐字为草案；2 条文本多于字框的 span 降级 `line_bbox` 并披露，PUBLIC_RELEASE 追加拒绝。
  - P5：解析上游 StagePackage 只接受所属 StepRun `succeeded` 的包（`impl-02 ACCEPTANCE.md` §5.3）。
- **覆盖性**：BDD 各条都能在某个 `act/*.yaml` 的 `tests` 用例名或 `verify` 命令上找到落点；K1/K2/K3 的串行前置与 `depends_on` 一致；`README.md` §1 完成判据覆盖单测、`m8-span-identity.sh`、`--check publication`、缺页图退出 3、`run_all.sh` SUMMARY 五项。
- **可执行性**：每个 ACT 有 `scope.write`、先红后绿的用例名、contract（函数签名/规则/检查名/退出码）、精确 `verify`、`commit.add`/`message`；退出码纪律（0/1/2/3）在 `m8-span-identity.sh`、`acceptance.py`、CLI 三处一致。
- **独立性**：`gate.py` 不 import `packs`/`canonical`/`levels`/`step`；`acceptance.py` 不 import `packs`/`gate`，不读 `run_m8` 返回的 gate；`acceptance.py` 不信任被验目录自带 `verify.sh`（永远调用仓库内规范脚本）。

派发前核对（主 Agent 脚本，定稿时执行）：9 份 ACT YAML 可解析；`ACT.yaml` 的 acts 与 `act/*.yaml` 一一对应；`impl-02` 状态 `ACCEPTED`；`python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py` 末行 `I00-IF SUMMARY pass=18 fail=0` 且 exit 0；本机三页页图存在；`m8-span-identity.sh` 尚不存在（exit 127）；`run_all.sh` 20.4/20.8 当前为静态 BLOCKED；按 `build_index.py` 规则独立复算 fixture 43 span → 39 键、4 组碰撞；fixture `spans.yaml` sha256 = `ec6d77b9…44ef`。

## 1. 范围核对

每个提交只含该 ACT `commit.add` 路径；`pipeline/dataset_compiler/` 之外仅 `openspec/acceptance/m8-span-identity.sh`（ACT 07）与 `openspec/acceptance/run_all.sh`（仅 ACT 08，仅 20.4/20.8 段）；规格、Schema、fixture、`pipeline/ledger`、`pipeline/corpus_compiler`、台账文件未动；无 `var/`、`__pycache__`；`git diff --check` 通过。

## 2. 门禁与判据（`git archive` 干净树，软链 `.venv` 与工作台 assets，`FIXTURE_ASSET_ROOT` 指本机页图）

- `ACT.yaml` 全部 `gates` 绿；三套 `unittest`（ledger、corpus_compiler、dataset_compiler）全过且用例数达 `TDD.md` §1 阈值；`m8-span-identity.sh` → `SUMMARY pass=7 fail=0 blocked=1`、exit 2；`acceptance.py --check publication` → `SUMMARY pass=8 fail=0 blocked=1`、exit 2；`FIXTURE_ASSET_ROOT=/nonexistent` → exit 3；`run_all.sh` → `pass=2 fail=1 blocked=8`。
- `TDD.md` §2 附加判据逐条实跑；`README.md` §1 完成判据逐条复现。

## 3. 语义与质量审查清单

- 纯函数性：`canonical.py`/`levels.py`/`packs.py`/`gate.py` 不读文件、不取时间、不用随机数。
- 身份键：`entries` 以完整 `span_id` 为键；`span_id` 页号/行序与 `page`/`line_index+1` 一致；反向索引覆盖清单全部页、排除页为 `[]`。
- 哈希无环：ReleaseManifest 只含两个内容子包的哈希与输入对账；`canonical_hash` 可按 pack_type 排序重算；`m8` StagePackage `content_sha256` == release_manifest 字节哈希。
- 事务序列与 §17 一致；`run_m8` 冻结输入恰 10 个；begin 之前的拒绝无写入；begin 之后的失败封存完整（检查名 ∈ {`input_contract`,`admission`,`compile`,`publication_gate`,`internal`}），失败运行不留子包修订、不留第二个 m8 StepRun。
- fail-closed：`DEV_SEARCH`/`PUBLIC_RELEASE` 失败且四类子包修订数为 0；任何输入下 `PUBLIC_RELEASE` 均不 `admitted`；`draft_schema`/`rights_unconfirmed` 参与拒绝。
- 披露不少报：fixture 上 `known_defects` 代码恰为六个；任一 `entry.watermark` 为 false 即 Gate 失败。
- 宿主有效性：`legacy_collision_exposed` 的 39/4/43 由 fixture 重算，不是常量；副本假 `verify.sh` 下仍 `FAIL fixture_host`、exit 1。
- 独立重算：Gate 与验收判定均不依赖被验实现自身产出的 gate 报告。
- 中文注释；无 `except: pass`；不新增依赖、ID 前缀、模型调用。

## 4. 结论规则

- K1、K2、K3 各自通过后，由主 Agent 在 §5 记名并写 `ACCEPTED`；执行者不得自记。
- 任一 FAIL 视为未通过，返工另立 ACT；`mentions_mapping`、`knowledge_chain` 与 `run_all.sh` 20.4/20.8 的 BLOCKED 不视为失败，但必须确属 §19 第一列差距。
- 全部通过后，由主 Agent 同步 `SUBAGENT_TODO.md`、`HANDOFF.md` 并据此勾选 `PLAN`/`G7-PLAN` 相应项。

## 5. 验收记录

§5 验收记录由主 Agent 填写。

### 5.1 W3-F 实现（2026-09-12，主 Agent 独立验收，`git archive` 干净树）

执行者：tmux 中的 cmd（DeepSeek V4.1 Flash），会话 `w3f`，按 K1/K2/K3 分组停下待验收。

- K1（ACT 00–02：`a64d0e9`、`000386e`、`4a79ef5`）：范围仅 `pipeline/dataset_compiler`；`dataset_compiler` 73 OK、ledger 74 OK、corpus_compiler 68 OK；`gate.py` 不 import 编译器实现；`canonical/levels/packs/gate` 无文件、时间、随机、uuid、环境副作用；全部门禁绿。回归取行方式裁定为 `grep -E "^(Ran|OK|FAILED)"`（G7-RULINGS 第 27 条）。
- K2（ACT 03–06：`7dcf032`、`5a54d42`、`f85471e`、`338c157`）：`dataset_compiler` 113 OK。ACT 03 薄 M1 按第 32 条改用 `supersede_step_run` 接替 m1 运行（不改 Ledger），并新增 `test_register_assets_keeps_m3_input_resolution`。矩阵外端到端 15 项全过：INTERNAL_DEMO succeeded、恰 1 个 m8 包、EvidenceMapPack 43 个唯一完整 `span_id`、知识链前三段 `not_compiled`、ReleaseManifest 级别 INTERNAL_DEMO、两次运行（去身份字段）一致、登记页图后 `resolve_m3_inputs` 清单不变、DEV_SEARCH/PUBLIC_RELEASE `failed/admission` 无包、页图目录缺失 `SourceAssetMissing`、未登记页图 `DatasetRefused`、M3 spans 与页图对象篡改 `failed/input_contract`、fixture 灌入 m3 包（无 `spans_revision_id`）拒绝、begin 后注入异常 `failed/internal` 无包。
- K3（ACT 07 `c36d628`、ACT 08 `950b77b`）：`dataset_compiler` 125 OK；`m8-span-identity.sh` `SUMMARY pass=7 fail=0 blocked=1`、exit 2（`mentions_mapping` BLOCKED）；`run_all.sh` 改前改后均 `pass=2 fail=1 blocked=8`，除 20.4/20.8 外无行变化，两条仍 `BLOCKED 前置缺失: M4 Knowledge Extraction` 并写明已判定段，20.4/20.8 段无 `pass_line`。fixture 副本删一条 span：`m8-span-identity.sh` exit 1 落点 `FAIL fixture_host`，`run_all.sh 20.4` `FAIL fixture_host`，直接调用 acceptance 模块落点 `FAIL span_key_unique`（第 44 条；BDD §9.2 与 act/08 verify 注释已订正 `ccbfe64`）。`acceptance.py` 三处 import 为 `run_m3`/`register_source_assets`/`run_m8` 用于构造真实链路，发布判定由自身 `_evaluate_publication` 重算；`DEFAULT_FIXTURE` 常量仅作 `--fixture` 缺省值（建议，登记不返工）。
- 全部门禁（`950b77b` 干净树）：`verify-T.sh` 0 FAIL、`mutations.sh` 109/109、`schemas/verify.sh` 0、`check_d16.py` OK、`check_interfaces.py` 18 PASS、`m3-coverage.sh` exit 2。

impl-04（M8 首切片，证据尾链发布包，INTERNAL_DEMO）`ACCEPTED`。§20.4/§20.8 仍 BLOCKED（M4 未接入），§19 M8 差距不宣称关闭。

### 5.2 W8 8.6 实现组 K1：ACT 09 + ACT 10（2026-09-16，主 Agent 独立验收，`git archive ce3ddab` 干净树；执行器 agy Gemini 3.8 Flash Medium）

判定：**ACT 09（`fc31716`）与 ACT 10（`ce3ddab`）ACCEPTED**，附一项纪律提醒。

- ACT 09：`packs.build_graph_projection_pack` 按 INTERFACES §3.15（边无 ID、三元组排序、前缀与 relation 闭集、`release_id`/`canonical_hash` 共享、INTERNAL_DEMO 水印）。ACT 10：`levels.py` 放行 `reference_and_hash_only`；SourceAssetPack 按策略分派；EvidenceMapPack offset 第 6/7 键 `text_mapping`/`source_asset{page, sha256}`、恰 7 键；`reference_and_hash_only` 下 `quote`、`source_span.text` 为 `null`；片段身份经 `pipeline.ledger.ids`。
- 干净树：dataset_compiler `Ran 143 OK (skipped=32)`（125 → 143，skipped 数不变）；`check_interfaces` `pass=44 fail=0`（IF44 XFAIL 列表未变，符合本轮不改 `gate.py`）；`m8-span-identity.sh` 在干净树因页图不入库如实 BLOCKED，执行方工作树前后一致。
- 用例审计（AST）：`test_levels.py` 删 0 改 0；`test_packs.py` 删 0，**ACT 10 提交改动了 ACT 09 刚新增的 `test_graph_projection_mirrors_knowledge_data_entities`——删去一行 `assertEqual(pack["node_count"], 4)`，回报未报备**。该字段仍由结构用例 `node_count == 3`、`edge_count == 2` 覆盖，不构成覆盖缺口；因属同组未验收用例，不按第 97 条返工，但记为纪律提醒：**任何断言删除都必须在回报中报备**。
- **主 Agent 篡改**（临时副本）：`reference_and_hash_only` 下不再置空 `source_span.text` → `test_evidence_map_reference_and_hash_only_nulls_quote_and_text` 转红。执行方三组（边加 `edge_id`、offset 链 8 键、保留 `quote`）亦转红。

### 5.3 W8 8.6 实现组 K2：ACT 11 + ACT 12（2026-09-17，主 Agent 独立验收；执行器 freebuff GLM 5.3 Flash 会话 fb86d）

判定：**ACT 11（`496fbb1`）与 ACT 12（`162250c`）ACCEPTED**。

- ACT 11（`496fbb1`）：`build_knowledge_data_pack` 构建 EvidenceMapPack 前三段（`entry_id`、`assertion_id`、`evidence_link`），双轨不推断（Pattern 携带快照审核裁定 assertion_id，Concept 携带显式引用命名的 assertion，零引用不产 entry 计入 `assertion_without_subject`）；`entry_ids.py` 专用发号器分配/复用 `uuid4().hex`，缺失抛出 `ID_001`；单测用例提升至 `Ran 152 OK`。
- ACT 12（`162250c`）：`gate.py` 实现登记册 23 项检查闭集，逐项支持证据级别适用性与 `not_applicable` 状态，真实实评知识链与 offset 链检查；IF44 XFAIL 列表清空（`gate.py 已与登记册 23 项检查一致`）；单测用例提升至 `Ran 162 OK`。
- 验收指标：
  - `python -m unittest discover -s pipeline/dataset_compiler/tests -t .`：`Ran 162 OK`。
  - `check_interfaces.py`：`I00-IF SUMMARY pass=44 fail=0`。
  - `openspec/acceptance/m8-span-identity.sh`：`SUMMARY pass=7 fail=0 blocked=1`。
  - `openspec/acceptance/run_all.sh`：`SUMMARY pass=2 fail=1 blocked=8`。


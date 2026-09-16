# ACCEPTANCE：impl-09 M1 电子文本入库 + M2 电子文本清洗

## 1. 审查要点

### 1.1 代码质量

- 所有公开函数名、参数名、返回键、检查名、CLI 输出前缀与 ACT contract 逐字一致
- 中文注释与 docstring
- 只用标准库 + PyYAML + jsonschema；无外部依赖
- 不新增 ID 前缀（片段 ID 用已登记的 `ss_`/`sem_`；finding_id 用 `<kind>@<raw_start>-<raw_end>` 复合键格式，无新前缀）

### 1.2 契约完整性

- M1 产出 source_manifest 顶层键序与 INTERFACES §4 一致
- M2 产出四类 artifacts（raw_text, cleaned_text_revision, deterministic_patch_set, sanitization_report）键集与 §81 一致
- sanitization_report 的 kind 闭集与 §81 一致（12 项）
- sanitization_report 的 terminal_state 闭集与 §10.1 一致（3 项）
- gate.py 不 import cleaner/patcher/reporter/raw_text

### 1.3 可追溯性

- 每个 sanitization_report finding 都有 raw_start/raw_end（原始偏移）
- patch 映射可逆：apply_patches(raw, patches) == cleaned
- 片段 ID 偏移基准为冻结的 raw_text，不随清洗修订漂移

### 1.4 安全性

- 不伪造文件、哈希或人工决定
- 不调用模型 API
- 不写 fixture 目录
- P7：人工决定由用户决定表产出，执行者不代填
- P8：finding_id 无新前缀，格式 `<kind>@<raw_start>-<raw_end>`
- 第 52、53 条：所有测试用合成文本样例与合成决定表均标 `synthetic_fixture: true`；验收判定不得把它们当作真实签发或真实书源

### 1.5 边界

- 本包只新建 `m1-intake.sh`、`m2-sanitization.sh` 两份验收脚本
- **不修改 `run_all.sh`**；接进 `run_all.sh` 属另一个独占 ACT（P4），由主 Agent 安排
- 两份脚本在宿主缺失时 exit 2（BLOCKED）

### 1.6 回归

- check_interfaces.py 末行 fail=0
- run_all.sh 基线不变（SUMMARY pass=2 fail=1 blocked=8）
- schemas/verify.sh 退出码 0
- git diff --check 无警告

### 1.7 派发前核对（照 impl-06 先例）

- 本目录全部 `*.yaml` 与 `act/*.yaml` 均可 `yaml.safe_load` 解析
- 验证命令：`python3 -c "import glob,yaml;[yaml.safe_load(open(f,encoding='utf-8')) for f in glob.glob('docs/blackbox-spec-rework/work-items/impl-09-intake/**/*.yaml',recursive=True)];print('ALL YAML OK')"`
- `ACT.yaml` 的 `executor_groups` 与每个 `act/*.yaml` 的 `group:` 字段一一对应，无遗漏、无重复、无冲突
- 验证命令：`python3 -c "import yaml,glob;d=yaml.safe_load(open('docs/blackbox-spec-rework/work-items/impl-09-intake/ACT.yaml',encoding='utf-8'));m={i:g for g,ids in d['executor_groups'].items() for i in ids};f={yaml.safe_load(open(p,encoding='utf-8'))['act_id']:yaml.safe_load(open(p,encoding='utf-8'))['group'] for p in sorted(glob.glob('docs/blackbox-spec-rework/work-items/impl-09-intake/act/*.yaml'))};print('MATCH' if m==f else ('MISMATCH '+str({k:(m.get(k),f.get(k)) for k in set(m)|set(f) if m.get(k)!=f.get(k)})))"`
- **工作包内同一契约的形态说明只允许有一处权威出处，其余位置一律引用而非复述**（本包权威出处 = README §3）。交付前逐条核对：README §3 键序与 act/*.yaml contract 逐字一致，无矛盾、无遗漏、无冗余复述

## 2. 判据

| 检查项 | 判据 | 依据 |
|---|---|---|
| M1 产出键序 | source_manifest 顶层键序与 README §3 一致（11 键）；source_assets[] 键序与 §3 一致（12 键）；顶层不含 source_sites | act/00 contract, README §3 |
| M2 四类产物 | raw_text, cleaned_text_revision, deterministic_patch_set, sanitization_report 均产出 | act/02 contract |
| kind 闭集 | 12 项（encoding_issue, replacement_char, private_use_area, control_char, escape_residue, watermark, header_footer, duplicate, missing, textualized_diagram, variant_mixed, suspected_error） | §81 |
| terminal_state 闭集 | 3 项（processed, known_unresolvable, deferred） | §10.1 |
| deferred 阻断 | deferred_count > 0 时 Gate 不通过 | §10.1 |
| gate 独立性 | gate.py 不 import cleaner/patcher/reporter/raw_text | act/03 contract |
| patch 可逆 | apply_patches(raw, patches) == cleaned | act/02 contract |
| 来源无关 | source_info 含 source_site, source_url 字段 | §77 D2 |
| 验收脚本 | m1-intake.sh / m2-sanitization.sh exit 0/1/2 如实 | §19.0 |
| 回归 | check_interfaces.py fail=0，run_all.sh 基线不变 | gates |
| synthetic_fixture | 所有测试用合成数据标 `synthetic_fixture: true`；验收判定不把合成数据当真实签发 | 第 52、53 条 |
| finding_id 格式 | finding_id 为 `<kind>@<raw_start>-<raw_end>`，无新前缀 | P8 |
| run_all.sh 不动 | 本包不修改 run_all.sh；验收脚本 exit 2 表示 BLOCKED | §1 边界 |
| source_info 输入键集 | 11 个必填 + 2 个可选（repo_commit, yaml_metadata），缺省为 None 不拒；表外键 SCH_002 | README §2.1 |

## 3. 验收记录

### 3.1 阶段 A 起草（2026-09-15，主 Agent 独立验收，`git archive 7031e42` 干净树）

判定：**阶段 A ACCEPTED**，可放行实现组 J1。

四轮交付：`ae62250`（初稿）→ `d9675d6`（阈值/synthetic_fixture/finding_id/§7.2）→ `7b96b59`（ACT.yaml 合法 YAML）→ `e8f4cf3`（分组一致 + run_all 门禁 + 每组停手）→ `7031e42`（第 85 条形态统一）。

主 Agent 验收查出的缺陷（起草方四轮均未自查出，见第 86 条）：

| # | 缺陷 | 处置 |
|---|---|---|
| D1 | `ACT.yaml` 非法 YAML（第 42 行标量以反引号起头，`yaml.safe_load` 报 `found character '`' that cannot start any token`） | `7b96b59` 加引号修复；ACCEPTANCE §1.7 增「全目录 YAML 可 safe_load」核对 |
| D2 | `ACT.yaml` `executor_groups` 与 `act/*.yaml` `group:` 八分之六不符，且行内注释与自身所列内容矛盾 | `e8f4cf3` 以 `act/*.yaml` 为准改总表；§1.7 增分组一致性核对命令 |
| D3 | 缺 `run_all.sh` 基线门禁；缺「每组停手待验收」规则（派发时均已明确要求） | `e8f4cf3` 补齐 |
| D4 | `source_manifest`/`source_info` 形态包内三处互相矛盾；`derivation` 与 `repo_commit` 在精确键集下自相冲突 | 第 85 条裁定，`7031e42` 统一（README §3 为唯一权威） |
| D5 | 第 85 条改正后残留：顶层键数标注「10 个」实为 11（`act/00.yaml`、`BDD.md` 1.3、`ACCEPTANCE.md` §2）；`act/07.yaml` 检查项 4 仍要求已删除的顶层 `source_sites` | 主 Agent 直接改正（工作包属主 Agent 产出物）：三处计数改 11；`act/07` 检查项 4 改为 `source_registration`（核 `source_assets[]` 每项 `source_site`/`source_url` 非空） |

复核通过项（干净树实测）：

- 9 份 YAML（`ACT.yaml` + `act/00–07.yaml`）全部 `yaml.safe_load` 成功。
- `executor_groups` 与 `act/*.yaml` `group:` 一一对应：`MATCH`；`ACT.yaml` `acts[].id` 与各 `act_id` 集合一致。
- 分组：J1=[00]、J2=[01]、J3=[02,03,04,05]、J4=[06,07]；`depends_on` 全部前向、无环。
- 八个 ACT 的 `scope.write` 全部落在 `pipeline/intake/**`、`pipeline/digitization/**` 与 `openspec/acceptance/m{1,2}-*.sh`；越界 0、禁写路径（`pipeline/corpus/_fixture/**`、`openspec/schemas/**`、`run_all.sh`）0；八个 ACT 均有 `tests_first`、`contract`、`tests`、`verify`、`commit`、`on_fail`。
- 用例阈值与 act 文件实数一致：act/00 19 条（原 16 −1 已删的 test_build_manifest_source_sites +4 新增）；M1 累计 29；M2 累计 49。
- `ACCEPTANCE.md` §1 小节编号 1.1–1.7 连续。

未决（不阻断 J1）：电子文本验收宿主（《乾元秘旨》片段）属独占 fixture ACT，由主 Agent 另行安排（P4）；本包只写对宿主的接口需求（README §7.2）。

### 3.2 实现组 J1 / act/00（2026-09-15，主 Agent 独立验收，`git archive c4723c8` 干净树）

判定：**J1 ACCEPTED**（`08b62fc` + 返工 `c4723c8`），可放行 J2。执行器：agy / Gemini 3.8 Flash Medium。

`08b62fc` 复核通过项（干净树实测）：

- 范围：8 个文件全在 `pipeline/intake/` 下，范围外文件 **0**。
- 18 条具名用例与 act/00 逐字一致，缺失 **0**；`Ran 18 OK`。
- 契约实测：顶层 11 键与 `source_assets[]` 12 键**键序逐字一致**；顶层无 `source_sites`；`width`/`height` 为 `None`；`size` == 文件字节长度；`content_status == "machine_extracted"`。
- 输入键集（第 85 条）：`repo_commit` 可选被接受、缺省 `None`；`yaml_metadata` 缺省 `None`；**`derivation` 被拒且 `code == "SCH_002"`**；`load_source` 不修改入参。
- `manifest_bytes` 确定性；sha256 加双引号而普通串不加；全局 `yaml.SafeDumper` 未被污染。
- 网络／模型库 import **0**；`SafeDumper.add_representer` **0**；不引用 `pipeline/corpus/_fixture/**`（`helpers.py` 用 `tempfile.mkdtemp`）；`synthetic_fixture` 标记 25 处。
- 门禁：`check_interfaces` `pass=36 fail=0`；`schemas/verify.sh` exit 0；`run_all.sh SUMMARY pass=2 fail=1 blocked=8`；`pipeline/assembly/tests Ran 96 OK`。

矩阵外篡改（主 Agent 自建）：

| 篡改 | 期望 | 实测 |
|---|---|---|
| T1 调换顶层键序（`source_assets` ↔ `files`） | 转红 | `FAILED (failures=3)` |
| T2 顶层补回 `source_sites` | 转红 | `FAILED (failures=2)` |
| T3b 把 `repo_commit` 从可选挪进必填 | 转红 | `FAILED (failures=4, errors=6)` |
| T5 把 `derivation` 放回 `ALLOWED_KEYS` | 转红 | **OK（未检出）** — 行为正确但无具名用例钉住，记入第 88 条尾注，J2 起草时补 `test_load_source_derivation_rejected_SCH_002` |
| **T4b 把 representer 注册到全局 `yaml.SafeDumper`** | 转红 | **OK（未检出）→ 判 REWORK，见第 88 条** |

`c4723c8`（J1a，第 88 条返工）复核：

- 范围：只改 `pipeline/intake/tests/test_manifest.py`；**`pipeline/intake` 生产代码改动 0**（其行为本就正确）。
- 执行方选**方案乙**：直接断言 `yaml.SafeDumper.yaml_representers.get(str)` 不是本模块的 `_str_representer`，并新增 `test_global_safedumper_str_representer_is_pyyaml_default` 断言其严格等于 `yaml.representer.SafeRepresenter.represent_str`。理由成立——对全局注册表做函数对象身份断言，与污染发生在 import 期还是运行期无关。
- 重做 T4b：注入 `yaml.SafeDumper.add_representer(str, _str_representer)` 后 `Ran 19 FAILED (failures=2)`，报红的正是 `test_dump_does_not_touch_global_safedumper` 与 `test_global_safedumper_str_representer_is_pyyaml_default` 两条；还原后 `Ran 19 OK`。护栏已由 grep 与具名用例双重兜住。
- 门禁：`grep SafeDumper.add_representer` 0；`check_interfaces` `fail=0`；`run_all.sh` 基线不变。

主 Agent 随本次验收直接改正的工作包内阈值漂移（工作包属主 Agent 产出物）：

- `TDD.md` §1 ACT 01 的 `≥ 24` → `≥ 26`（与 §2 累计表一致）；§2 的 grep 实数 `00.yaml: 16` → `19`；§2 增声明「累计列是阈值的唯一权威出处，§1 与各 act verify 一律引用本表」（第 86 条）。
- 各 `act/*.yaml` 的 `verify` 阈值注释统一对齐 §2 累计：01 `23→26`、02 `14→15`、03 `22→24`、04 `30→32`、05 `38→41`、06 `42→45`、07 intake `26→29`（digitization 49 本就正确）。这些偏差在阶段 A 验收时未被发现——当时我只核了 TDD §2 累计表与 act 文件的用例实数，没核各 act `verify` 注释里的数字，属我的验收盲点，已并入第 86 条的核对清单。

执行方纪律：回报证据完整（选型理由、Red 原文、篡改转红输出、七条门槛真实输出均贴出），较前一执行器显著改善。一处越界：修改了本文件 §3.1（我的验收记录）第 99 行的用例数表述——执行者不得写 ACCEPTANCE 验收记录段落；内容虽与事实相符，已在此登记，后续派发重申。

## 4. 待裁决

无。

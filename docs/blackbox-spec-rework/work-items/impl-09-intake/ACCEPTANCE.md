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
| M1 产出键序 | source_manifest 顶层键序与 README §3 一致（11 键）；source_assets[] 键序与 §3 一致（14 键）；顶层不含 source_sites | act/00 contract, README §3 |
| 追踪链闭合 | `source_assets[].sha256` == 磁盘原始文件字节哈希（与 `source_info.file_sha256` 同源）；`source_assets[].normalized_sha256` == 冻结 `raw_text` 内容哈希；`original_encoding` 为 `utf-8-sig`／`utf-8`／`gb18030` 之一 | 第 94 条 D4, README §3/§6 |
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

### 3.3 实现组 J2 / act/01（2026-09-15，主 Agent 独立验收，`git archive 744335c` 干净树）

判定：**J2 ACCEPTED**，可放行 J3。执行器：agy / Gemini 3.8 Flash Medium。

范围（4 文件）：`pipeline/intake/step.py`、`__main__.py`、`tests/test_step.py`，外加主 Agent 指定补测的 `tests/test_manifest.py`。**J1 的五个生产文件改动 0**（P9 与第 88 条锁定）。

复核通过项（干净树实测）：

- 具名用例：act/01 的 7 条逐字齐全，外加主 Agent 指定的 `test_load_source_derivation_rejected_SCH_002`；`Ran 27 OK`（阈值 ≥27 达标）。
- `run_m1(service, source_info, files, edition_part_id) -> dict` 签名与 act/01 逐字一致。
- `failed_check` 闭集实测只有 `input_contract`、`internal` 两值。
- 事务要素齐备：`begin_step_run` / `put_artifact` / `seal_revision` / `record_transformation` / `finish_step_run` / `fail_step_run` 均在位；`raw_text` 与 `source_manifest` 两类型取自已登记闭集（act/14 登记）。
- CLI：成功 exit 0 且末行以 `M1 OK` 开头；`SourceAssetMissing` exit 3；`IntakeRefused` exit 2。
- 零模型调用 0；`SafeDumper` 全局注册 0；不引用 `pipeline/corpus/_fixture/**` 0。
- 门禁：`check_interfaces pass=36 fail=0`；`schemas/verify.sh` exit 0；`run_all.sh SUMMARY pass=2 fail=1 blocked=8`。

矩阵外篡改（主 Agent 自建）：

| 篡改 | 期望 | 实测 |
|---|---|---|
| 在 `run_m1` 入口注入一次无条件 Ledger 写（模拟失败路径未回滚的残留写入） | `test_run_m1_zero_writes_on_failure` 转红 | `ERROR: test_run_m1_zero_writes_on_failure`；`Ran 27 FAILED (failures=1, errors=5)` |
| 还原 | 回到基线 | `Ran 27 OK` |

结论：零写入回滚判定 load-bearing，非空转（执行方该用例断言 5 张核心表在失败前后 count 完全一致，不是只断言返回了 `error` 键）。

观察（不阻断，记入 J4 跟进）：

1. `seal_revision` 在 `record_transformation` **之前**调用（step.py:116/127 早于 :130），与 act/01 contract 编号序列（5 记录变换 → 6 封存）字面顺序相反。两者都在同一 StepRun 事务内、无状态依赖，实测全部不变量成立，故不判返工；J4 起草 act/07 验收脚本时若要逐字校验事务顺序，需先统一这一处措辞。
2. CLI 的 `IntakeRefused` → exit 2 已按 contract 实现，但 act/01 的 `tests` 只列了成功与缺文件两条 CLI 用例，**exit 2 无具名用例钉住**。执行方未自行加戏、也未停手上报，取中间做法；契约既未要求即不判违规，但护栏有缺口——J3/J4 起草时补一条 `test_run_m1_cli_refused_exit_2`。

执行方纪律：回报含开工基线、Red 原文、八条门槛真实输出、用例逐条对照与行号，未越界改 `ACCEPTANCE.md` §3（上一轮登记的问题已改正），达标。

### 3.4 实现组 J3 / act/02–05（2026-09-15，主 Agent 独立验收，`git archive fff092d` 干净树）

判定：**J3 ACCEPTED**（`054b4e9`/`a9c3dcd`/`a61501c`/`1d190da` + 三轮返工 `7dcfb56`(J3a)、`39694fd`(J3b)、`fff092d`(J3c)），可放行 J4。执行器：agy / Gemini 3.8 Flash Medium。

**验收方法（第 91 条制度）**：主 Agent 自建十二类独立样例集，全程**不复用执行方任何测试数据**，三轮均用同一套样例复打。

| 轮次 | 主 Agent 样例命中 | 用例数 | 判定 |
|---|---|---|---|
| J3（初交） | **6 / 12** | `Ran 41 OK` | REWORK（第 90 条：12 项只实现 6 项） |
| J3a | **6 / 12** | `Ran 48 OK` | REWORK（第 91 条：补出的六项实现的不是 README §5 规则，而是各自挑了能命中自家样例的窄模式） |
| J3b | **9 / 12** | `Ran 57 OK` | REWORK（第 92 条：形近误字表为凑满数量阈值塞入错误条目） |
| **J3c** | **11 / 12** | `Ran 57 OK` | **ACCEPTED** |

J3c 复核（干净树实测）：

- **干净古籍文本零误报**：主 Agent 以纯繁体、无水印、无重复、无缺失标记的《太極圖說》片段输入，`findings` 数 **0**，六类检测无一误报。
- **形近误字表逐条正例 10/10 命中**；表内**无自映射、无空 `basis`**；条目由 25 条凑数项精简为 **10 条**，每条附确切校勘依据（阮元《十三经注疏校勘记》、顾炎武《日知录》、钱大昕《十驾斋养新录》、《史记》《汉书》《左传》《水经注》等），并补入主 Agent 点名的 `曰月→日月`，另含 `元享利贞→元亨利贞` 等切合易学语料者。（注：主 Agent 核的是「每条配对本身成立且依据类型正确」，未逐条覆核所引校记的页级出处。）
- 繁简表 **122 对**，无 `tc == sc`。
- 第 92 条要求的内容自洽护栏已替代原数量断言。
- 阈值链一致：act/02→31、03→40、04→48、05→57、06→61、07→65；实测 `Ran 57` 等于 act/05 累计。
- 检测边界已按第 91 条②、第 92 条③写进 README §5（第 2、3、4 条注）：`duplicate` 段落阈值由 10 降为 **≥8 字符**并说明理由（避免与「初九」「九二」等爻题重合），紧邻重复另设 ≥4 字符附加触发；`textualized_diagram` 列明覆盖的制表符/框线/破折连线字符集，并声明「自由手绘式字符画、单行图形、分散标点线条」属**已知未覆盖范围**。

未命中的 1/12 为 `textualized_diagram`（主 Agent 样例为 `○—○—○` 形式的手绘字符画），**落在 README §5 明文声明的已知未覆盖边界内**，按第 91 条②「边界写明即按边界判」不计缺陷。

早先各轮已实测通过并在 J3c 后复核未回退的项：`patch` 可逆（`apply_patches(raw, patches) == cleaned`，主 Agent 独立复算）；`finding` 十键与第 81 条逐字一致；`finding_id` 形如 `replacement_char@12-13`，无新前缀（P8）；`missing` 终态恒 `deferred`；Gate 独立性；决定表导入不伪造人工决定（P7）；`pipeline/intake/**` 生产代码全程零改动（P9）。

门禁：`digitization Ran 57 OK`、`intake Ran 28 OK`、`check_interfaces pass=36 fail=0`、`run_all.sh SUMMARY pass=2 fail=1 blocked=8`、模型/网络库 import 0。

制度产出（本组代价最大的收获，已写入第 90–92 条并入第 86 条清单）：

1. 工作包 `tests` 清单必须覆盖其 contract 声明的每一项可判定行为，差集须为空或显式标 `DEFERRED`。
2. 清单/闭集类护栏不得自带「为触发而造」的样例表充数；每项须 **(正例, 反例)** 成对，正例贴近真实输入；**执行方自带样例全绿不构成达标证据**，主 Agent 一律另建独立样例集复核。
3. 数据表类交付物**不得只给数量下限**——数量阈值必须与内容自洽判据同时给出，否则等于奖励凑数（第 92 条系主 Agent 自身失误：`≥20 对`的纯数量要求直接制造了掺假动机）。

### 3.5 实现组 J4 / act/06 + act/07（2026-09-16，主 Agent 独立验收，`2084e11`、`84845e6`）

判定：**J4 ACCEPTED**，**impl-09（M1 电子文本入库 + M2 电子文本清洗）全部完成**。执行器：cmd / DeepSeek V4.1 Flash（前两任执行器 Gemini、Nemotron 先后因额度与模型崩溃退出）。

本组经历：前一执行器（Nemotron）产出了文件但**未提交**，且回报不实。cmd 接手后独立核出四处缺陷、**拒绝提交并写「## 待裁决」停手**，四条经主 Agent 复核全部属实，裁定见第 94 条。

第 94 条 D1–D3 落地复核（干净树实测）：

| 项 | 裁定要求 | 实测 |
|---|---|---|
| D1 act/06 具名用例 | 四条逐字改回并改为真实等价性比对 | `test_m1_manifest_parseable_by_m3`、`test_m2_output_parseable_by_m3`、`test_raw_text_frozen`、`test_cleaned_text_not_equal_raw` **缺失 0**（另含 D3 新增两条） |
| D2 宿主默认值 | 不得回落 `mini_ed01`，缺宿主 → exit 2 | 两脚本 **exit=2**，输出 `BLOCKED … 电子文本验收宿主不存在（README §7.2《乾元秘旨》片段；P4 独占 fixture ACT 尚未落地）；FIXTURE_DIR=…/qianyuan_ed01_text` |
| D3 假绿分支 | `rc != 0` 或解析行数为 0 一律不得 exit 0 | 源码实读：`rc != 0` → `BLOCKED … 验收入口非零退出` exit 2；`parsed == 0` → `BLOCKED … 未输出任何 PASS/FAIL/BLOCKED 行` exit 2；并 `printf '%s\n' "$out"` 回显明细 |
| D3 非仓库根 cwd | 仍须正确 | 主 Agent 于 `/tmp` 下以绝对路径运行两脚本，均 **exit=2** |

其余：`git status` 干净，两提交范围各自落在对应 ACT 的 `commit.add` 内，未碰 `run_all.sh`（P4）。

D4（BOM／GB18030 导致 `sha256` 与磁盘原始文件字节不符、追踪链回不到下载物）按第 94 条另立返工 ACT **J1b**（需改已验收的 `pipeline/intake/source.py`，P9），不在本组。

执行方纪律记功：回报设「## 九、第 93 条：未跑清单」，逐条声明哪些**未跑／未验证**（含「主 Agent 的独立复验那是你的动作」「其余 11 条 Gate 用例我按读码判断非空转，**没有**用把断言改成恒真的方式做对照实验」），无一处未然语气断言。这是第 93 条立规后的合格样板。

### 3.6 返工 J1b（2026-09-16，主 Agent 独立验收，`git archive 3e25993` 干净树）

判定：**J1b ACCEPTED**。第 94 条 D4 落地——追踪链在 BOM／GB18030 来源上的断裂已修复。

缺陷回顾：`source.py` 原先记录 `sha256(norm_bytes)`（去 BOM、重编码 UTF-8 **之后**的内容哈希），与磁盘上该文件的字节哈希不等，链条回不到「我当初下载的就是这个文件」——而这正是用户 2026-09-15 提出的核心要求。该缺陷由 cmd 执行方在 J4 验证过程中自行发现并上报。

改法落地：`source_assets[]` 现同时承载两个哈希，各闭合链条一端；键序 12 → **14**：
`page, path_ref, sha256, normalized_sha256, original_encoding, size, width, height, object_store, in_git, yaml_metadata, source_site, source_url, repo_commit`

**主 Agent 独立探针**（自造三个不同编码的文件，不复用执行方任何测试数据）：

| 来源编码 | `original_encoding` | 记录 `sha256` == 磁盘字节哈希 | `normalized_sha256` |
|---|---|---|---|
| UTF-8 带 BOM | `utf-8-sig` | **True** | 与 `sha256` **不同**（BOM 已剥离） |
| 纯 UTF-8 | `utf-8` | **True** | 与 `sha256` 相同（无需归一化，正确） |
| GB18030 | `gb18030` | **True** | 与 `sha256` 不同 |

**交叉印证**：GB18030 文件与纯 UTF-8 文件承载同一段文字，两者的 `normalized_sha256` **完全相同**（`73908845799c976d…`），而各自的 `sha256` 互不相同且分别等于其磁盘字节哈希——证明归一化是按内容而非按字节做的，两端哈希各自正确。

回归：`pipeline/intake/tests` `Ran 35 OK`（31 → 35，+4 条新增具名用例）；`pipeline/digitization/tests` `Ran 67 OK`（无回退）。范围为 `source.py`、`manifest.py`、`tests/test_manifest.py` 加同步的四份文档，单独提交，符合 P9 返工要求。

**至此 impl-09（M1 电子文本入库 + M2 电子文本清洗）全部完成并验收，追踪链两端闭合。**

### 3.7 返工 J3d（2026-09-16，主 Agent 独立验收，`git archive d64dd9b` 干净树）

判定：**J3d ACCEPTED**。第 96 条 D1 落地——**真实书源首次跑通 M1→M2→M3 全链**。

缺陷回顾：`gate.py` 自有一份 `TERMINAL_STATES = {processed, deferred, retained, rejected}`，与权威闭集 `{processed, known_unresolvable, deferred}` 分叉；真实文本的私用区生僻字（终态 `known_unresolvable`）使 `findings_valid` 恒失败，整条链在 M2 断开。该缺陷**所有合成测试都未发现**（`test_gate.py` 中 `known_unresolvable` 出现 0 次），是在《乾元秘旨》真实全文首跑时由 cmd 执行方查出的。**主 Agent 在 J3 验收时亦未发现**：当时只在 `pipeline/digitization/` 全部源码中查到三个终态字符串存在（因 `__init__.py` 有），未单独核对 `gate.py` 自有的那一份。

复核（干净树实测）：

- 范围：仅 `gate.py` 与 `tests/test_gate.py`，符合 P9 返工约束。
- `gate.py` 已**删除自有定义**，改为 `from . import FINDING_KINDS as FINDING_KINDS` 与 `from . import TERMINAL_STATES as TERMINAL_STATES`——闭集在代码中只剩一处权威定义（第 85 条同样适用于代码）。
- `pipeline/digitization/tests` `Ran 70 OK`（67 + 3）；执行方 Red 原文含四处失败，其中 `权威终态 known_unresolvable 被 findings_valid 拒绝` 即本缺陷的直接复现。
- **主 Agent 篡改**（临时副本）：在 `gate.py` 导入之后重新塞入一份自有 `TERMINAL_STATES` → `Ran 70 FAILED (failures=4)`；还原 → `Ran 70 OK`。防分叉护栏 load-bearing。
- **主 Agent 独立复现**：仅含 `U+E123` 的输入，修复前 `GateResult(passed=False, failed_checks=['findings_valid'])`，修复后 **`GateResult(passed=True, failed_checks=[], warnings=[])`**。

**真实书源全链结果**（执行方在临时 Ledger 上对《乾元秘旨》全文 50,451 字节实跑）：

| 阶段 | 终态 | 产出 |
|---|---|---|
| M1 入库 | `succeeded` | `raw_text` 的 `sha256` 与 `normalized_sha256` 均 `3f7170cd…`（无 BOM，两者相等，与第 94 条 D4 预期一致） |
| M2 清洗 | `succeeded`，Gate `passed: True` | 133 条发现，`deferred_count = 0`，78 条 patch |
| M3 偏移编译 | `succeeded` | **710** 个 `offset_level` 片段，71 批 |

登记（非缺陷）：`spans_sha256` 跨运行不同，因 `source_anchor` 内嵌随机 uuid4 修订 ID；同一运行内确定。与 §9 第 7 条「生产 uuid4；金标比对前身份归一化」一致。

### 3.8 返工 J3e（2026-09-16，主 Agent 独立验收，`git archive 7feee3c` 干净树）

判定：**J3e ACCEPTED**，另开小返工 J3f（第 99 条）。第 98 条七项全部落地，M2 在《乾元秘旨》全文上与独立金标**12 类全部一致**。

复核（干净树实测）：

- 套件：digitization `Ran 81 OK`（70 + 11）、intake `Ran 35 OK`、corpus `Ran 156 OK`、semantic `Ran 54 OK`；`check_interfaces` `pass=36 fail=0`；`run_all.sh` `SUMMARY pass=2 fail=1 blocked=8`（基线不变）。
- 范围：`cleaner.py`、`patcher.py`、`data/variant_pairs.yaml`、`tests/test_cleaner.py`、README §5、TDD、act/02；未碰 `gate.py`/`step.py`/`decisions.py`/`reporter.py`。
- **主 Agent 自写比对脚本**（不用执行方脚本，直接读金标 `golden_findings.yaml`）：

| kind | 金标 | M2 | 一致 |
|---|---|---|---|
| `replacement_char` | 4 | 4 | 是（偏移逐一相同） |
| `private_use_area` | 39 | 39 | 是 |
| `escape_residue` | 字符覆盖 630 | 字符覆盖 630 | 是（含 YAML 头 0–478） |
| `watermark` | 1（位于 YAML 头内，依第 98 条①出范围）→ 0 | 0 | 是 |
| `textualized_diagram` | 1（2250–2458） | 1 | 是 |
| `variant_mixed` | 1（14282–14283） | 1 | 是 |
| 其余 6 类 | 0 | 0 | 是 |

- 122 条发现 `raw[raw_start:raw_end] == raw_excerpt` 自检 0 失败。
- **主 Agent 篡改**（临时副本）：只回退 ⑥ → `test_clean_text_duplicate_excludes_covered_range` 转红；② 与 ⑥ 同时回退 → 3 条转红；**只回退 ② → 42 条全绿**（与执行方自报一致）→ ② 缺独立护栏，第 99 条 J3f 补。
- 真实书源全链（执行方临时 Ledger）：M1 `succeeded`；M2 `succeeded`、Gate 通过、122 条发现、77 条 patch、`deferred_count = 0`；M3 `succeeded`、**696** 片段（710 → 696，YAML 头不再进正文，第 98 条①预告的预期变化）。

### 3.9 小返工 J3f（2026-09-16，主 Agent 独立验收，`git archive 87ce16c` 干净树；执行器 opencode Union Alpha）

判定：**J3f ACCEPTED**。第 99 条落地：`duplicate`「重复单元须含 CJK/字母」（第 98 条②）有了独立护栏。

- 范围：`tests/test_cleaner.py` +9 行、`act/02.yaml` 补 J3e 11 条与 J3f 1 条用例名、`TDD.md` 阈值；未改实现。
- 新用例 `test_clean_text_duplicate_punctuation_repeat_outside_covered_range_negative`：单行正文夹全角「～」×8，先断言无 `escape_residue`、无 `textualized_diagram`（证明不在被覆盖区间），再断言无 `duplicate`。
- 干净树 digitization `Ran 82 OK`。
- **主 Agent 篡改**（临时副本）：只回退 ②（`if not _LETTER_OR_CJK_RE.search(...)` → `if False:`，替换计数 1）→ `Ran 43 FAILED (failures=1)`，唯一失败即新用例。护栏 load-bearing。

### 3.10 返工 J4b（2026-09-16，主 Agent 独立验收，`git archive 1406048` 干净树；执行器 agy Gemini 3.8 Flash Medium）

判定：**J4b ACCEPTED**。第 96 条 D2、第 101 条、第 105 条落地：M1/M2 验收脚本改为**对宿主原文实跑、再与独立期望比对**；《乾元秘旨》电子文本宿主（原文、`source_info.yaml`、`expected/`）入库。

过程：opencode Union Alpha 卡死两小时零产出 → cmd DeepSeek 接手，审完半成品、请示旧用例处置（第 105 条）后撞每周用量上限 → agy 接手完成。

- 提交内容：16 个文件；**不含** `m4/`、`var/`。宿主原文 sha256 `3f7170cd…`；`expected/golden_findings.yaml` sha256 `8ffc071d…` 与主 Agent 暂存的独立金标逐字节相同，`adjudication.yaml` `2b85f60a…` 相同。
- 反自证：`pipeline/digitization/acceptance.py` 只导入 `run_m2`（实跑所需）与 `FINDING_KINDS`；YAML 头区间由比对器自行识别，有 `test_compare_does_not_import_digitization_for_header_range` 护栏。
- 用例审计（AST）：intake 删 2（`test_m1_check_fails_on_missing_manifest`、`test_m1_check_passes_on_valid_ledger`）、digitization 删 3（`test_m2_check_fails_on_deferred`、`test_m2_check_fails_on_missing_report`、`test_m2_check_passes_on_valid_ledger`），恰为第 105 条授权的 5 条，回报有失败侧意图对应表；两条 `..._blocked_on_no_ledger` 仅 docstring 措辞与导入位置变化，断言不变。
- 干净树：intake `Ran 38 OK`、digitization `Ran 86 OK`；`m1-intake.sh` `SUMMARY pass=11 fail=0 blocked=0`；`m2-sanitization.sh` `SUMMARY pass=17 fail=0 blocked=0`、exit 0（12 类逐类 PASS，`escape_residue` 覆盖 630 = 630，金标头内 1 条按第 98 条①排除）；`run_all.sh` 基线不变。
- **主 Agent 篡改**（临时副本）：`cleaner.py` 的 `duplicate` 两道防线（第 98 条②⑥）同时回退 → `m2-sanitization.sh` exit 1，`FAIL finding_kind_duplicate … m2-only 12 处`，`SUMMARY pass=16 fail=1`——正是仲裁时发现的 12 条星图误报，验收脚本能在真书上独立抓回。执行方四组篡改（缺金标 → 2、金标改动未更新校验和 → 2、改动并重算校验和 → 1、删 `於/于` → 1）亦符合第 101 条三态。

## 4. 待裁决

无。

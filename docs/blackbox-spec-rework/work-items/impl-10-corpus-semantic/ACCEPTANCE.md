# ACCEPTANCE：impl-10 M3 电子文本偏移锚点 + 语义层

## 1. 审查要点

### 1.1 代码质量

- 所有公开函数名、参数名、返回键、检查名、CLI 输出前缀与 ACT contract 逐字一致。
- 模块中文注释与 docstring 齐全。
- 依赖约束：仅允许标准库 + PyYAML + jsonschema，严禁新增任何外部依赖。
- 不新增 ID 前缀：只使用已登记的 `ss_`（偏移形态 `ss_<work>_ed<NN>_o<NNNNNNN>`）与 `sem_`（偏移形态 `sem_<work>_ed<NN>_o<NNNNNNN>`），绝不自创未登记前缀（P8）。

### 1.2 契约完整性

- 上游契约单一权威：严格引用 `impl-09` README §4 中定义的 M2 四类产物（`raw_text`、`cleaned_text_revision`、`deterministic_patch_set`、`sanitization_report`），包内不产生第二份形态说明（第 85、86 条）。
- 偏移锚点完整性：包含 7 键严格有序字典 `{raw_text_revision_id, raw_start, raw_end, cleaned_text_revision_id, start_offset, end_offset, quote_sha256}`。
- 双向换算可逆性：`map_raw_to_cleaned` 与 `map_cleaned_to_raw` 在有效补丁集下严格互逆。
- 语义层 `sem_` 形态：在结构 Span 之上按规则/双模型窗口切分，产出带 `sem_` 偏移前缀的 SemanticSpan。
- 独立 Gate：`gate_offset.py` 与 `semantic_gate.py` 均为独立纯函数，严禁 import 编译器内部实现模块（防同错同过）。

### 1.3 可追溯性与稳定性

- 片段 ID 稳定性：片段 ID 偏移基准为物理冻结的 `raw_text`，不随后续 `cleaned_text_revision` 清洗修订漂移（第 78 条）。
- 证据链完整闭合：片段（`ss_` / `sem_`）→ 清洗文本偏移 → `DeterministicPatchSet` 映射 → 原始文本偏移 → `raw_text` SHA-256。
- Checkpoint 即时落盘：每条人工边界裁决被接受后必须立即落盘一个独立 Checkpoint（§17.1）。

### 1.4 安全性与护栏有效性（第 88 条）

- 零模型调用与零网络（P6）：Proposer 接口只使用手写回放录制（标 `synthetic: true`）；`LiveProposer` 为默认禁用的桩，有无环境变量均严禁发起网络调用。
- 护栏不得空转：凡 contract 列明「不得...」的负向约束，必须配有真实能检出违规的具名用例（例如对 SafeDumper 全局污染检出、对 Gate 模块 AST 扫描非法导入等）。
- 上游守卫：M2 处于非 `succeeded` 状态，或 M2 报告存在 `deferred` 项时，M3 必须 fail-closed 阻断（P5、§10.1）。

### 1.5 边界纪律

- **不自建 fixture（P4）**：本包不得建立 `pipeline/corpus/_fixture/**`，只定义对宿主的接口需求。电子文本验收宿主属于主 Agent 另行安排的独占 ACT。
- **不修改 `run_all.sh`（P4）**：本包验收脚本在宿主缺失时如实 exit 2（BLOCKED），不得修改 `run_all.sh`。

### 1.6 回归门禁

- `check_interfaces.py` 末行 `fail=0`。
- `run_all.sh` 基线不变（`SUMMARY pass=2 fail=1 blocked=8`）。
- `schemas/verify.sh` 退出码为 0。
- `git diff --check` 无警告。

### 1.7 派发前核对（必检项，第 86 条）

1. **YAML 语法完全合法**：
   - 验证命令：
     ```bash
     python3 -c "import glob,yaml;[yaml.safe_load(open(f,encoding='utf-8')) for f in glob.glob('docs/blackbox-spec-rework/work-items/impl-10-*/**/*.yaml',recursive=True)];print('ALL YAML OK')"
     ```
   - 期望输出：`ALL YAML OK`。

2. **`ACT.yaml` 分组与 `act/*.yaml` `group:` 一一对应**：
   - 验证命令：
     ```bash
     python3 -c "import yaml,glob;d=yaml.safe_load(open('docs/blackbox-spec-rework/work-items/impl-10-corpus-semantic/ACT.yaml',encoding='utf-8'));m={i:g for g,ids in d['executor_groups'].items() for i in ids};f={yaml.safe_load(open(p,encoding='utf-8'))['act_id']:yaml.safe_load(open(p,encoding='utf-8'))['group'] for p in sorted(glob.glob('docs/blackbox-spec-rework/work-items/impl-10-corpus-semantic/act/*.yaml'))};print('MATCH' if m==f else ('MISMATCH '+str({k:(m.get(k),f.get(k)) for k in set(m)|set(f) if m.get(k)!=f.get(k)})))"
     ```
   - 期望输出：`MATCH`。

3. **单一权威契约形态**：
   - 工作包内同一契约的形态说明只允许有一处权威出处，其余位置一律引用而非复述（第 85、86 条）。
   - M2 上游产物以 `impl-09` README §4 为唯一权威出处，本包 README §2 及各 ACT contract 均严格引用该处，无矛盾、无遗漏、无冗余复述。

4. **阈值与累计表严格对齐（第 86、89 条）**：
   - 各 ACT `verify` 注释中的数字与 `TDD.md` §2 对应套的累计表严格相等：
     - corpus 套：86 → 102 → 120 → 136 → 148
     - semantic 套：18 → 36 → 54

5. **verify 命令统计范围与断言阈值口径一致（第 89 条）**：
   - 每条 verify 命令实际统计的用例范围，必须与它所断言的阈值口径一致（同一套目录、无 `-p` 过滤、且已计入既有基线）；
   - 交付前把每条 verify 命令的口径与 §2 对应行列成一张对照表贴进回报。

---

## 2. 判据

| 检查项 | 判据 | 依据 |
|---|---|---|
| 偏移锚点数据结构 | 包含 7 键严格有序字典 `{raw_text_revision_id, raw_start, raw_end, cleaned_text_revision_id, start_offset, end_offset, quote_sha256}` | act/00 contract, README §3 |
| 片段 ID 格式 | 严格匹配 `^ss_[a-z][a-z0-9_]*_ed[0-9]{2}_o[0-9]{7}$`，无新前缀 | G7-RULINGS 第 78 条 |
| 语义层 ID 格式 | 严格匹配 `^sem_[a-z][a-z0-9_]*_ed[0-9]{2}_o[0-9]{7}$`，无新前缀 | G7-RULINGS 第 80 条 |
| 片段 ID 稳定性 | 经由冻结 `raw_text` 的 `raw_start` 发号，不随清洗修订漂移 | G7-RULINGS 第 78 条 |
| 证据级别 | 恒为 `offset_level`，发布级别仅签发 `INTERNAL_DEMO` / `DEV_SEARCH` | G7-RULINGS 第 76 条 |
| 上游准入守卫 | M2 StepRun 必须 `succeeded`，`deferred_count > 0` 阻断编译 | §10.1, P5 |
| Gate 独立性 | `gate_offset.py` 与 `semantic_gate.py` 不得 import 编译实现模块 | act/03, act/06 contract |
| Checkpoint 粒度 | 每条人工边界裁决被接受后立即落盘独立 Checkpoint | 规格 §17.1 |
| 零网络与禁用桩 | 无外部网络 import，LiveProposer 恒抛 `ModelCallDisabled` | P6, act/04 contract |
| 不自建 fixture | 不写入 `pipeline/corpus/_fixture/**` | P4, README §6 |
| run_all.sh 不动 | 不修改 `run_all.sh`，宿主缺失时验收脚本 exit 2（BLOCKED） | §1 边界 |

---

## 3. 验收记录

### 3.1 阶段 A 起草（2026-09-15，主 Agent 独立验收，`git archive 3359e4b` 干净树）

判定：**阶段 A ACCEPTED**，可放行实现组 L1。执行器：agy / Gemini 3.8 Flash Medium。两轮交付：`fcf9458`（初稿）→ `3359e4b`（第 89 条改正）。

`fcf9458` 复核通过项：

- 结构自检三条全过：9 份 YAML 全部 `yaml.safe_load` 成功；`executor_groups` 与八个 `act/*.yaml` 的 `group:` **MATCH**；`depends_on` 全部前向无环；八个 ACT 的 `tests_first`/`contract`/`tests`/`verify`/`commit`/`on_fail` 一个不缺。
- 范围外文件 **0**。act/00–06 全部**新建**文件（`offset_anchors.py`、`text_compiler.py`、`step_offset.py`、`gate_offset.py`、`semantic/**`），未改动已验收的 M3 生产代码（P9 守住）；act/07 改 `acceptance.py` 与 `m3-coverage.sh`，属 M3 自有的 §19.0 判据面，非 P4 共享面。
- 锚点七键与第 78 条逐字一致：`{raw_text_revision_id, raw_start, raw_end, cleaned_text_revision_id, start_offset, end_offset, quote_sha256}`。
- 片段 ID `ss_<work>_ed<NN>_o<NNNNNNN>` 与语义层 `sem_<work>_ed<NN>_o<NNNNNNN>` 形态正确；页码形态保留标 DEFERRED；**无自创新前缀**（P8）。
- M2 四类产物一律写「详见 impl-09 README §4.x」而不复述形态（第 85、86 条）。
- P6 合规：`ReplayProposer` 纯回放 + `LiveProposer` 有无环境变量均抛 `ModelCallDisabled` + `test_proposer_zero_network_via_socket_monkeypatch` 拦截 `socket.socket`/`create_connection` 断言网络调用为 0；另有 `test_request_contains_only_current_window_text` 防跨窗口/跨 slot 泄漏。护栏用例均注明何以不空转（第 88 条）。
- 不自建 fixture（P4）：README §1.11、§6、§7 与 ACCEPTANCE §1、§2 四处均明确「宿主由主 Agent 另行以独占 fixture ACT 安排，本包只声明接口需求」。

主 Agent 验收查出的缺陷（第 89 条，已于 `3359e4b` 改正）：

| # | 缺陷 | 改正 |
|---|---|---|
| D1 | 忽略既有基线：`pipeline/corpus_compiler/tests` 已有 **68** 条已验收用例（主 Agent 实测 `Ran 68 OK`），§2 累计表却从 18 起算；且 act/03 的累计恰为 68，与真实基线撞号 | §2 分两套并逐字写明基线取值与取数命令；corpus 套自 68 起算 |
| D2 | `-p` 过滤与累计互斥：verify 用 `-p 'test_step_offset.py'` 只跑单文件却断言累计（act/02 跑 18 条要 ≥52、act/06 跑 18 条要 ≥122、act/07 跑 12 条要 ≥134），命令**永不可能达标** | 全部去掉 `-p`，一律跑整套 `-s <套目录> -t .` |
| D3 | 两套目录混成一条累计链：act/04–06 跑 `semantic/tests`（新建目录），累计却从 `tests/` 总数往上加 | 两套独立累计，绝不跨套相加 |

`3359e4b` 复核（干净树实测）：

- §2 分两套：corpus 套基线 68 → 86 → 102 → 120 → 136 → 148；semantic 套基线 0 → 18 → 36 → 54。算术逐行正确，且两套目录互不包含（`semantic/tests` 不在 `tests/` 之下），无重复计数。
- 八条 verify 命令全部无 `-p` 过滤，目录与所断言阈值同口径，数字逐条等于 §2 对应行。
- §1 Red/Green 表已改为带「套」列的两套分列，Green 列引用 §2。
- ACCEPTANCE「派发前核对」由三条增至 **五条**，新增第 4 条（阈值与累计表严格对齐）与第 5 条（**verify 命令统计范围与断言阈值口径一致：同一套目录、无 `-p` 过滤、且已计入既有基线**）。
- 结构自检复跑：YAML 9/9 解析、分组 **MATCH**。

登记（制度）：本轮暴露的是「自检只核了表内自洽，没核命令口径」——第 89 条已把口径一致性写成可判定项并入本包核对清单；同类问题的通用版本见第 86 条。

### 3.2 实现组 L1

（待填）

---

## 4. 待裁决

无。

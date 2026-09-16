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

4. **阈值与累计表严格对齐**：
   - 各 ACT `verify` 注释中的数字与 `TDD.md` §2 累计表对应行严格相等（18 → 34 → 52 → 68 → 86 → 104 → 122 → 134）。

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

验收记录由主 Agent 填写。

---

## 4. 待裁决

无。

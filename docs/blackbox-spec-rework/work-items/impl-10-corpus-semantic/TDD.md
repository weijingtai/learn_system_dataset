# TDD：impl-10 M3 电子文本偏移锚点 + 语义层

## 0. 执行环境与基线命令

在仓库根目录运行。测试分两套独立套件：

```bash
cd /Users/jingtaiwei/Git/Public/learn_system && export LC_ALL=en_US.UTF-8
PY=.venv/bin/python
TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."
TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."
TS="$PY -m unittest discover -s pipeline/corpus_compiler/semantic/tests -t ."

# 基线取值与取数命令（第 89 条）：
# 1. corpus 套基线（68 条）：
#    $TC 2>&1 | grep -E '^(Ran|OK|FAILED)'   # 得到：Ran 68 tests ... OK（2026-09-15 主 Agent 与起草方实测）
# 2. semantic 套基线（0 条）：目录尚不存在，从 0 开始累计。

# 全局门禁
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py | tail -1   # I00-IF SUMMARY pass=36 fail=0
bash openspec/acceptance/run_all.sh | tail -1                                                 # SUMMARY pass=2 fail=1 blocked=8
bash openspec/schemas/verify.sh >/dev/null; echo $?                                          # 0
$TL 2>&1 | grep -E '^(Ran|OK|FAILED)'                                                        # OK
git diff --check
```

---

## 1. 逐 ACT 的 Red → Green（两套分列，第 89 条）

| ACT | 组 | 套 | Red（实现前） | Green（实现后，权威引用 §2 对应套累计列） |
|---|---|---|---|---|
| 00 | L1 | corpus | `$TC` → 新增用例 `ImportError`（基线 68 全绿） | `$TC` OK，≥ 86（基线 68 + 本 ACT 18） |
| 01 | L1 | corpus | `$TC` → 新增用例 `ImportError` | `$TC` OK，≥ 102（累计 86 + 16） |
| 02 | L2 | corpus | `$TC` → 新增用例 `ImportError` | `$TC` OK，≥ 120（累计 102 + 18） |
| 03 | L2 | corpus | `$TC` → 新增用例 `ImportError` | `$TC` OK，≥ 136（累计 120 + 16） |
| 04 | L3 | semantic | `$TS` → `ImportError`（套件目录新建） | `$TS` OK，≥ 18（基线 0 + 本 ACT 18） |
| 05 | L3 | semantic | `$TS` → 新增用例 `ImportError` | `$TS` OK，≥ 36（累计 18 + 18） |
| 06 | L3 | semantic | `$TS` → 新增用例 `ImportError` | `$TS` OK，≥ 54（累计 36 + 18） |
| 07 | L4 | corpus | `$TC` → 新增用例 `ImportError` | `$TC` OK，≥ 153（实测基线 139 + 14）；`m3-coverage.sh` 宿主缺失时 exit 2（BLOCKED） |

---

## 2. 用例阈值计算与权威累计表（第 86、89 条）

> **唯一权威出处声明（第 86、89 条）**：
> 本节按两套独立分列：`corpus` 套与 `semantic` 套**各自独立累计，绝不跨套相加**。
> 累计值严格等于「既有基线 + 本包新增用例实数之和」。
> §1 的 Green 列以及各 `act/*.yaml` 中 `verify` 注释里的期望数字，一律且必须精确引用本表数值，绝不允许各写各的。

### 2.1 corpus 套（$TC，`pipeline/corpus_compiler/tests`，基线 68）

基线取数命令：`.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -t . 2>&1 | grep -E "^(Ran|OK|FAILED)"` → `Ran 68 OK`（2026-09-15 实测）。

| ACT | 组 | 模块与用例文件 | 本 ACT 具名用例实数 | 累计算术公式 | 累计用例阈值 |
|---|---|---|---|---|---|
| `impl-10/00` | L1 | `test_offset_anchors.py` | 18 | 基线 68 + 18 | **86** |
| `impl-10/01` | L1 | `test_text_compiler.py` | 16 | 86 + 16 | **102** |
| `impl-10/02` | L2 | `test_step_offset.py` | 18 | 102 + 18 | **120** |
| `impl-10/03` | L2 | `test_gate_offset.py` | 16 | 120 + 16 | **136** |
| `impl-10/03` 补 | L2 | `test_gate_offset.py`（第 93 条注入反例） | 3 | 136 + 3 | **139** |
| `impl-10/07` | L4 | `test_acceptance.py` | 14 | 139 + 14 | **153** |

corpus 套总计新增用例：18 + 16 + 18 + 16 + 3 + 14 = **85** 条；最终套件总数：68 + 85 = **153** 条。（2026-09-16 主 Agent 修订：act/03 验收时依第 93 条补入 3 条注入反例，实测基线 139；act/07 依第 94 条增 2 条、改名 1 条，本 ACT 14 条。）

### 2.2 semantic 套（$TS，`pipeline/corpus_compiler/semantic/tests`，基线 0）

基线：新建子包目录，基线为 **0**。

| ACT | 组 | 模块与用例文件 | 本 ACT 具名用例实数 | 累计算术公式 | 累计用例阈值 |
|---|---|---|---|---|---|
| `impl-10/04` | L3 | `test_offset_rules.py` (3) + `test_proposer.py` (9) + `test_proposals.py` (6) | 18 | 基线 0 + 18 | **18** |
| `impl-10/05` | L3 | `test_offset_assemble.py` (8) + `test_review.py` (10) | 18 | 18 + 18 | **36** |
| `impl-10/06` | L3 | `test_semantic_gate.py` | 18 | 36 + 18 | **54** |

semantic 套总计新增用例：18 + 18 + 18 = **54** 条；最终套件总数：**54** 条。

**全包两套总计新增具名用例数**：80 + 54 = **134** 条。

### 2.3 各 ACT grep -c 实数核对

```bash
$ for f in docs/blackbox-spec-rework/work-items/impl-10-corpus-semantic/act/*.yaml; do echo "$(basename $f): $(grep -c '^\s*- test_' $f)"; done
00.yaml: 18
01.yaml: 16
02.yaml: 18
03.yaml: 16
04.yaml: 18  (test_offset_rules: 3, test_proposer: 9, test_proposals: 6)
05.yaml: 18  (test_offset_assemble: 8, test_review: 10)
06.yaml: 18  (test_semantic_gate: 18)
07.yaml: 12  (test_acceptance: 12)
```

---

## 3. 回归与全量门禁（每 ACT 完成后必须执行）

```bash
# 1. 接口与闭集检查
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py | tail -1   # 必须 fail=0

# 2. 全量回归基线（恒不变）
bash openspec/acceptance/run_all.sh | tail -1                                                 # 恒为 SUMMARY pass=2 fail=1 blocked=8

# 3. Schemas 语法校验
bash openspec/schemas/verify.sh >/dev/null; echo $?                                          # 恒为 0

# 4. 单元测试全量
$TL 2>&1 | grep -E '^(Ran|OK|FAILED)'                                                        # OK
$TC 2>&1 | grep -E '^(Ran|OK|FAILED)'                                                        # OK，按 §2.1 阈值
$TS 2>&1 | grep -E '^(Ran|OK|FAILED)'                                                        # OK，按 §2.2 阈值（L3 起）

# 5. 代码与 Git 规范
git diff --check
git status --short | grep -v '^??' | grep -vE 'pipeline/corpus_compiler|openspec/acceptance/m3-coverage.sh'   # 必须为空
```

---

## 附录：OCR 路线 TDD（第二版 OCR）

> **以下内容为原 OCR / 页码路线草稿，全部标记为 `DEFERRED（第二版 OCR）`，不在第一版电子文本实现中启用。**

```text
原 OCR 路线 TDD（留第二版参考）：
- 原 ACT 00: mini_ed01_semantic 宿主校验（exit 0）
- 原 ACT 01: Proposer Adapter 接口与回放（≥ 16）
- 原 ACT 02: 规则、字框对齐锚点与 assemble（≥ 32）
- 原 ACT 03: 独立语义 Gate（≥ 52）
- 原 ACT 04: run_m3_full 进入人工队列（≥ 64）
- 原 ACT 05: 人工裁决落盘 Checkpoint 与恢复（≥ 78）
- 原 ACT 06: 验收九子项与 m3-coverage.sh exit 0（≥ 84）
```

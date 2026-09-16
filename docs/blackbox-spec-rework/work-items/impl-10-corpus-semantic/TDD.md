# TDD：impl-10 M3 电子文本偏移锚点 + 语义层

## 0. 执行环境与基线命令

```bash
cd /Users/jingtaiwei/Git/Public/learn_system && export LC_ALL=en_US.UTF-8
PY=.venv/bin/python
TL="$PY -m unittest discover -s pipeline/ledger/tests -t ."
TC="$PY -m unittest discover -s pipeline/corpus_compiler/tests -t ."
TS="$PY -m unittest discover -s pipeline/corpus_compiler/semantic/tests -t ."

# 基线门禁
python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py | tail -1   # I00-IF SUMMARY pass=36 fail=0
bash openspec/acceptance/run_all.sh | tail -1                                                 # SUMMARY pass=2 fail=1 blocked=8
bash openspec/schemas/verify.sh >/dev/null; echo $?                                          # 0
$TL 2>&1 | grep -E '^(Ran|OK|FAILED)'                                                        # OK
git diff --check
```

---

## 1. 逐 ACT 的 Red → Green

| ACT | 组 | Red（实现前） | Green（实现后，权威引用 §2 累计列） |
|---|---|---|---|
| 00 | L1 | `.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -p 'test_offset_anchors.py' -t .` → `ImportError`（全红） | OK，≥ 18 |
| 01 | L1 | `.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -p 'test_*.py' -t .` → 新增用例 `ImportError` | OK，≥ 34 |
| 02 | L2 | `.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -p 'test_step_offset.py' -t .` → `ImportError` | OK，≥ 52 |
| 03 | L2 | `.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -p 'test_gate_offset.py' -t .` → `ImportError` | OK，≥ 68 |
| 04 | L3 | `.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/semantic/tests -p 'test_*.py' -t .` → `ImportError` | OK，≥ 86 |
| 05 | L3 | `.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/semantic/tests -p 'test_*.py' -t .` → 新增用例 `ImportError` | OK，≥ 104 |
| 06 | L3 | `.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/semantic/tests -p 'test_semantic_gate.py' -t .` → `ImportError` | OK，≥ 122 |
| 07 | L4 | `.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -p 'test_acceptance.py' -t .` → 新增用例 `ImportError` | OK，≥ 134；`m3-coverage.sh` exit 2（BLOCKED） |

---

## 2. 用例阈值计算与权威累计表（第 86 条）

> **唯一权威出处声明（第 86 条）**：
> 本表「累计用例阈值」列为工作包全部用例计数的**唯一权威依据**。
> §1 的 Green 列以及各 `act/*.yaml` 中 `verify` 注释里的期望数字，一律且必须精确引用本表数值，绝不允许各写各的。

### 2.1 阈值计算过程

| ACT | 组 | 模块与用例文件 | 本 ACT 具名用例实数 | 累计算术公式 | 累计用例阈值 |
|---|---|---|---|---|---|
| `impl-10/00` | L1 | `test_offset_anchors.py` | 18 | 18 | **18** |
| `impl-10/01` | L1 | `test_text_compiler.py` | 16 | 18 + 16 | **34** |
| `impl-10/02` | L2 | `test_step_offset.py` | 18 | 34 + 18 | **52** |
| `impl-10/03` | L2 | `test_gate_offset.py` | 16 | 52 + 16 | **68** |
| `impl-10/04` | L3 | `test_offset_rules.py`, `test_proposer.py`, `test_proposals.py` (3+9+6) | 18 | 68 + 18 | **86** |
| `impl-10/05` | L3 | `test_offset_assemble.py`, `test_review.py` (8+10) | 18 | 86 + 18 | **104** |
| `impl-10/06` | L3 | `test_semantic_gate.py` | 18 | 104 + 18 | **122** |
| `impl-10/07` | L4 | `test_acceptance.py` | 12 | 122 + 12 | **134** |

**总计具名用例数**：134 条。

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
.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t .                          # OK
.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/tests -t .                 # OK
.venv/bin/python -m unittest discover -s pipeline/corpus_compiler/semantic/tests -t .        # OK（L3 起）

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

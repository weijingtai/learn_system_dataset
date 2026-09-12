# impl-03 四查复审 R2（独立审查者）

- 复审对象：返工提交 `06d7d08`（R3-01～R3-05）与 `881538d`（R3-06）；`git diff 1a189ae…HEAD --stat` 确认 impl-03-validation 全部改动仅这两笔（10 个文件），工作树与 `881538d` 一致。
- 方法：逐条对照 R1 发现实测闭合；对关键数字重新独立计量；扫描返工引入的新问题。

## 判定：READY

R3-01～R3-06 全部闭合；未发现新阻断或新重要问题。

## 逐条闭合核对

| 编号 | 结论 | 证据 |
|---|---|---|
| R3-01 | 闭合 | 逐 act 重数具名用例：8/8/8/24/12/10/13（累计 8/16/24/48/60/70/83）；TDD.md §1 阈值改为 8/16/24/48/60/70/83，act/03–06 verify 注释（≥48/60/70/83）、README §1 与 ACCEPTANCE §2「ACT 06 后累计 ≥ 83」全部同步；每个累计值与阈值精确相等，BDD §8 对齐表未动、仍然成立 |
| R3-02 | 闭合 | act/06 fail_closed_tamper 改为「Gate 未过时 StepRun 仍 succeeded，m5 StagePackage 仍照常封存且 `validation.passed == false`（§9 第 21 条），下游判据必须拒绝」；BDD 6.3、TDD §2 fail-closed 行、act/06 用例注记同步；与 G7-RULINGS §9 第 21 条逐字一致；BDD 6.4 / act/05 test_after_begin_exception / ACCEPTANCE §3 保留的「无 m5 StagePackage」仅指 begin 之后异常封存路径，语义正确非残留 |
| R3-03 | 闭合 | 按 fixture 独立复算：spans 带 `quote_sha256` 字段 0 条 → quote_hash_not_stored 1；unresolved_glyph 涉及 2 个 span（s03: c0038/c0040/c0041；s04: c0036/c0037）；pending page_001=32、page_003=193（合计 225）→ unproofread_glyphs 2；字框拼接 ≠ 文本 2 条（s03 6/5、s04 17/16）→ G1 4 + G3 3 = **7**；act/05 用例、BDD 6.1、TDD act/05 行、README §1 新增「合计 findings 7（warnings 5、info 2、failures 0）」四处一致，severity 算术复核成立 |
| R3-04 | 闭合 | TDD.md §0 改为「K2: 10（ACT 00–03 的 9 个文件 + tests）」，与实际 `ls pipeline/validation`（9 文件 + tests/ = 10 条目）一致；K3: 16 不变仍正确 |
| R3-05 | 闭合 | README §1 表与 act/03 contract 措辞改为「代码、fixture、schemas 内 git grep quote_hash 0 处」；实测该范围 0 处（全仓 21 处均在 work-items 文档内，不再误述） |
| R3-06 | 闭合 | 实跑 `python3 docs/blackbox-spec-rework/work-items/impl-00-interfaces/check_interfaces.py` → `I00-IF SUMMARY pass=18 fail=0`、exit 0，与 ACT.yaml/PROMPT-E1/README/ACCEPTANCE/TDD 五处写死的期望串逐字一致；checker 覆盖：IF02/IF03 断言 §4 含 `gate_results`/`validation_package` 恰 1 次、IF18 断言 §4 **不含 `gate_report`/`validator_report`**（正好落实 R1 指出的 gate_report 对账）、IF10–IF11 防重复与 DEFERRED 残留；开工前提、停手规则、TDD §2 均已绑定该探针 |

## 返工引入问题扫描

- 改动范围合规：两笔提交只写 `docs/blackbox-spec-rework/work-items/impl-03-validation/`，未触碰规格、Schema、fixture、`pipeline/**`、台账或 impl-00/impl-04 文件。
- 一致性：降阈值而非加用例，BDD §8 场景映射不受影响；`counts.findings == 7` 在 act/05、BDD、TDD、README 四处无版本分叉；`validation.passed == false` 的新表述与 act/05 step 10–11 原文吻合。
- 备注（非发现）：开工前提把 `I00-IF SUMMARY pass=18 fail=0` 写成字面判据，与 checker 的检查条数强耦合；impl-00 后续增删检查会使该串失配。失败模式安全（停手上报、不静默放行），且停手规则已显式覆盖，无需本次修改。

## 自检与提交

- 本文件只新增 `docs/blackbox-spec-rework/reviews/IMPL-03-REVIEW-R2.md`；`git diff --check` 无输出。

# IMPL-00 W5H（act/13）四查审查 R1（独立审查者 W4-R5）

- 审查对象：`work-items/impl-00-interfaces/act/13.yaml`（M6 artifact_type 闭集登记与 INTERFACES §2.6/§3.4/§3.5/§3.6/§3.15/§4 对账），提交 `950349b`，以 HEAD（`91e5348`）文本为准。
- 依据：G7-RULINGS §9.6 第 47 条（登记 ACT 模式）、§9.8 第 54 条（fail=0 不写死 pass 数）、§9.12 第 61–62 条、§4 impl-06（D-10/D-13）；`INTERFACES.md` 现状（act/12 已执行，`check_interfaces.py` 实测 `I00-IF SUMMARY pass=24 fail=0`、13 个现存用例）；impl-06 README §4.2/§5.3/§5.4。

## 一、忠实性

- A 条：§4 M6 行（`INTERFACES.md:348`，行号实测准确）整行替换为四行 `review_queue`/`rework_impact_report`/`reviewed_edition`/`reviewed_edition_package`，名称与 impl-06 D-13 提名逐字一致；**删除 `correction_request`** 与 impl-06 D-10/C7 一致（`service.py:940-945` `record_human_event` 只收 `human_event`，理由引用属实），并落实第 62 条裁定链。
- C 条：§2.6 卡片（:161-175，实测准确）按 impl-06 定稿重写——冻结输入 6 修订、task/Checkpoint 粒度（`m6_review_<entity_id>_<decision_type>`）、payload/counts/content_sha256/operation、九项 Gate 结果作为自身 validation_report（第 50 条）、M6 不改 M4 修订状态（第 62 条）、Snapshot 归 M7（第 61 条）——与 impl-06 README §5.1/§5.2/§5.3 逐字对齐。
- D 条：§3.4 `review_decision` 按已验收 `review_events.py` 改写（顶层键 12 项、校验拒收多余键、school_dispute 配 review_school_attribution）——与实测代码一致。
- E/F 条：`reviewed_edition`/`rework_impact_report` 结构 = impl-06 README §5.3/§5.2 逐字（含 `standing` 闭集、`carried_from_revision_id`、§14.1:641 必含字段全覆盖）。
- G 条：§3.15（:323，实测准确）删 `correction_request` 与 `review_queue`、保留 `term_layer_report` 与四类 Proposal——与 act/12 K 执行后的现状衔接正确。
- B/H/I 条：登记纪律行、M6_TYPES 纳入 IF11、不动 M4 五行与 M5/M8 首纵切行——符合 P2 单写者与第 47 条模式。
- 第 54 条：绿色期望与 verify 全部为「末行 `fail=0` 且 exit 0，IF25–IF28 四个 PASS 行存在；不写死 pass 总数」，`test_summary_line_format` 不断言 pass 总数。

## 二、覆盖性

- 用例 18 = 现存 13（名字与 `tests/test_check_interfaces.py` 逐一相符）+ 新增 5（IF25–IF28 各一 + IF29 一），`≥ 18` 可达；Red（先改 check_interfaces 再改 INTERFACES）→ Green 次序明确。
- verify 七项均可计算：`grep -c '^| M6 ' ≥ 4`（替换后恰 4 行）、`grep -c '^| M6 .*correction_request' = 0`（替换后可达）、`grep -c 'review_queue' ≥ 1`、热点未动、schemas verify 0、`git diff --check`。
- 时长 60 ≤ 110；depends_on [impl-00/12] 与现状（act/12 已执行、pass=24）一致。

## 三、可执行性

- 写范围仅 `INTERFACES.md`、`check_interfaces.py`、`tests/__init__.py`、`tests/test_check_interfaces.py`；commit.add 同；on_fail 禁改代码/Schema/fixture/ledger、禁改 IF01–IF24 与现存 13 用例断言。
- J 条实现要求可行：M6_TYPES 显式编号 IF25–IF28、`FORBIDDEN_M6_TYPES = ("correction_request",)` 走 IF29、IF11 集合扩为 REQUIRED_TYPES + M4_TYPES + M6_TYPES、docstring IF01–IF29——与 act/12 的 M4_TYPES 先例同构。
- 行号引用实测全部准确：§2.6 :161-175、§3.4 :277-279、§3.5 :281-283、§3.6 :285-287、§3.15 :323、表头纪律行 :329、§4 M6 行 :348。
- 可执行性发现：G1（Red 预期与 INTERFACES 现状不符，见下）。

## 四、独立性

- 单写者（P2）：本波唯一写 INTERFACES §4 的 ACT（act/12 已完成、act/05 属 fixture 面）；与 impl-06（pipeline/review/**）、impl-08 零交集。
- 防同错同过：IF25–IF28 逐类型「出现恰 1 次」+ IF11 状态列 + IF29 旧名禁忌三重校验；现有用例断言冻结。

## 发现（编号｜严重度｜文件:行号｜问题｜依据 文件:行号｜修改建议）

- G1｜阻断｜act/13.yaml:11（tests_first）｜Red 预期失真：称「应因 §4 尚未登记 M6 类型而 FAIL IF25–IF28」，但 `INTERFACES.md:348` 现行 M6 行已含全部四个类型名（`review_queue`/`correction_request`/`rework_impact_report`/`reviewed_edition`/`reviewed_edition_package`），Red 实际 FAIL 项为 IF11（四类型状态列「纵切后（D-14）」）与 IF29（`correction_request` 在表）；IF25–IF28 将 PASS——执行者按 tests_first 核对 Red 必不符而停手上报（on_fail：门禁不符）｜INTERFACES.md:348（实测：「| M6 | `review_queue` / `correction_request` / … | 纵切后（D-14）」）｜tests_first 改为「Red 应 FAIL IF11（M6 四类型状态列）与 IF29（correction_request 在表）；IF25–IF28 因类型名已在行内而 PASS，属预期」。
- G2｜建议｜act/13.yaml:20（A 条）｜删除 `correction_request` 的依据标注为「G7-RULINGS §9.12 第 62 条 / impl-06 D-10」，第 62 条正文只裁 D-08（不改 M4 状态）；删除类型的直接依据是 impl-06 D-10 + C7 对账（第 53/62 条为关联）｜G7-RULINGS.md:182（第 62 条）；impl-06 README.md:87（D-10）、:113（C7）｜依据标注改为「impl-06 D-10（A）与 §4.2 C7；第 62 条关联」。
- G3｜建议｜act/13.yaml:33（D 条）｜§3.4 改写含 `evidence_refs[]` 但未给 minLength/约束，`consumption_level` 未列闭集（INTERNAL_DEMO/DEV_SEARCH/PUBLIC_RELEASE，`review_events.py:23`）｜`review_events.py:23`；act/13.yaml:33｜补 `consumption_level` 三值闭集与 `evidence_refs[]` 元素为 `source_span_id` 格式，避免登记后仍欠约束。

## 判定

**REWORK**（阻断 1：G1；建议 2：G2、G3。G1 为一处 Red 预期文本订正，随 impl-06 返工同批处理后本 ACT 即可执行；其余结构与对账全部正确。）

（审查者：W4-R5；以 HEAD `91e5348` 只读核查；`git diff --check` 无输出。）

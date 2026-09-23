"""I 波轨道 2（ACT 30）：Gate 多版次对勘检查的具名用例（CHARTER §25 / §28）。

输入一律**手工构造**成 §25 形状（Snapshot `editions[].collation_units`、视图 `collation_units`），
不读 fixture 与金标——它们仍是旧口径（r2 的对齐是自环）。

世界（§25.9 同构）：基底 ed01 声明 0001/0002/0003 present、0005 present:false；本轮视图 ed99：
0001 同主体同文 → alignment；0003 同主体异文 → variant_reading；0002 声明 present:false → omission；
0005 有断言且 present → addition；0004 ed01 未声明 → not_comparable；另有一条无键断言。
"""

import ast
import copy
import unittest
from pathlib import Path

from pipeline.assembly import canonical
from pipeline.assembly.gate import ASSEMBLY_CHECK_ORDER, _asm_closure, evaluate_assembly

GATE_PATH = Path(__file__).resolve().parents[1] / "gate.py"

CHECK = "collation_comparable_only"
TECH = "qizheng"
ED01 = "src_sanche_ed01"
ED99 = "src_sanche_ed99"
PAT1 = "pat_qizheng_900001"
PAT2 = "pat_qizheng_900002"
STATUS = "machine_extracted"

A01, A02, A03 = "as_qizheng_900001", "as_qizheng_900002", "as_qizheng_900003"
B01, B03, B04, B05, B_NOKEY = (
    "as_qizheng_900011",
    "as_qizheng_900013",
    "as_qizheng_900014",
    "as_qizheng_900015",
    "as_qizheng_900016",
)


def key(n):
    return "sanche-%04d" % n


def text_sha(text):
    return canonical.sha256_hex(canonical.nfc_key(text).encode("utf-8"))


def unit(n, present=True):
    return {"collation_key": key(n), "present": present}


def edition(source_id, units):
    return {
        "collation_units": units,
        "corpus_spans_revision_id": None,
        "edition_complete": False,
        "edition_part_artifact_ids": ["art_%032x" % (1 if source_id == ED01 else 0x99)],
        "evidence_level": "offset_level",
        "reviewed_edition_package_revision_id": "rev_%032x" % 0,
        "reviewed_edition_revision_id": "rev_%032x" % 1,
        "source_id": source_id,
        "stage_package_id": "pkg_m6_%032x" % 0,
        "work_key": "sanche",
    }


def assertion(assertion_id, source_id, n, subject, text):
    return {
        "assertion_id": assertion_id,
        "collation_key": key(n) if n is not None else None,
        "content_status": STATUS,
        "evidence": [],
        "proposition": text,
        "school_view_ids": [],
        "source_id": source_id,
        "source_span_ids": [],
        "subject_entity_id": subject,
        "text_sha256": text_sha(text),
    }


def view_assertion(assertion_id, n, text):
    return {
        "assertion_id": assertion_id,
        "collation_key": key(n) if n is not None else None,
        "content_status": STATUS,
        "evidence": [],
        "proposition": text,
    }


def pattern(pattern_id, name):
    return {
        "aliases": [],
        "assertion_ids": [],
        "concept_id": None,
        "name": name,
        "pattern_id": pattern_id,
        "provenance": [{"content_sha256": "0" * 64, "content_status": STATUS, "source_id": ED01}],
        "rules": [],
        "school_view_ids": [],
    }


def relation(kind, from_id, to_id, detail, mode="auto", proposal_kind="evidence"):
    tag = detail.get("collation_key")
    return {
        "detail": detail,
        "from_entity_id": from_id,
        "relation_key": "%s:%s" % (kind, tag),
        "relation_kind": kind,
        "resolution": {"mode": mode, "proposal_key": "%s:%s" % (proposal_kind, tag)},
        "to_entity_id": to_id,
    }


def not_comparable(n, assertion_id, reason):
    return {
        "assertion_id": assertion_id,
        "collation_key": key(n) if n is not None else None,
        "reason": reason,
        "source_id": ED99,
    }


def sort_knowledge(knowledge):
    for name, field in (
        ("editions", "source_id"),
        ("patterns", "pattern_id"),
        ("assertions", "assertion_id"),
        ("relations", "relation_key"),
    ):
        knowledge[name].sort(key=lambda item: item[field])
    return knowledge


def base_knowledge():
    return sort_knowledge(
        {
            "technique_id": TECH,
            "id_allocation": {"pat_qizheng": 900002},
            "id_range": {"pat_qizheng": [900001, 999999]},
            "allocated_pattern_ids": [],
            "retired_entity_ids": [],
            "editions": [edition(ED01, [unit(1), unit(2), unit(3), unit(5, False)])],
            "concepts": [],
            "patterns": [pattern(PAT1, "三辰"), pattern(PAT2, "貴格")],
            "assertions": [
                assertion(A01, ED01, 1, PAT1, "三辰通載"),
                assertion(A02, ED01, 2, None, "（宋）錢如璧撰"),
                assertion(A03, ED01, 3, PAT1, "貴格之圖"),
            ],
            "school_views": [],
            "conflict_groups": [],
            "relations": [],
        }
    )


#: 视图断言：(号, 位置, 裁决后主体, 文本)
VIEW_ROWS = (
    (B01, 1, PAT1, "三辰通載"),  # 同主体同文 → alignment
    (B03, 3, PAT1, "貴格之圗"),  # 同主体异文 → variant_reading
    (B04, 4, PAT1, "三辰通載目錄"),  # ed01 未声明 0004 → not_comparable(base_undeclared)
    (B05, 5, PAT2, "附錄"),  # ed01 声明 present:false → addition
    (B_NOKEY, None, None, "序"),  # 无键 → not_comparable(missing_collation_key)
)


def make_world():
    base = base_knowledge()
    cset = {
        "source_id": ED99,
        "technique_id": TECH,
        # 末项是 collation_key=null 的声明：计入 not_comparable，但不写进 editions（§28 Q4 / §29 Q11）
        "collation_units": [
            unit(1), unit(2, False), unit(3), unit(4), unit(5),
            {"collation_key": None, "present": True},
        ],
        "assertions": [view_assertion(a, n, t) for a, n, _, t in VIEW_ROWS],
        "patterns": [],
        "school_views": [],
        "concept_mentions": [],
        "new_concept_candidates": [],
    }
    reviewed = {
        "approved": [
            {"kind": "assertion", "entity_id": a, "content_status": STATUS} for a, *_ in VIEW_ROWS
        ]
    }
    knowledge = copy.deepcopy(base)
    knowledge["editions"].append(
        edition(ED99, [unit(1), unit(2, False), unit(3), unit(4), unit(5)])
    )
    knowledge["assertions"] += [assertion(a, ED99, n, s, t) for a, n, s, t in VIEW_ROWS]
    knowledge["relations"] = [
        relation("alignment", B01, A01, {"collation_key": key(1)}),
        relation(
            "variant_reading",
            B03,
            A03,
            {
                "collation_key": key(3),
                "opcodes": [["equal", 0, 2, 0, 2], ["replace", 2, 3, 2, 3], ["equal", 3, 4, 3, 4]],
            },
        ),
        relation("omission", A02, None, {"collation_key": key(2), "absent_source_id": ED99}),
        relation("addition", B05, None, {"collation_key": key(5), "absent_source_id": ED01}),
    ]
    sort_knowledge(knowledge)
    return {
        "base_knowledge": base,
        "views": [{"source_id": ED99, "candidate_set": cset, "reviewed_edition": reviewed}],
        "decisions": [],
        "knowledge": knowledge,
        "identity_delta": {"entries": []},
        "collation": {
            "not_comparable": [
                not_comparable(None, None, "missing_collation_key"),  # null 键声明
                not_comparable(None, B_NOKEY, "missing_collation_key"),  # 无键断言
                not_comparable(4, None, "base_undeclared"),
            ]
        },
        "report": {
            "affected_entity_ids": [A01, A02, A03],
            "rebuilt_entity_ids": [],
            "round_proposal_keys": sorted(
                rel["resolution"]["proposal_key"] for rel in knowledge["relations"]
            ),
        },
    }


# ------------------------------------------------------------------ 篡改工具
def find(items, field, value):
    return next(item for item in items if item[field] == value)


def rel_of(world, kind):
    return find(world["knowledge"]["relations"], "relation_kind", kind)


def cset_of(world):
    return world["views"][0]["candidate_set"]


def add_view_assertion(world, assertion_id, n, subject, text):
    """在视图与新 knowledge 里**一致地**加一条获批断言（其他检查不受牵连）。"""
    cset_of(world)["assertions"].append(view_assertion(assertion_id, n, text))
    world["views"][0]["reviewed_edition"]["approved"].append(
        {"kind": "assertion", "entity_id": assertion_id, "content_status": STATUS}
    )
    world["knowledge"]["assertions"].append(assertion(assertion_id, ED99, n, subject, text))
    sort_knowledge(world["knowledge"])


def set_view_text(world, assertion_id, text):
    """视图与新 knowledge 同步改文本（view_objects_unaltered 仍然过）。"""
    find(cset_of(world)["assertions"], "assertion_id", assertion_id)["proposition"] = text
    item = find(world["knowledge"]["assertions"], "assertion_id", assertion_id)
    item["proposition"] = text
    item["text_sha256"] = text_sha(text)


def set_subject(world, assertion_id, subject):
    find(world["knowledge"]["assertions"], "assertion_id", assertion_id)["subject_entity_id"] = subject


def replace_relation(world, kind, new_relation):
    relations = [rel for rel in world["knowledge"]["relations"] if rel["relation_kind"] != kind]
    relations.append(new_relation)
    world["knowledge"]["relations"] = relations
    sort_knowledge(world["knowledge"])
    world["report"]["round_proposal_keys"] = sorted(
        rel["resolution"]["proposal_key"] for rel in relations
    )


def set_units(world, source_id, units, *, where="knowledge"):
    find(world[where]["editions"], "source_id", source_id)["collation_units"] = units


def add_not_comparable(world, row):
    rows = world["collation"]["not_comparable"]
    rows.append(row)
    rows.sort(key=lambda r: (r["source_id"], r["collation_key"] or "", r["assertion_id"] or ""))


ED02 = "src_sanche_ed02"
C01 = "as_qizheng_900021"


def make_three_edition_world():
    """基底已有 ed01 与 ed02（ed02 → ed01 的对齐是上一轮的），本轮 ed99（§29 Q8）。

    ed99 的 0001 对 ed01、ed02 各可比 → 两条 alignment；ed02 只声明 0001，
    其余单元对 ed02 不可比但对 ed01 可比 → 不列入 not_comparable（§29 Q11 第 5 条）。
    """
    world = make_world()
    carried = relation("alignment", C01, A01, {"collation_key": key(1)})
    carried["relation_key"] = "alignment:ed02-ed01-0001"
    for doc in (world["base_knowledge"], world["knowledge"]):
        doc["editions"].append(edition(ED02, [unit(1)]))
        doc["assertions"].append(assertion(C01, ED02, 1, PAT1, "三辰通載"))
        doc["relations"].append(copy.deepcopy(carried))
        sort_knowledge(doc)
    fresh = relation("alignment", B01, C01, {"collation_key": key(1)})
    fresh["relation_key"] = "alignment:ed99-ed02-0001"
    world["knowledge"]["relations"].append(fresh)
    sort_knowledge(world["knowledge"])
    world["report"]["affected_entity_ids"] = [A01, A02, A03, C01]
    world["report"]["round_proposal_keys"] = sorted(
        {rel["resolution"]["proposal_key"] for rel in world["knowledge"]["relations"]}
    )
    return world


class GateCollationCase(unittest.TestCase):
    def evaluate(self, world):
        return evaluate_assembly(**world)

    def assert_collation_fails(self, world, marker):
        res = self.evaluate(world)
        check = res["checks"][CHECK]
        self.assertFalse(check["passed"], "%s 未转红: %s" % (CHECK, check["detail"]))
        self.assertFalse(res["passed"], "单点篡改后总体判定必须为 False")
        self.assertIn(marker, check["detail"], "失败理由须实指「%s」: %s" % (marker, check["detail"]))
        return check

    def assert_all_pass(self, world):
        res = self.evaluate(world)
        failed = {
            name: res["checks"][name]["detail"]
            for name in ASSEMBLY_CHECK_ORDER
            if not res["checks"][name]["passed"]
        }
        self.assertEqual(failed, {})
        self.assertTrue(res["passed"])
        return res

    # ------------------------------------------------------------ 正向
    def test_well_formed_four_kinds_pass(self):
        world = make_world()
        kinds = sorted(rel["relation_kind"] for rel in world["knowledge"]["relations"])
        self.assertEqual(kinds, ["addition", "alignment", "omission", "variant_reading"])
        res = self.assert_all_pass(world)
        self.assertEqual(list(res["checks"]), list(ASSEMBLY_CHECK_ORDER))

    # ------------------------------------------------------------ 关系两端
    def test_tamper_self_loop(self):
        world = make_world()
        rel_of(world, "alignment")["to_entity_id"] = B01
        self.assert_collation_fails(world, "自环")

    def test_tamper_null_endpoint_on_alignment(self):
        world = make_world()
        rel_of(world, "alignment")["to_entity_id"] = None
        self.assert_collation_fails(world, "null 端点")

    def test_tamper_addition_direction_reversed(self):
        world = make_world()
        addition = rel_of(world, "addition")
        addition["from_entity_id"], addition["to_entity_id"] = None, B05
        self.assert_collation_fails(world, "方向")

    def test_tamper_alignment_direction_reversed(self):
        world = make_world()
        alignment = rel_of(world, "alignment")
        alignment["from_entity_id"], alignment["to_entity_id"] = A01, B01
        self.assert_collation_fails(world, "方向")

    def test_tamper_same_source_pair(self):
        # 旧版断言改记在新版 source 名下：两端同 source，同一版次不跟自己比（§25.3）
        world = make_world()
        find(world["knowledge"]["assertions"], "assertion_id", A01)["source_id"] = ED99
        self.assert_collation_fails(world, "同一版次")

    def test_tamper_detail_collation_key_wrong(self):
        world = make_world()
        rel_of(world, "alignment")["detail"]["collation_key"] = key(3)
        self.assert_collation_fails(world, "collation_key")

    # ------------------------------------------------------------ 四类的内容条件
    def test_tamper_omission_but_view_actually_present(self):
        # 视图其实声明了 0002 present 且有同主体同文断言 → 该是 alignment，不是 omission
        world = make_world()
        for units in (cset_of(world)["collation_units"],):
            find(units, "collation_key", key(2))["present"] = True
        set_units(world, ED99, [unit(1), unit(2), unit(3), unit(4), unit(5)])
        add_view_assertion(world, "as_qizheng_900012", 2, None, "（宋）錢如璧撰")
        self.assert_collation_fails(world, "omission")

    def test_tamper_alignment_with_different_subjects(self):
        world = make_world()
        set_subject(world, B01, PAT2)
        self.assert_collation_fails(world, "subject_entity_id")

    def test_tamper_alignment_with_null_subjects(self):
        # §28 Q3：两端都为 null 也不算同一正式对象
        world = make_world()
        set_subject(world, B01, None)
        set_subject(world, A01, None)
        self.assert_collation_fails(world, "subject_entity_id")

    def test_tamper_alignment_with_different_text(self):
        world = make_world()
        set_view_text(world, B01, "三辰通载")
        self.assert_collation_fails(world, "text_sha256")

    def test_tamper_variant_reading_with_same_text(self):
        world = make_world()
        set_view_text(world, B03, "貴格之圖")
        self.assert_collation_fails(world, "text_sha256")

    def test_tamper_absent_source_id_wrong(self):
        for kind, wrong in (("addition", ED99), ("omission", ED01)):
            with self.subTest(kind=kind):
                world = make_world()
                rel_of(world, kind)["detail"]["absent_source_id"] = wrong
                self.assert_collation_fails(world, "absent_source_id")

    # ------------------------------------------------------------ 不可比单元
    def test_tamper_relation_on_unit_undeclared_by_base(self):
        # 0004：ed01 没声明 → 不可比，出了增文就 FAIL（基底声明只从 editions[].collation_units 读）
        world = make_world()
        world["knowledge"]["relations"].append(
            relation("addition", B04, None, {"collation_key": key(4), "absent_source_id": ED01})
        )
        sort_knowledge(world["knowledge"])
        self.assert_collation_fails(world, "不可比")

    def test_tamper_relation_on_multiple_assertions_unit(self):
        # §28 假设一：同侧同键 >1 条获批断言 → 不可比，不出任何关系
        world = make_world()
        add_view_assertion(world, "as_qizheng_900017", 1, PAT1, "三辰通載")
        add_not_comparable(world, not_comparable(1, None, "multiple_assertions_per_unit"))
        self.assert_collation_fails(world, "不可比")

    def test_multiple_assertions_unit_without_relation_passes(self):
        world = make_world()
        add_view_assertion(world, "as_qizheng_900017", 1, PAT1, "三辰通載")
        world["knowledge"]["relations"] = [
            rel for rel in world["knowledge"]["relations"] if rel["relation_kind"] != "alignment"
        ]
        world["report"]["round_proposal_keys"] = sorted(
            rel["resolution"]["proposal_key"] for rel in world["knowledge"]["relations"]
        )
        add_not_comparable(world, not_comparable(1, None, "multiple_assertions_per_unit"))
        self.assert_all_pass(world)

    def test_tamper_relation_on_view_undeclared_key(self):
        # §28 Q5：视图有 0006 的断言但没声明 0006 → 不可比（view_undeclared）
        world = make_world()
        for doc in (world["base_knowledge"], world["knowledge"]):
            find(doc["editions"], "source_id", ED01)["collation_units"] = [
                unit(1), unit(2), unit(3), unit(5, False), unit(6)
            ]
            doc["assertions"].append(assertion("as_qizheng_900006", ED01, 6, PAT1, "六"))
            sort_knowledge(doc)
        add_view_assertion(world, "as_qizheng_900018", 6, PAT1, "六")
        world["knowledge"]["relations"].append(
            relation("alignment", "as_qizheng_900018", "as_qizheng_900006", {"collation_key": key(6)})
        )
        sort_knowledge(world["knowledge"])
        world["report"]["affected_entity_ids"] = [A01, A02, A03, "as_qizheng_900006"]
        add_not_comparable(world, not_comparable(6, None, "view_undeclared"))
        self.assert_collation_fails(world, "不可比")

    # ------------------------------------------------------------ 完整性（反向）
    def test_tamper_comparable_unit_without_any_relation(self):
        for kind in ("alignment", "variant_reading", "addition", "omission"):
            with self.subTest(kind=kind):
                world = make_world()
                world["knowledge"]["relations"] = [
                    rel for rel in world["knowledge"]["relations"] if rel["relation_kind"] != kind
                ]
                self.assert_collation_fails(world, "完整性")

    def test_tamper_duplicate_relation_on_unit(self):
        world = make_world()
        extra = copy.deepcopy(rel_of(world, "alignment"))
        extra["relation_key"] = "alignment:dup"
        world["knowledge"]["relations"].append(extra)
        sort_knowledge(world["knowledge"])
        self.assert_collation_fails(world, "完整性")

    # ------------------------------------------------------------ 多个基底版次（§29 Q8）
    def test_three_editions_pairwise_pass(self):
        self.assert_all_pass(make_three_edition_world())

    def test_tamper_pairwise_completeness_second_base_edition(self):
        world = make_three_edition_world()
        world["knowledge"]["relations"] = [
            rel for rel in world["knowledge"]["relations"]
            if rel["relation_key"] != "alignment:ed99-ed02-0001"
        ]
        self.assert_collation_fails(world, "完整性")

    def test_tamper_carried_relation_not_byte_identical(self):
        def edit_detail(relations):
            find(relations, "relation_key", "alignment:ed02-ed01-0001")["detail"]["note"] = "x"
            return relations

        def drop(relations):
            return [rel for rel in relations if rel["relation_key"] != "alignment:ed02-ed01-0001"]

        for label, tweak in (("改了 detail", edit_detail), ("静默删掉", drop)):
            with self.subTest(case=label):
                world = make_three_edition_world()
                world["knowledge"]["relations"] = tweak(world["knowledge"]["relations"])
                self.assert_collation_fails(world, "逐字节")

    # ------------------------------------------------------------ R07b 落点（§28 Q2）
    def _r07b_world(self, choice):
        world = make_world()
        set_subject(world, B01, PAT2)  # 主体裁决到不同对象 → R07b
        proposal_key = "conflict:%s" % key(1)
        if choice == "reject_alignment":
            landing = relation(
                "distinct_from", B01, A01, {"collation_key": key(1)}, mode="human",
                proposal_kind="conflict",
            )
        else:
            landing = relation(
                "alignment", B01, A01, {"collation_key": key(1)}, mode="human",
                proposal_kind="conflict",
            )
        replace_relation(world, "alignment", landing)
        world["decisions"] = [
            {"proposal_key": proposal_key, "choice": choice, "target_entity_ids": [B01, A01]}
        ]
        return world

    def test_r07b_reject_lands_as_human_distinct_from(self):
        self.assert_all_pass(self._r07b_world("reject_alignment"))

    def test_r07b_accept_lands_as_human_alignment(self):
        self.assert_all_pass(self._r07b_world("accept_alignment"))

    def test_tamper_r07b_distinct_from_not_human(self):
        world = self._r07b_world("reject_alignment")
        landing = rel_of(world, "distinct_from")
        landing["resolution"]["mode"] = "auto"
        world["decisions"] = []
        self.assert_collation_fails(world, "human")

    # ------------------------------------------------------------ 版次声明（§25.5 / §28 Q4）
    def test_tamper_edition_missing_collation_units_field(self):
        for where in ("base_knowledge", "knowledge"):
            with self.subTest(where=where):
                world = make_world()
                del find(world[where]["editions"], "source_id", ED01)["collation_units"]
                self.assert_collation_fails(world, "collation_units")

    def test_tamper_view_edition_units_not_written_as_declared(self):
        declared = [unit(1), unit(2, False), unit(3), unit(4), unit(5)]
        cases = {
            "漏写 present:false": [unit(1), unit(3), unit(4), unit(5)],
            "写进 null 键": declared + [{"collation_key": None, "present": True}],
            "未升序": list(reversed(declared)),
            "present 写反": [unit(1), unit(2), unit(3), unit(4), unit(5)],
            "多带字段": [dict(item, note="x") for item in declared],
        }
        for label, units in cases.items():
            with self.subTest(case=label):
                world = make_world()
                set_units(world, ED99, units)
                self.assert_collation_fails(world, "editions")

    def test_tamper_other_edition_entry_changed(self):
        world = make_world()
        set_units(world, ED01, [unit(1), unit(2), unit(3)])
        self.assert_collation_fails(world, "editions")

    # ------------------------------------------------------------ not_comparable 清单（§28 Q7）
    def test_tamper_not_comparable_list_wrong(self):
        def drop(rows):
            return rows[1:]

        def wrong_reason(rows):
            rows = copy.deepcopy(rows)
            rows[1]["reason"] = "view_undeclared"
            return rows

        def extra_field(rows):
            return [dict(row, present=True) for row in rows]

        def unsorted(rows):
            return list(reversed(rows))

        for label, tweak in (
            ("少一项", drop),
            ("理由错", wrong_reason),
            ("多带字段", extra_field),
            ("未排序", unsorted),
        ):
            with self.subTest(case=label):
                world = make_world()
                world["collation"]["not_comparable"] = tweak(world["collation"]["not_comparable"])
                self.assert_collation_fails(world, "not_comparable")

    # ------------------------------------------------------------ 闭包触点（README §6:533，§28 Q6）
    def test_closure_contacts_read_declared_units(self):
        with self.subTest(rule="(a) 视图声明 present:false → 基底该位置断言入触点"):
            world = make_world()
            closure = _asm_closure(world["base_knowledge"], world["views"], [])
            self.assertIn(A02, closure["affected"])

        with self.subTest(rule="(b) 基底为视图 source 声明过、视图不再声明 → 基底该位置断言入触点"):
            world = make_world()
            base = world["base_knowledge"]
            base["editions"].append(edition(ED99, [unit(7)]))  # 上一轮 ed99 声明过 0007（无断言）
            find(base["editions"], "source_id", ED01)["collation_units"].append(unit(7))
            base["assertions"].append(assertion("as_qizheng_900007", ED01, 7, PAT1, "七"))
            sort_knowledge(base)
            closure = _asm_closure(base, world["views"], [])
            self.assertIn("as_qizheng_900007", closure["affected"])

        with self.subTest(rule="(c) present:true 的单元本身不贡献触点"):
            world = make_world()
            base = world["base_knowledge"]
            find(base["editions"], "source_id", ED01)["collation_units"].append(unit(6))
            base["assertions"].append(assertion("as_qizheng_900006", ED01, 6, PAT1, "六"))
            sort_knowledge(base)
            cset_of(world)["collation_units"].append(unit(6))  # 声明 present 却无断言
            closure = _asm_closure(base, world["views"], [])
            self.assertNotIn("as_qizheng_900006", closure["affected"])

    # ------------------------------------------------------------ 独立性
    def test_gate_does_not_import_engine_modules(self):
        tree = ast.parse(GATE_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.add("%s.%s" % (node.module or "", alias.name))
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        forbidden = ("matcher", "apply", "incremental", "orchestrate", "genesis")
        self.assertEqual(
            sorted(name for name in imported if set(name.split(".")) & set(forbidden)), []
        )
        allowed = {
            "pipeline.assembly.canonical",
            "pipeline.assembly.model",
            "pipeline.ledger.ids",
            "pipeline.ledger.states",
        }
        self.assertEqual(
            sorted(name for name in imported if name.startswith("pipeline") and name not in allowed),
            [],
        )


if __name__ == "__main__":
    unittest.main()


class RelationTouchesViewCase(unittest.TestCase):
    """§29 Q8 / §31：哪些对勘关系「涉及本轮视图」，须随本轮删掉重算。"""

    INDEX = {
        "assertions": {
            "as_qizheng_000001": {"source_id": "src_sanche_ed01"},
            "as_qizheng_000007": {"source_id": "src_sanche_ed99"},
        }
    }

    def _touches(self, relation, view_source):
        from pipeline.assembly.gate import _asm_relation_touches

        return _asm_relation_touches(relation, self.INDEX, {view_source})

    def test_addition_whose_absent_side_is_the_view_touches_it(self):
        # 同书返工 ed01：旧轮「ed99 有、ed01 缺」的增文，缺侧就是本轮视图，必须算涉及
        addition = {
            "relation_kind": "addition",
            "from_entity_id": "as_qizheng_000007",
            "to_entity_id": None,
            "detail": {"collation_key": "sanche-0005", "absent_source_id": "src_sanche_ed01"},
        }
        self.assertTrue(self._touches(addition, "src_sanche_ed01"))

    def test_omission_whose_absent_side_is_the_view_touches_it(self):
        omission = {
            "relation_kind": "omission",
            "from_entity_id": "as_qizheng_000001",
            "to_entity_id": None,
            "detail": {"collation_key": "sanche-0002", "absent_source_id": "src_sanche_ed99"},
        }
        self.assertTrue(self._touches(omission, "src_sanche_ed99"))

    def test_relation_between_two_other_editions_does_not_touch_view(self):
        addition = {
            "relation_kind": "addition",
            "from_entity_id": "as_qizheng_000007",
            "to_entity_id": None,
            "detail": {"collation_key": "sanche-0005", "absent_source_id": "src_sanche_ed01"},
        }
        self.assertFalse(self._touches(addition, "src_sanche_ed50"))

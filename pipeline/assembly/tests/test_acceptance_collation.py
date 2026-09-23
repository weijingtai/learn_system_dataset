"""I 波轨道 2（ACT 30）：验收判据 edition_collation 由 BLOCKED 改为实跑判定（CHARTER §25.9 / §28 / §29）。

输入一律**手工构造**成 §25 形状，经临时目录里的假夹具（manifest + 两份视图 + r2 金标）驱动
``check_edition_collation``；不读仓库里的 fixture 与金标（它们仍是旧口径）。
产出侧借用 test_gate_collation 的 §25.9 同构世界。
"""

import copy
import inspect
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from pipeline.assembly import acceptance
from pipeline.assembly.tests.test_gate_collation import (
    A01,
    A02,
    A03,
    ED01,
    ED99,
    STATUS,
    key,
    make_world,
    not_comparable,
    relation,
    sort_knowledge,
    view_assertion,
)


def old_view():
    """ed01 的视图：声明 0001/0002/0003 present、0005 present:false，三条获批断言保号进 r1。"""
    rows = ((A01, 1, "三辰通載"), (A02, 2, "（宋）錢如璧撰"), (A03, 3, "貴格之圖"))
    return {
        "source_id": ED01,
        "candidate_set": {
            "source_id": ED01,
            "collation_units": [
                {"collation_key": key(1), "present": True},
                {"collation_key": key(2), "present": True},
                {"collation_key": key(3), "present": True},
                {"collation_key": key(5), "present": False},
            ],
            "assertions": [view_assertion(a, n, t) for a, n, t in rows],
        },
        "reviewed_edition": {
            "approved": [
                {"kind": "assertion", "entity_id": a, "content_status": STATUS} for a, _, _ in rows
            ]
        },
    }


class EditionCollationCase(unittest.TestCase):
    def setUp(self):
        world = make_world()
        self.produced = world["knowledge"]
        self.golden = copy.deepcopy(world["knowledge"])
        self.new_view = world["views"][0]
        self.rows = world["collation"]["not_comparable"]
        self.count = len(self.rows)
        self.tmp = Path(tempfile.mkdtemp(prefix="test_acc_collation_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def verdict(self, *, produced=None, golden=None, rows=None, count=None):
        """把手工输入铺成假夹具 + 假 release，跑真的 check_edition_collation。"""
        root = self.tmp / ("fixture_%d" % len(list(self.tmp.iterdir())))
        manifest = {
            "editions": [
                {"source_id": ED01, "views_dir": "ed01/views"},
                {"source_id": ED99, "views_dir": "ed99/views"},
            ],
            "expected": {"round2": "expected/snapshot_r2.json"},
        }
        for edition, view in zip(manifest["editions"], (old_view(), self.new_view)):
            views = root / edition["views_dir"]
            views.mkdir(parents=True)
            for name in ("candidate_set", "reviewed_edition"):
                (views / ("%s.json" % name)).write_text(
                    json.dumps(view[name], ensure_ascii=False), encoding="utf-8"
                )
        (root / "expected").mkdir()
        (root / "expected" / "snapshot_r2.json").write_text(
            json.dumps(self.golden if golden is None else golden, ensure_ascii=False),
            encoding="utf-8",
        )
        (root / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
        release = {
            "manifest": manifest,
            "snapshots": {"r2": self.produced if produced is None else produced},
            "packages": {
                "r2": {"assembly_report": {"not_comparable_count": self.count if count is None else count}}
            },
            "pure": {
                "r2": {"result": {"collation": {"not_comparable": self.rows if rows is None else rows}}}
            },
        }
        with mock.patch.object(acceptance, "RELEASE_FIXTURE", root):
            return acceptance.check_edition_collation({"release": release})

    def without(self, document, kind):
        document = copy.deepcopy(document)
        document["relations"] = [rel for rel in document["relations"] if rel["relation_kind"] != kind]
        return document

    # ------------------------------------------------------------ 具名用例
    def test_edition_collation_pass_when_four_kinds_match_gold(self):
        self.assertEqual(self.verdict(), ("PASS", ""))

    def test_edition_collation_fail_when_a_kind_missing(self):
        for kind in acceptance.COLLATION_KINDS:
            with self.subTest(kind=kind):
                document = self.without(self.produced, kind)
                status, detail = self.verdict(produced=document, golden=document)
                self.assertEqual(status, "FAIL", detail)
                self.assertIn("四类对勘关系须各至少一条", detail)
                self.assertIn(kind, detail)

    def test_edition_collation_fail_when_relation_set_differs_from_gold(self):
        # 金标仍是旧口径：r2 那条对齐是自环 as_…900001 → as_…900001
        old_gold = copy.deepcopy(self.golden)
        for rel in old_gold["relations"]:
            if rel["relation_kind"] == "alignment":
                rel["from_entity_id"] = rel["to_entity_id"] = A01
        cases = {
            "金标是旧口径": {"golden": old_gold},
            "实跑少一条": {"produced": self.without(self.produced, "variant_reading")},
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                status, detail = self.verdict(**overrides)
                self.assertEqual(status, "FAIL", detail)
                self.assertIn("与 r2 金标不一致", detail)

    def test_edition_collation_never_blocked(self):
        empty = self.without(self.without(self.without(self.without(self.produced, "alignment"),
                                                       "variant_reading"), "addition"), "omission")
        for label, overrides in {
            "四类齐全": {},
            "零对勘关系（旧 BLOCKED 的触发条件）": {"produced": empty, "golden": empty},
            "只有缺一类": {"produced": self.without(self.produced, "addition"),
                        "golden": self.without(self.golden, "addition")},
        }.items():
            with self.subTest(case=label):
                status, _ = self.verdict(**overrides)
                self.assertIn(status, ("PASS", "FAIL"))
        # 判据里不再有能返回 BLOCKED 的分支（字符串字面量）
        self.assertNotIn('"BLOCKED"', inspect.getsource(acceptance.check_edition_collation))

    # ------------------------------------------------------------ 其余判据分项
    def test_edition_collation_fail_when_relation_on_not_comparable_unit(self):
        # 0004：ed01 未声明 → 不可比；产出与金标都带一条增文也不许过
        document = copy.deepcopy(self.produced)
        document["relations"].append(
            relation("addition", "as_qizheng_900014", None,
                     {"collation_key": key(4), "absent_source_id": ED01})
        )
        sort_knowledge(document)
        status, detail = self.verdict(produced=document, golden=document)
        self.assertEqual(status, "FAIL", detail)
        self.assertIn("落在不可比单元", detail)

    def test_edition_collation_fail_when_alignment_is_self_loop(self):
        # 旧 fixture 口径：ed99 沿用 ed01 的断言号，对齐成了自己连自己（§25.0）
        document = copy.deepcopy(self.produced)
        for rel in document["relations"]:
            if rel["relation_kind"] == "alignment":
                rel["from_entity_id"] = A01
        status, detail = self.verdict(produced=document, golden=document)
        self.assertEqual(status, "FAIL", detail)
        self.assertIn("对齐关系", detail)

    def test_edition_collation_fail_when_not_comparable_wrong(self):
        wrong_reason = copy.deepcopy(self.rows)
        wrong_reason[-1]["reason"] = "view_undeclared"
        for label, overrides, marker in (
            ("清单少一项", {"rows": self.rows[1:]}, "not_comparable 清单"),
            ("理由错", {"rows": wrong_reason}, "not_comparable 清单"),
            ("多带字段", {"rows": [dict(r, present=True) for r in self.rows]}, "not_comparable 清单"),
            ("计数写死 1", {"count": 1}, "not_comparable_count"),
        ):
            with self.subTest(case=label):
                status, detail = self.verdict(**overrides)
                self.assertEqual(status, "FAIL", detail)
                self.assertIn(marker, detail)

    def test_not_comparable_expected_matches_charter_fixture(self):
        # §29 Q11：0004（base_undeclared）+ null 声明 + 无键断言；本世界比 §25.9 多一条无键断言
        _, rows = acceptance._collation_expected(old_view(), self.new_view)
        self.assertEqual(
            rows,
            [
                not_comparable(None, None, "missing_collation_key"),
                not_comparable(None, "as_qizheng_900016", "missing_collation_key"),
                not_comparable(4, None, "base_undeclared"),
            ],
        )


if __name__ == "__main__":
    unittest.main()

"""M7 E 波：独立增量 Gate `evaluate_assembly` 的单元测试与篡改矩阵（act/impl-07/25）。

检查清单**逐字沿用** `act/06.yaml`（13 项检查名与顺序、篡改矩阵），四处校准见 `act/25.yaml` 第一节：

1. 场景：`test_r2_incremental_all_checks_pass`（fixture r1→r2）+ `test_real_book_second_round_all_checks_pass`
2. `affected_scope_exact`：`report.affected_entity_ids == Gate 自算闭包`，且 `rebuilt ⊆ 自算闭包`
3. §14.1 静默覆盖：`test_tamper_view_change_silently_reverted_to_base`
4. §10.1 配对隔离用行为验证：`test_tamper_relation_without_deterministic_basis`

本文件只读 fixture / 真书账本（**副本**），不写 `var/`。
"""

import ast
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from pipeline.assembly import fixture_seed
from pipeline.assembly import orchestrate
from pipeline.assembly import step as step_module
from pipeline.assembly.canonical import content_sha256
from pipeline.assembly.gate import ASSEMBLY_CHECK_ORDER, evaluate_assembly
from pipeline.assembly.inputs import resolve_m7_inputs
from pipeline.assembly.step import run_m7
from pipeline.assembly.tests.test_incremental_orchestration import (
    fixture_views,
    load_manifest,
    round1_knowledge,
)
from pipeline.assembly.tests.fixture_decisions import decisions_for_round
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"
REAL_LEDGER = ROOT / "var" / "ledgers" / "qianyuan_w8"

#: 合法 `rev_` 号（只当基底占位；不进任何账本正本）
BASE_REV = "rev_000000000000000000000000000000f1"

#: ACT 29（§25.9）之后，基底里唯一**不在闭包内**的对象是这条流派视图（r2 的三条断言都进了对勘触点）
UNTOUCHED_BASE_ID = "sv_00000000000000000000000000000001"

EXPECTED_CHECKS = (
    "schema_and_ids",
    "identity_preserved",
    "allocation_monotonic",
    "provenance_complete",
    "view_objects_unaltered",
    "untouched_byte_identical",
    "affected_scope_exact",
    "collation_comparable_only",
    "no_silent_fold",
    "first_layer_display",
    "identity_delta_contract",
    "maturity_not_synthesized",
    "decisions_consistent",
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class IncrementalGateCase(unittest.TestCase):
    """fixture r1 → ed99 视图的增量轮：13 项检查必须全过，篡改后必须逐项转红。"""

    @classmethod
    def setUpClass(cls):
        manifest = load_manifest()
        cls.base = round1_knowledge(manifest)
        cls.views = [fixture_views(manifest)[1]]
        # 第二版次带一条同名歧义提案（另一个 pat_ 号与基底格局同名）→ 决定集读夹具数据
        cls.decisions = decisions_for_round(2)
        cls.outcome = orchestrate.assemble(
            cls.base,
            cls.views,
            cls.decisions,
            incremental=True,
            base_snapshot_revision_id=BASE_REV,
        )
        assert cls.outcome["status"] == "complete", cls.outcome["status"]

    # ------------------------------------------------------------------ 便捷入口
    def evaluate(self, *, knowledge=None, base_knowledge=None, views=None, decisions=None,
                 identity_delta=None, collation=None, report=None):
        result = self.outcome["result"]
        return evaluate_assembly(
            base_knowledge=self.base if base_knowledge is None else base_knowledge,
            views=self.views if views is None else views,
            decisions=self.decisions if decisions is None else decisions,
            knowledge=result["knowledge"] if knowledge is None else knowledge,
            identity_delta=result["identity_delta"] if identity_delta is None else identity_delta,
            collation=result["collation"] if collation is None else collation,
            report=self.outcome["report"] if report is None else report,
        )

    def evaluate_tampered(self, tweak, **overrides):
        knowledge = copy.deepcopy(self.outcome["result"]["knowledge"])
        tweak(knowledge)
        return self.evaluate(knowledge=knowledge, **overrides)

    def assert_only_check_failed(self, res, name):
        self.assertFalse(res["checks"][name]["passed"], "检查 %s 未转红：%s" % (name, res["checks"][name]))
        self.assertFalse(res["passed"], "单点篡改后总体判定必须为 False")

    # ------------------------------------------------------- 具名用例 1（校准 1）
    def test_r2_incremental_all_checks_pass(self):
        res = self.evaluate()
        self.assertEqual(list(res["checks"].keys()), list(EXPECTED_CHECKS), "检查名与顺序须逐字固定")
        self.assertEqual(list(ASSEMBLY_CHECK_ORDER), list(EXPECTED_CHECKS))
        failed = {name: chk["detail"] for name, chk in res["checks"].items() if not chk["passed"]}
        self.assertEqual(failed, {}, "fixture r1→r2 增量轮必须 13 项全过：%s" % failed)
        self.assertTrue(res["passed"])

    # ------------------------------------------------------- 具名用例 2（真书副本）
    def test_real_book_second_round_all_checks_pass(self):
        if not (REAL_LEDGER / "ledger.sqlite").is_file():
            self.skipTest("本机无 var/ledgers/qianyuan_w8：真书第二轮用例跳过（回报已注明）")

        tmp = tempfile.mkdtemp(prefix="m7_e_gate_real_")
        self.addCleanup(shutil.rmtree, tmp, True)
        work = Path(tmp) / REAL_LEDGER.name
        shutil.copytree(REAL_LEDGER, work)  # 正本只读，实跑在副本上
        service = LedgerService(work)
        self.addCleanup(service.close)

        rows = service.store.conn.execute(
            "SELECT r.artifact_revision_id FROM stage_packages sp "
            "JOIN artifact_revisions r ON r.artifact_id = sp.artifact_id "
            "WHERE sp.stage='m6' AND r.status='sealed' ORDER BY r.created_at DESC, r.rowid DESC"
        ).fetchall()
        self.assertTrue(rows, "真书账本里没有 sealed 的 m6 包")
        inputs = resolve_m7_inputs(service, [rows[0][0]])
        views = [
            {
                "source_id": inputs["candidate_set"].get("source_id"),
                "candidate_set": inputs["candidate_set"],
                "reviewed_edition": inputs["reviewed_edition"],
            }
        ]
        base = load_json(FIXTURE / "expected" / "snapshot_r1.json")
        outcome = orchestrate.assemble(
            base, views, [], incremental=True, base_snapshot_revision_id=BASE_REV
        )
        self.assertEqual(outcome["status"], "complete", "真书第二轮不得停在 awaiting_human")

        res = evaluate_assembly(
            base_knowledge=base,
            views=views,
            decisions=[],
            knowledge=outcome["result"]["knowledge"],
            identity_delta=outcome["result"]["identity_delta"],
            collation=outcome["result"]["collation"],
            report=outcome["report"],
        )
        failed = {name: chk["detail"] for name, chk in res["checks"].items() if not chk["passed"]}
        self.assertEqual(failed, {}, "真书第二轮必须 13 项全过：%s" % failed)

    # ------------------------------------------------------- 具名用例 3（独立性）
    def test_gate_does_not_import_assembly_logic(self):
        gate_path = Path(__file__).resolve().parents[1] / "gate.py"
        tree = ast.parse(gate_path.read_text(encoding="utf-8"), filename="gate.py")
        forbidden = ("matcher", "apply", "incremental", "orchestrate", "genesis")
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.add(node.module or "")
                modules.update(alias.name for alias in node.names)
        offenders = sorted(m for m in modules if any(f in m for f in forbidden))
        self.assertEqual(offenders, [], "Gate 不得 import 被验对象的实现：%s" % offenders)

    # ------------------------------------------------------------------ 篡改矩阵
    def test_tamper_drop_base_entity_without_delta(self):
        def tweak(knowledge):
            knowledge["concepts"] = [c for c in knowledge["concepts"] if c["concept_id"] != "co_qizheng_900001"]

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "identity_preserved")

    def test_tamper_revive_retired_id(self):
        def tweak(knowledge):
            knowledge["retired_entity_ids"] = ["as_qizheng_900002"]  # 该号在总账里仍是活对象

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "identity_preserved")

    def test_tamper_new_id_not_above_allocation(self):
        def tweak(knowledge):
            clone = copy.deepcopy(knowledge["patterns"][0])
            clone["pattern_id"] = "pat_qizheng_000001"  # 小于基底 id_allocation 900001
            clone["name"] = "伪造新号"
            knowledge["patterns"] = sorted([clone] + knowledge["patterns"], key=lambda p: p["pattern_id"])

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "allocation_monotonic")

    def test_tamper_drop_view_school_view(self):
        def tweak(knowledge):
            target = "sv_00000000000000000000000000000002"  # 只在视图里出现过的流派视图
            knowledge["school_views"] = [s for s in knowledge["school_views"] if s["school_view_id"] != target]
            for group in knowledge["conflict_groups"]:
                group["member_school_view_ids"] = [
                    m for m in group["member_school_view_ids"] if m != target
                ]

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "no_silent_fold")

    def test_tamper_provenance_hash(self):
        def tweak(knowledge):
            pattern = [p for p in knowledge["patterns"] if p["pattern_id"] == "pat_qizheng_900001"][0]
            row = [r for r in pattern["provenance"] if r["source_id"] == "src_sanche_ed99"][0]
            row["content_sha256"] = "0" * 64  # 视图来源行的内容哈希被改

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "view_objects_unaltered")

    def test_tamper_assertion_text_sha(self):
        # ACT 29（§25.1）：断言号不再跨版次沿用——`as_qizheng_900001` 属 ed01，ed99 的视图建的是 900005。
        # 篡改对象改成**本轮视图新建的断言**（断言意图不变：改视图对象 → view_objects_unaltered 转红）。
        def tweak(knowledge):
            assertion = [a for a in knowledge["assertions"] if a["assertion_id"] == "as_qizheng_900005"][0]
            assertion["text_sha256"] = "0" * 64

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "view_objects_unaltered")

    def test_tamper_untouched_entity_bytes(self):
        # ACT 29（§25.9）：ed99 现在声明 `sanche-0002` 缺文，`as_qizheng_900002` 因此**落在闭包内**
        # （omission 的旧版端点）。闭包外的基底对象只剩流派视图——改它（断言意图不变）。
        def tweak(knowledge):
            school_view = [s for s in knowledge["school_views"] if s["school_view_id"] == UNTOUCHED_BASE_ID][0]
            school_view["changes_current_judgment"] = False  # 该号在闭包之外

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "untouched_byte_identical")

    def test_tamper_report_affected_missing_one(self):
        report = copy.deepcopy(self.outcome["report"])
        report["affected_entity_ids"] = [
            e for e in report["affected_entity_ids"] if e != "co_qizheng_900001"
        ]
        res = self.evaluate(report=report)
        self.assert_only_check_failed(res, "affected_scope_exact")

    def test_tamper_report_affected_extra_one(self):
        # ACT 29：`as_qizheng_900002` 现在在闭包内，改多它不再改变等式 → 换成闭包外号（意图不变）
        report = copy.deepcopy(self.outcome["report"])
        report["affected_entity_ids"] = sorted(
            list(report["affected_entity_ids"]) + [UNTOUCHED_BASE_ID]
        )
        res = self.evaluate(report=report)
        self.assert_only_check_failed(res, "affected_scope_exact")

    def test_tamper_rebuilt_outside_closure(self):
        # ACT 29：同上——多出的号必须真的在闭包外
        report = copy.deepcopy(self.outcome["report"])
        report["rebuilt_entity_ids"] = sorted(
            list(report["rebuilt_entity_ids"]) + [UNTOUCHED_BASE_ID]
        )
        res = self.evaluate(report=report)
        self.assert_only_check_failed(res, "affected_scope_exact")

    def test_tamper_omission_on_undeclared_unit(self):
        def tweak(knowledge):
            # `sanche-0001` 两侧都声明 present，把它记成 omission 就是无依据的对勘关系。
            # ACT 29：r2 的关系表里第一条已是 addition；**按 kind 取**对齐关系（不再按下标 0）。
            alignment = [rel for rel in knowledge["relations"] if rel["relation_kind"] == "alignment"][0]
            alignment["relation_kind"] = "omission"

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "collation_comparable_only")

    def test_tamper_relation_without_deterministic_basis(self):
        """校准 4（§10.1）：alias / merge / omission / addition 必须能由 Gate 独立推出的确定性依据解释。"""

        def tweak(knowledge):
            knowledge["relations"] = sorted(
                knowledge["relations"]
                + [
                    {
                        "relation_key": "alias_of:000000000000000000000000000000ff",
                        "from_entity_id": "as_qizheng_900001",
                        "to_entity_id": "as_qizheng_900002",
                        "relation_kind": "alias_of",
                        "detail": {},
                        "resolution": {"mode": "auto", "proposal_key": "merge:0a380cd067938cea2c949bbec2c3ed94"},
                    }
                ],
                key=lambda rel: rel["relation_key"],
            )

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "collation_comparable_only")

    def test_tamper_first_layer_display_false(self):
        def tweak(knowledge):
            knowledge["conflict_groups"][0]["first_layer_display"] = False

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "first_layer_display")

    def test_tamper_delta_bad_change_type(self):
        delta = copy.deepcopy(self.outcome["result"]["identity_delta"])
        delta["entries"] = [
            {
                "from_entity_id": "as_qizheng_900002",
                "to_entity_ids": ["as_qizheng_900001"],
                "change_type": "vanished",  # 不在闭集 {migrated, merged, split, retired}
                "entity_kind": "assertion",
                "reason_ref": {"kind": "proposal", "proposal_key": "merge:0a380cd067938cea2c949bbec2c3ed94"},
            }
        ]
        res = self.evaluate(identity_delta=delta)
        self.assert_only_check_failed(res, "identity_delta_contract")

    def test_tamper_delta_unresolvable_reason_ref(self):
        delta = copy.deepcopy(self.outcome["result"]["identity_delta"])
        delta["entries"] = [
            {
                "from_entity_id": "as_qizheng_900002",
                "to_entity_ids": ["as_qizheng_900001"],
                "change_type": "merged",
                "entity_kind": "assertion",
                "reason_ref": {"kind": "proposal", "proposal_key": "nothing:deadbeef"},
            }
        ]
        res = self.evaluate(identity_delta=delta)
        self.assert_only_check_failed(res, "identity_delta_contract")

    def test_tamper_split_without_allocation(self):
        delta = copy.deepcopy(self.outcome["result"]["identity_delta"])
        delta["entries"] = [
            {
                "from_entity_id": "as_qizheng_900002",
                "to_entity_ids": ["as_qizheng_900001", "as_qizheng_900003"],
                "change_type": "split",
                "entity_kind": "assertion",
                "reason_ref": {"kind": "proposal", "proposal_key": "merge:0a380cd067938cea2c949bbec2c3ed94"},
            }
        ]
        res = self.evaluate(identity_delta=delta)
        self.assert_only_check_failed(res, "identity_delta_contract")

    # ------------------------------------------------- ACT 28 五（回到草稿口径）
    def test_identity_delta_reason_ref_must_be_in_round_proposal_keys(self):
        """delta 每条的 `reason_ref.proposal_key` 必须出现在 `report.round_proposal_keys` 里。

        E 波的放宽口径（总账里已落地的键 ∪ 决定 ∪ 沿用）已按 CHARTER §16.1 第二条删掉：
        只在别处出现、不在本轮提案集里的键必须判 FAIL；`report` 缺该字段同样 FAIL，
        **不许静默退回旧口径**。
        """
        # 这个键只在「别处」（report.carried，即 E 波放宽口径里的「沿用」）出现，
        # 不在本轮提案集里 → 新口径必须判 FAIL
        landed = "conflict:0123456789abcdef0123456789abcdef"
        report = copy.deepcopy(self.outcome["report"])
        self.assertNotIn(landed, report["round_proposal_keys"])
        report["carried"] = sorted(list(report["carried"]) + [landed])

        def delta_with(key):
            return {
                "entries": [
                    {
                        "from_entity_id": "as_qizheng_900002",
                        "to_entity_ids": [],
                        "change_type": "retired",
                        "entity_kind": "assertion",
                        "reason_ref": {"kind": "proposal", "proposal_key": key},
                    }
                ]
            }

        # (1) 不在本轮提案集里的键 → FAIL
        res = self.evaluate(identity_delta=delta_with(landed), report=report)
        self.assert_only_check_failed(res, "identity_delta_contract")
        self.assertIn("不在本轮提案集内", res["checks"]["identity_delta_contract"]["detail"])

        # (2) report 缺 round_proposal_keys → FAIL（不静默退回）
        stripped = {key: value for key, value in report.items() if key != "round_proposal_keys"}
        res2 = self.evaluate(identity_delta=delta_with(landed), report=stripped)
        self.assert_only_check_failed(res2, "identity_delta_contract")
        self.assertIn("round_proposal_keys", res2["checks"]["identity_delta_contract"]["detail"])

        # (3) 本轮真有的提案键 → 该条检查通过
        res3 = self.evaluate(
            identity_delta=delta_with(sorted(report["round_proposal_keys"])[0]), report=report
        )
        self.assertTrue(
            res3["checks"]["identity_delta_contract"]["passed"],
            res3["checks"]["identity_delta_contract"]["detail"],
        )

    def test_tamper_synthesized_pattern_status(self):
        def tweak(knowledge):
            knowledge["patterns"][0]["content_status"] = "machine_extracted"

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "maturity_not_synthesized")

    def test_tamper_human_mode_without_decision(self):
        def tweak(knowledge):
            # 没有任何人工决定，却把关系记成 mode=human
            knowledge["relations"][0]["resolution"] = {
                "mode": "human",
                "proposal_key": knowledge["relations"][0]["resolution"]["proposal_key"],
            }

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "decisions_consistent")

    def test_tamper_relation_key_looks_like_registered_id(self):
        def tweak(knowledge):
            knowledge["relations"][0]["relation_key"] = "rev_00000000000000000000000000000009"

        res = self.evaluate_tampered(tweak)
        self.assert_only_check_failed(res, "schema_and_ids")

    # ---------------------------------------------- 校准 3：静默覆盖（§14.1）
    def test_tamper_view_change_silently_reverted_to_base(self):
        """视图候选带着基底号、内容改了；总账用基底旧版把它拷回 → 改动丢了且不报错。

        这正是 §14.1 点名要堵的洞：只有「对照**视图**版本」的检查才抓得住它。
        """
        views = copy.deepcopy(self.views)
        views[0]["candidate_set"]["assertions"][0]["proposition"] = "三辰通載（第二版次改文）"
        res = self.evaluate(views=views)  # 总账仍是基底版内容，apply 侧不报任何错
        self.assertFalse(res["checks"]["view_objects_unaltered"]["passed"])
        self.assertFalse(res["passed"])

        # Pattern 侧同理：视图候选改了自己的名字，总账里还是基底版
        views2 = copy.deepcopy(self.views)
        views2[0]["candidate_set"]["patterns"][0]["name"] = "三辰通載貴格（第二版次改名）"
        res2 = self.evaluate(views=views2)
        self.assertFalse(res2["checks"]["view_objects_unaltered"]["passed"])
        self.assertFalse(res2["passed"])


class ReworkGateCase(unittest.TestCase):
    """同书返工轮（r2 → ed01r2，带一条 `merge_entities` 人工决定）在 Gate 上的可判定性。

    ACT 28 / CHARTER §22.1：§21④ 把合并的落点定在 IdentityDelta（不写 `merged_into` 关系），
    而 E 波的 `decisions_consistent` 原来只在 `relations` / `conflict_groups` 里找决定的落点 ——
    于是任何合并、拆分决定都**恒不能通过**。授权把 IdentityDelta 计入落点，口径写严：
      ① merge / split 决定必须恰有一条与之对应的 delta（类型必须对应）；
      ② 反向：delta 里的每条 merged / split 必须有决定（retired 来自 R11 自动提案，不要求）。
    """

    @classmethod
    def setUpClass(cls):
        manifest = load_manifest()
        plan = yaml.safe_load(
            (FIXTURE / manifest["expected"]["snapshot_revisions"]).read_text(encoding="utf-8")
        )
        cls.base = load_json(FIXTURE / manifest["expected"]["round2"])
        cls.base_rev = plan["revisions"][1]["snapshot_revision_id"]
        rework = manifest["rework"]
        view_dir = FIXTURE / rework["views_dir"]
        cls.views = [
            {
                "source_id": rework["source_id"],
                "candidate_set": load_json(view_dir / "candidate_set.json"),
                "reviewed_edition": load_json(view_dir / "reviewed_edition.json"),
            }
        ]
        cls.decisions = decisions_for_round(3)
        cls.outcome = orchestrate.assemble(
            cls.base,
            cls.views,
            cls.decisions,
            incremental=True,
            base_snapshot_revision_id=cls.base_rev,
        )
        assert cls.outcome["status"] == "complete", cls.outcome["status"]

    def evaluate(self, *, decisions=None, identity_delta=None):
        result = self.outcome["result"]
        return evaluate_assembly(
            base_knowledge=self.base,
            views=self.views,
            decisions=self.decisions if decisions is None else decisions,
            knowledge=result["knowledge"],
            identity_delta=result["identity_delta"] if identity_delta is None else identity_delta,
            collation=result["collation"],
            report=self.outcome["report"],
        )

    def assert_only_check_failed(self, res, name):
        self.assertFalse(res["checks"][name]["passed"], "检查 %s 未转红：%s" % (name, res["checks"][name]))
        self.assertFalse(res["passed"], "单点篡改后总体判定必须为 False")

    # ------------------------------------------------------- 具名用例（返工轮全过）
    def test_rework_round_all_checks_pass(self):
        res = self.evaluate()
        failed = {name: c["detail"] for name, c in res["checks"].items() if not c["passed"]}
        self.assertEqual(failed, {}, "同书返工轮（含 merge_entities 决定）必须 13 项全过：%s" % failed)
        self.assertTrue(res["passed"])

    # ------------------------------------------------------- 篡改矩阵（CHARTER §22.1）
    def test_tamper_merge_decision_without_delta(self):
        """①：决定有，对应的 merged delta 没了 → FAIL。"""
        delta = copy.deepcopy(self.outcome["result"]["identity_delta"])
        delta["entries"] = [e for e in delta["entries"] if e["change_type"] != "merged"]
        res = self.evaluate(identity_delta=delta)
        self.assert_only_check_failed(res, "decisions_consistent")
        detail = res["checks"]["decisions_consistent"]["detail"]
        self.assertIn("merged", detail, "必须点出缺的是哪种 delta: %s" % detail)

    def test_tamper_merged_delta_without_decision(self):
        """②：无决定却出现一条 merged delta → FAIL（retired 才允许无决定）。"""
        delta = copy.deepcopy(self.outcome["result"]["identity_delta"])
        orphan_key = "merge:b25dfbab46aae82540df6a911f52fc89"  # 本轮真实生成过的键（R04 自动 attach）
        self.assertIn(orphan_key, self.outcome["report"]["round_proposal_keys"])
        self.assertNotIn(
            orphan_key,
            [item["proposal_key"] for item in self.decisions],
            "前置：这个键上没有人工决定",
        )
        delta["entries"].append(
            {
                "change_type": "merged",
                "entity_kind": "pattern",
                "from_entity_id": "pat_qizheng_900003",
                "to_entity_ids": ["pat_qizheng_900001"],
                "reason_ref": {"kind": "proposal", "proposal_key": orphan_key},
            }
        )
        delta["entries"] = sorted(
            delta["entries"], key=lambda entry: (entry["change_type"], entry["from_entity_id"])
        )
        res = self.evaluate(identity_delta=delta)
        self.assert_only_check_failed(res, "decisions_consistent")
        detail = res["checks"]["decisions_consistent"]["detail"]
        self.assertIn(orphan_key, detail, "必须点出没有决定的那条 delta 键: %s" % detail)

    def test_tamper_delta_change_type_mismatches_decision(self):
        """①：决定的选项与 delta 的 change_type 对不上 → FAIL。"""
        decisions = copy.deepcopy(self.decisions)
        for item in decisions:
            if item["choice"] == "merge_entities":
                item["choice"] = "split"
        res = self.evaluate(decisions=decisions)
        self.assert_only_check_failed(res, "decisions_consistent")
        detail = res["checks"]["decisions_consistent"]["detail"]
        self.assertIn("split", detail, "必须点出类型不符: %s" % detail)


class IncrementalGateWiringTest(unittest.TestCase):
    """第三节：增量轮在写 Snapshot **之前** 过 Gate；不过即失败封存。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="m7_e_gate_ledger_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.service = LedgerService(Path(self.tmp) / "ledger")
        self.addCleanup(self.service.close)
        self.manifest = load_manifest()
        self.seeded = fixture_seed.seed_release_package(self.service, FIXTURE)["editions"]
        self.ed01, self.ed99 = self.manifest["editions"][0], self.manifest["editions"][1]

    def _run_first_round(self):
        first = run_m7(
            self.service,
            self.ed01["edition_part_artifact_id"],
            technique_id=self.manifest["technique_id"],
            reviewed_package_revision_ids=[
                self.seeded[self.ed01["edition_key"]]["m6_package_revision_id"]
            ],
            id_range=self.manifest["id_range"],
        )
        self.assertEqual(first["status"], "succeeded")
        return first

    def _run_second_round(self, base_revision_id, decisions=None):
        return run_m7(
            self.service,
            self.ed99["edition_part_artifact_id"],
            technique_id=self.manifest["technique_id"],
            reviewed_package_revision_ids=[
                self.seeded[self.ed99["edition_key"]]["m6_package_revision_id"]
            ],
            base_snapshot_revision_id=base_revision_id,
            id_range=self.manifest["id_range"],
            # 同名歧义（R03b）须人工裁定：决定集是夹具数据，用例不手写
            decisions=decisions_for_round(2) if decisions is None else decisions,
        )

    def _snapshot_revisions(self):
        return [
            row[0]
            for row in self.service.store.conn.execute(
                "SELECT r.artifact_revision_id FROM artifact_revisions r "
                "JOIN artifacts a ON a.artifact_id = r.artifact_id "
                "WHERE a.artifact_type='canonical_snapshot' AND r.status='sealed'"
            ).fetchall()
        ]

    def test_incremental_round_fails_closed_on_gate_failure(self):
        first = self._run_first_round()
        fake = {
            "passed": False,
            "checks": {
                "affected_scope_exact": {"passed": False, "detail": "注入的 Gate 失败"},
            },
        }
        with mock.patch.object(step_module, "evaluate_assembly", lambda **kwargs: fake):
            second = self._run_second_round(first["snapshot_revision_id"])

        self.assertEqual(second["status"], "failed", "Gate 不过的增量轮必须失败封存")
        self.assertIsNone(second["snapshot_revision_id"], "Gate 不过时不得写 Snapshot")
        self.assertEqual(
            self._snapshot_revisions(),
            [first["snapshot_revision_id"]],
            "Gate 不过时账本里只能有基底那一条 Snapshot 修订",
        )
        self.assertEqual(
            self.service.get_step_run(second["step_run_id"])["status"],
            "failed",
            "不得留下跑着的 StepRun",
        )

    def test_incremental_round_report_carries_gate_result(self):
        first = self._run_first_round()
        second = self._run_second_round(first["snapshot_revision_id"])
        self.assertEqual(second["status"], "succeeded", second.get("error"))
        self.assertIsNotNone(second["snapshot_revision_id"])

        revision = self.service.get_revision(second["validation_report_revision_id"])
        raw = self.service.objects.get(revision["sha256"]).decode("utf-8")
        self.assertNotIn("pending_e_wave", raw, "增量轮的 Gate 结果不许再是占位符")
        doc = json.loads(raw)
        gate = doc["incremental_gate"]
        self.assertIsInstance(gate, dict, "validation_report 必须携带真实的 Gate 结果：%r" % (gate,))
        self.assertTrue(gate["passed"])
        # validation_report 是 sort_keys 的规范 JSON：键序在落盘时重新排序，比集合即可
        self.assertEqual(sorted(gate["checks"].keys()), sorted(EXPECTED_CHECKS))
        self.assertTrue(doc["passed"])


if __name__ == "__main__":
    unittest.main()

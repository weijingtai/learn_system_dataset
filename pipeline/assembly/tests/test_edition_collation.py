"""ACT 29（I 波）：多版次对勘的具名用例 —— CHARTER §25 的可执行口径。

本文件是「先红后绿」的**红侧证据**：取证命令与 Red 原文见
`/Users/jingtaiwei/tmux-agents/runs/fb-m7-i.report.md`。

覆盖 ACT 29 `tests_first` 的**引擎侧**具名用例（第十二条 R15 全栈用例照写）。

范围（CHARTER §26，ACT 30 拆波后收窄）：本文件**不碰** `gate.py` / `acceptance.py`；
三条 Gate 篡改用例（自环 / `null` 端点出现在 alignment / 增文方向写反）归 ACT 30。

口径来源（逐条对齐，不自行发明）：
- §25.1 断言号属于一个版次；自环关系拒收
- §25.2 R07/R08/R07b 比**主体**（`subject_entity_id` 裁决到同一正式对象），不比断言号
- §25.3 同 `source_id` 的单元一律不配对
- §25.4 方向按角色定（新版 = 本轮视图，旧版 = 基底），不按 `source_id` 字典序
- §25.5 `editions[].collation_units` 必填、按 `collation_key` 升序；基底声明只从这里读
- §25.6 关系两端与 `null` 端点只许 addition / omission
- §25.7 提案带 `targets = [from, to]`；apply 只按 targets 落关系
- §25.8 Gate 独立重算
- §25.9 fixture 与判据
- R15（CHARTER §19.1）：至少一条用例用真实形状输入走完全栈
"""

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"

from pipeline.assembly import apply as m7_apply  # noqa: E402
from pipeline.assembly import genesis, incremental  # noqa: E402
from pipeline.assembly.model import (  # noqa: E402
    empty_snapshot_knowledge,
    validate_snapshot_knowledge,
)
from pipeline.ledger.errors import DuplicateIdentifier, SchemaViolation  # noqa: E402

TECH = "qizheng"
SRC_ED01 = "src_sanche_ed01"
SRC_ED02 = "src_sanche_ed02"

SPAN_A = "ss_sanche_ed01_p0001_s01"  # 三辰通載
SPAN_B = "ss_sanche_ed01_p0001_s02"  # （宋）錢如璧撰
SPAN_C = "ss_sanche_ed01_p0003_s03"  # 三辰通載目錄
SPAN_D = "ss_sanche_ed01_p0003_s05"  # 貴格之圗

CK1 = "sanche-0001"
CK2 = "sanche-0002"
CK3 = "sanche-0003"
CK4 = "sanche-0004"
CK5 = "sanche-0005"

A1 = "as_qizheng_000001"   # ed01 · 0001 · 三辰通載 · 主体 PAT1
A2 = "as_qizheng_000002"   # ed01 · 0002 · （宋）錢如璧撰 · 主体 PAT2
A3 = "as_qizheng_000003"   # ed01 · 0003 · 貴格之圗 · 主体 PAT1
E1 = "as_qizheng_000101"   # ed02 自己发的号 · 0001 · 三辰通載（同主体同文）
E3 = "as_qizheng_000103"   # ed02 · 0003 · 貴格之圖（同主体异文）
E4 = "as_qizheng_000104"   # ed02 · 0004 · 基底**未声明**该单元
E5 = "as_qizheng_000105"   # ed02 · 0005 · 基底声明 present:false → 增文
PAT1 = "pat_qizheng_000001"
PAT2 = "pat_qizheng_000002"
PAT_NAME = "三辰通載貴格"
PAT2_NAME = "錢如璧撰述"

ART_ED1 = "art_" + "0" * 30 + "e1"
ART_ED2 = "art_" + "0" * 30 + "e2"
ID_RANGE = {"pat_%s" % TECH: [1, 999999]}
#: `genesis.assemble_genesis` 的口径是 `{"pattern": [start, end]}`
GENESIS_ID_RANGE = {"pattern": [1, 999999]}


def const(prefix: str, suffix: str) -> str:
    body = ("0" * (32 - len(suffix)) + suffix).lower()
    return prefix + body


CS1 = const("rev_", "11")
CP1 = const("rev_", "12")
VAL1 = const("rev_", "13")
CS2 = const("rev_", "21")
CP2 = const("rev_", "22")
VAL2 = const("rev_", "23")


# ---------------------------------------------------------------- 文档构造
def ev(span_id: str) -> dict:
    return {
        "source_span_id": span_id,
        "start_offset": 0,
        "end_offset": 4,
        "quote_sha256": "a" * 64,
    }


def assertion(aid: str, proposition: str, collation_key, span_id: str) -> dict:
    return {
        "assertion_id": aid,
        "proposition_id": "pr_qizheng_%s" % aid.split("_")[-1],
        "proposition": proposition,
        "relation": "supports",
        "evidence": [ev(span_id)],
        "conditions": [],
        "exceptions": [],
        "concept_refs": [],
        "school_ids": [],
        "layer": "general",
        "content_status": "machine_extracted",
        "collation_key": collation_key,
        "origin": {"lane": "main", "item_index": 0},
    }


def pattern(name: str, assertion_ids, pattern_id=None) -> dict:
    return {
        "pattern_id": pattern_id,
        "name": name,
        "assertion_ids": list(assertion_ids),
        "evidence": [],
        "interpretation": "用例宿主",
        "interpretation_status": "captured",
        "recognition_rule_status": "not_captured",
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 0},
    }


def candidate_set(source_id, part, *, assertions=(), patterns=(), units=()) -> dict:
    doc = {
        "schema_version": "0.1.0-draft",
        "synthetic": True,
        "technique_id": TECH,
        "source_id": source_id,
        "edition_part_artifact_id": part,
        "evidence_level": "glyphbox_level",
        "span_layer": "structural",
        "source_channels": {"assertion": {"main": "text"}},
        "collation_units": list(units),
        "assertions": list(assertions),
        "patterns": list(patterns),
        "school_views": [],
        "concept_mentions": [],
        "new_concept_candidates": [],
        "rejected": [],
        "disputes": [],
    }
    doc["counts"] = {
        key: len(doc[key])
        for key in (
            "assertions", "patterns", "school_views", "concept_mentions",
            "new_concept_candidates", "rejected", "disputes",
        )
    }
    return doc


def reviewed_edition(part, *, cs_rev, cp_rev, val_rev, approved=(), links=(), source_id) -> dict:
    approved_items = []
    decisions = []
    for index, (entity_id, kind) in enumerate(approved):
        rev = const("rev_", "9%02d" % (index + 1))
        approved_items.append(
            {
                "entity_id": entity_id,
                "kind": kind,
                "artifact_revision_id": cs_rev,
                "content_status": "machine_extracted",
                "decision_revision_ids": [rev],
            }
        )
        decisions.append(
            {
                "decision_revision_id": rev,
                "queue_item_id": "%s#review_source_fidelity" % entity_id,
                "target_entity_id": entity_id,
                "seen_artifact_revision_id": cs_rev,
                "current_target_revision_id": cs_rev,
                "modified_revision_id": None,
                "decision_type": "review_source_fidelity",
                "verdict": "accept",
                "standing": "active",
                "carried_from_revision_id": None,
                "carried_to_revision_id": None,
                "trigger_correction_request_id": None,
                "synthetic_fixture": True,
            }
        )
    return {
        "schema_version": "0.1.0-draft",
        "synthetic": True,
        "edition_part_artifact_id": part,
        "candidate_set_revision_id": cs_rev,
        "candidate_package_revision_id": cp_rev,
        "validation_package_revision_id": val_rev,
        "approved": approved_items,
        "rejected": [],
        "decisions": decisions,
        "evidence_links": [
            {
                "entity_id": entity_id,
                "source_span_id": span_id,
                "start_offset": 0,
                "end_offset": 4,
                "quote_sha256": "a" * 64,
                "corpus_spans_revision_id": const("rev_", "a01"),
            }
            for entity_id, span_id in links
        ],
        "school_views": [],
        "correction_request_revision_ids": [],
        "rework_impact_report_revision_id": None,
        "unresolved_count": 0,
        "source_id": source_id,
    }


# ---------------------------------------------------------------- 两版次视图
def view_ed01() -> dict:
    """基底版次（ed01）：0001/0002/0003 声明 present，另声明 0005 present:false（§25.9）。"""
    cset = candidate_set(
        SRC_ED01,
        ART_ED1,
        assertions=[
            assertion(A1, "三辰通載", CK1, SPAN_A),
            assertion(A2, "（宋）錢如璧撰", CK2, SPAN_B),
            assertion(A3, "貴格之圗", CK3, SPAN_D),
        ],
        patterns=[
            pattern(PAT_NAME, [A1, A3], PAT1),
            pattern(PAT2_NAME, [A2], PAT2),
        ],
        units=[
            {"collation_key": CK1, "present": True},
            {"collation_key": CK2, "present": True},
            {"collation_key": CK3, "present": True},
            {"collation_key": CK5, "present": False},
        ],
    )
    reviewed = reviewed_edition(
        ART_ED1,
        cs_rev=CS1,
        cp_rev=CP1,
        val_rev=VAL1,
        approved=[
            (A1, "assertion"), (A2, "assertion"), (A3, "assertion"),
            (PAT1, "pattern"), (PAT2, "pattern"),
        ],
        links=[(A1, SPAN_A), (A2, SPAN_B), (A3, SPAN_D)],
        source_id=SRC_ED01,
    )
    return {"source_id": SRC_ED01, "candidate_set": cset, "reviewed_edition": reviewed}


def view_ed02(*, e1_subject_pattern=PAT1) -> dict:
    """第二版次（ed99 形状）：自己发号的断言 + 四类关系的载体（§25.9）。

    - `E1`（0001）同主体同文 → 对齐
    - `E3`（0003）同主体异文 → 异文
    - `E4`（0004）基底未声明 → `not_comparable`，不许出增文
    - `E5`（0005）有断言且 present，基底声明 present:false → 增文
    - 0002 声明 present:false → 缺文（本视图**没有** 0002 的断言）
    """
    cset = candidate_set(
        SRC_ED02,
        ART_ED2,
        assertions=[
            assertion(E1, "三辰通載", CK1, SPAN_A),
            assertion(E3, "貴格之圖", CK3, SPAN_D),
            assertion(E4, "目錄", CK4, SPAN_C),
            assertion(E5, "錢如璧撰", CK5, SPAN_B),
        ],
        patterns=[
            # 默认：E1/E3 同属基底格局 PAT1（与基底两侧主体一致 → 对齐 / 异文）
            # 错配变体：E1 改挂 PAT2（与基底 A1 的主体 PAT1 不同 → R07b 人工），E3 照旧
            pattern(PAT_NAME, [E1, E3] if e1_subject_pattern == PAT1 else [E3], PAT1),
            pattern(PAT2_NAME, [E5] if e1_subject_pattern == PAT1 else [E1, E5], PAT2),
        ],
        units=[
            {"collation_key": CK1, "present": True},
            {"collation_key": CK2, "present": False},
            {"collation_key": CK3, "present": True},
            {"collation_key": CK4, "present": True},
            {"collation_key": CK5, "present": True},
        ],
    )
    reviewed = reviewed_edition(
        ART_ED2,
        cs_rev=CS2,
        cp_rev=CP2,
        val_rev=VAL2,
        approved=[
            (E1, "assertion"), (E3, "assertion"), (E4, "assertion"), (E5, "assertion"),
            (e1_subject_pattern, "pattern"), (PAT2, "pattern"),
        ],
        links=[(E1, SPAN_A), (E3, SPAN_D), (E4, SPAN_C), (E5, SPAN_B)],
        source_id=SRC_ED02,
    )
    return {"source_id": SRC_ED02, "candidate_set": cset, "reviewed_edition": reviewed}


def view_rework_absent(*, drop_id=None) -> dict:
    """同书返工视图：**同 `source_id`**，0002 声明 present:false（F3 的同 source 半边）。"""
    cset = candidate_set(
        SRC_ED01,
        ART_ED1,
        assertions=[assertion(A1, "三辰通載", CK1, SPAN_A), assertion(A3, "貴格之圗", CK3, SPAN_D)],
        patterns=[pattern(PAT_NAME, [A1, A3], PAT1)],
        units=[
            {"collation_key": CK1, "present": True},
            {"collation_key": CK2, "present": False},
            {"collation_key": CK3, "present": True},
        ],
    )
    reviewed = reviewed_edition(
        ART_ED1,
        cs_rev=const("rev_", "21"),
        cp_rev=const("rev_", "22"),
        val_rev=const("rev_", "23"),
        approved=[(A1, "assertion"), (A3, "assertion"), (PAT1, "pattern")],
        links=[(A1, SPAN_A), (A3, SPAN_D)],
        source_id=SRC_ED01,
    )
    return {"source_id": SRC_ED01, "candidate_set": cset, "reviewed_edition": reviewed}


# ---------------------------------------------------------------- 基座与运行
def base_knowledge() -> dict:
    """r1（创世轮）knowledge：由 apply 在空基底上实跑 ed01 视图产出。"""
    return m7_apply.apply_resolutions(
        empty_snapshot_knowledge(TECH, copy.deepcopy(ID_RANGE)), [view_ed01()], [], []
    )["knowledge"]


def propose(base: dict, view: dict, *, round_no: int = 2) -> list:
    return incremental.propose_incremental(base, [view], round_no=round_no)["proposals"]


def apply_round(base: dict, view: dict, *, round_no: int = 2, decisions=()):
    return m7_apply.apply_resolutions(
        base, [view], propose(base, view, round_no=round_no), list(decisions)
    )


def by_rule(proposals, rule_id: str) -> list:
    return [item for item in proposals if item["rule_id"] == rule_id]


def collation_kinds(knowledge: dict) -> list:
    from pipeline.assembly.apply import COLLATION_KINDS

    return [
        rel for rel in knowledge["relations"] if rel["relation_kind"] in COLLATION_KINDS
    ]


def relation_of(knowledge: dict, kind: str) -> dict:
    matches = [
        rel for rel in knowledge["relations"] if rel["relation_kind"] == kind
    ]
    assert len(matches) == 1, "期望恰好一条 %s 关系，实得 %d 条" % (kind, len(matches))
    return matches[0]


def rel(kind, from_id, to_id, *, key_subject=None, detail=None, proposal_key="test:key"):
    return m7_apply._relation_for(
        kind, from_id, to_id, detail or {}, proposal_key, mode="auto",
        key_subject=key_subject if key_subject is not None else [from_id, to_id],
    )


def decision_for(proposal: dict, choice: str) -> dict:
    """按 `apply.DECISION_REQUIRED_FIELDS` 造一条合法决定（夹具外的用例专用）。"""
    return {
        "proposal_set_revision_id": None,
        "proposal_key": proposal["proposal_key"],
        "choice": choice,
        "target_entity_ids": list(proposal.get("targets") or []),
        "seen_revision_id": None,
        "decision_type": proposal.get("decision_type"),
    }


def approve_assertion(view: dict, assertion_id: str, *, cs_rev=None, suffix="997") -> None:
    """给视图补一条已获批断言（用例构造输入，不改变断言意图）。"""
    view["reviewed_edition"]["approved"].append(
        {
            "entity_id": assertion_id,
            "kind": "assertion",
            "artifact_revision_id": cs_rev or CS2,
            "content_status": "machine_extracted",
            "decision_revision_ids": [const("rev_", suffix)],
        }
    )


def dedupe_approved(view: dict) -> dict:
    """`view_ed02(e1_subject_pattern=PAT2)` 会重复登记 PAT2；`apply` 校验 approved 不得重复，
    这里只去重构造输入，不改断言意图。"""
    seen = set()
    unique = []
    for item in view["reviewed_edition"]["approved"]:
        if item["entity_id"] in seen:
            continue
        seen.add(item["entity_id"])
        unique.append(item)
    view["reviewed_edition"]["approved"] = unique
    return view


def collation_subject_proposals(proposals, key: str) -> list:
    return [
        item
        for item in proposals
        if item.get("subject") and item["subject"][0] == "collation" and item["subject"][2] == key
    ]


class EditionCollationTest(unittest.TestCase):
    """全部用例共用基座（r1 = ed01 实跑产物）。"""

    @classmethod
    def setUpClass(cls):
        cls.base = base_knowledge()

    # ------------------------------------------------------------------ §25.1
    def test_view_reusing_other_edition_assertion_id_refused(self):
        """§25.1：视图带着**基底里另一个版次**拥有的 `as_` 号 → DuplicateIdentifier。"""
        view = view_ed02()
        cset = view["candidate_set"]
        # 把 ed02 自己的 0001 断言改成沿用 ed01 的号（同号同命题、只多一条证据）
        cset["assertions"][0]["assertion_id"] = A1
        for pat in cset["patterns"]:
            pat["assertion_ids"] = [A1 if aid == E1 else aid for aid in pat["assertion_ids"]]
        view["reviewed_edition"]["approved"] = [
            dict(item, entity_id=A1) if item["entity_id"] == E1 else item
            for item in view["reviewed_edition"]["approved"]
        ]
        view["reviewed_edition"]["evidence_links"] = [
            dict(link, entity_id=A1) if link["entity_id"] == E1 else link
            for link in view["reviewed_edition"]["evidence_links"]
        ]

        with self.assertRaises(DuplicateIdentifier) as ctx:
            m7_apply.apply_resolutions(
                self.base, [view], propose(self.base, view), []
            )
        self.assertIn("跨版次沿用断言号", str(ctx.exception))

    # ------------------------------------------------------------------ §25.1
    def test_self_loop_relation_refused(self):
        """§25.1：关系两端相同（自环）→ SchemaViolation。"""
        knowledge = copy.deepcopy(self.base)
        knowledge["relations"] = sorted(
            list(knowledge["relations"]) + [rel("alignment", A1, A1, detail={"collation_key": CK1})],
            key=lambda item: item["relation_key"],
        )
        with self.assertRaises(SchemaViolation) as ctx:
            validate_snapshot_knowledge(knowledge)
        self.assertIn("自环", str(ctx.exception))

    # ------------------------------------------------------------------ §25.2
    def test_alignment_links_two_editions_assertions(self):
        """§25.2：对齐连接**两个版次各自的断言**（两个不同的号），按主体裁决到同一正式对象。"""
        view = view_ed02()
        proposals = propose(self.base, view)

        r07 = by_rule(proposals, "R07")
        self.assertEqual(len(r07), 1, "0001 上应当恰有一条 R07，实得 %d 条" % len(r07))
        self.assertEqual(
            r07[0]["targets"],
            [E1, A1],
            "R07 的 targets 必须是 [新版断言, 旧版断言]（两个不同的号）",
        )

        result = apply_round(self.base, view)
        relation = relation_of(result["knowledge"], "alignment")
        self.assertEqual(
            (relation["from_entity_id"], relation["to_entity_id"]),
            (E1, A1),
            "alignment 必须是 from=新版断言、to=旧版断言（§25.6）",
        )
        self.assertEqual(relation["detail"].get("collation_key"), CK1)

    # ------------------------------------------------------------------ §25.2（F4）
    def test_variant_reading_same_subject_different_text(self):
        """§25.2（F4）：同主体、NFC 文本不等 → R08 异文，detail 带 difflib opcodes。"""
        view = view_ed02()
        proposals = propose(self.base, view)

        r08 = by_rule(proposals, "R08")
        self.assertEqual(len(r08), 1, "0003 上应当恰有一条 R08，实得 %d 条" % len(r08))
        self.assertEqual(r08[0]["targets"], [E3, A3])
        self.assertEqual(r08[0]["auto_choice"], "variant_reading")

        result = apply_round(self.base, view)
        relation = relation_of(result["knowledge"], "variant_reading")
        self.assertEqual(
            (relation["from_entity_id"], relation["to_entity_id"]), (E3, A3)
        )
        self.assertEqual(relation["detail"].get("collation_key"), CK3)
        self.assertTrue(
            relation["detail"].get("opcodes"),
            "异文必须带上 difflib opcodes（只记录，不裁定）",
        )

    # ------------------------------------------------------------------ R07b
    def test_collation_subject_mismatch_goes_human(self):
        """§25.2：两侧主体裁决到**不同**正式对象 → R07b 人工提案，不自动落关系。"""
        view = view_ed02(e1_subject_pattern=PAT2)
        proposals = propose(self.base, view)

        r07b = by_rule(proposals, "R07b")
        self.assertTrue(r07b, "主体不同必须出 R07b 人工提案")
        self.assertEqual(r07b[0]["resolution"], "human")
        self.assertEqual(r07b[0]["targets"], [E1, A1])
        self.assertEqual(r07b[0]["decision_type"], "review_edition_collation")
        self.assertEqual(
            by_rule(proposals, "R07"), [], "主体不同时不得再出 R07 对齐"
        )

    # ------------------------------------------------------------------ §25.3
    def test_same_source_units_never_paired(self):
        """§25.3：同 `source_id` 的单元一律不配对（F3 的同 source 半边）。"""
        view = view_rework_absent()
        proposals = propose(self.base, view, round_no=3)
        collation = [
            item for item in proposals if item["rule_id"] in ("R07", "R07b", "R08", "R09")
        ]
        self.assertEqual(
            collation,
            [],
            "同书返工不得产生任何对勘提案（尤其不得把缺文错标成增文）: %r"
            % [(item["rule_id"], item["auto_choice"]) for item in collation],
        )

    # ------------------------------------------------------------ §25.4/25.5（F3）
    def test_addition_when_base_declared_absent(self):
        """§25.4/§25.5（F3）：基底声明 present:false → 新版有断言 → **增文**，to=null。"""
        view = view_ed02()
        proposals = propose(self.base, view)

        r09 = by_rule(proposals, "R09")
        self.assertEqual(len(r09), 2, "0002 缺文 + 0005 增文，应当恰有两条 R09: %r" % r09)
        addition = [item for item in r09 if item["auto_choice"] == "addition"]
        self.assertEqual(len(addition), 1, "必须恰有一条增文: %r" % r09)
        self.assertEqual(addition[0]["targets"], [E5, None], "增文 targets = [新版断言, null]")

        result = apply_round(self.base, view)
        relation = relation_of(result["knowledge"], "addition")
        self.assertEqual(relation["from_entity_id"], E5)
        self.assertIsNone(relation["to_entity_id"])
        self.assertEqual(relation["detail"].get("collation_key"), CK5)
        self.assertEqual(
            relation["detail"].get("absent_source_id"),
            SRC_ED01,
            "增文的 absent_source_id 是**旧版**（基底）的 source_id",
        )

    # ------------------------------------------------------------------ §25.6（F2）
    def test_omission_when_view_declares_absent(self):
        """§25.6（F2）：视图声明 present:false → **缺文**，from=旧版断言、to=null。"""
        view = view_ed02()
        proposals = propose(self.base, view)

        r09 = [item for item in by_rule(proposals, "R09") if item["auto_choice"] == "omission"]
        self.assertEqual(len(r09), 1, "必须恰有一条缺文: %r" % r09)
        self.assertEqual(r09[0]["targets"], [A2, None], "缺文 targets = [旧版断言, null]")

        result = apply_round(self.base, view)
        relation = relation_of(result["knowledge"], "omission")
        self.assertEqual(relation["from_entity_id"], A2, "缺文的 from 是**旧版**断言")
        self.assertIsNone(relation["to_entity_id"])
        self.assertEqual(relation["detail"].get("collation_key"), CK2)
        self.assertEqual(
            relation["detail"].get("absent_source_id"),
            SRC_ED02,
            "缺文的 absent_source_id 是**新版**的 source_id",
        )

    # ------------------------------------------------------------------ §25.5
    def test_undeclared_on_base_side_is_not_comparable(self):
        """§25.5/§25.9：基底**未声明**的单元不得出任何对勘关系（不许出增文）。"""
        view = view_ed02()
        proposals = propose(self.base, view)
        for item in proposals:
            if item["rule_id"] in ("R07", "R07b", "R08", "R09"):
                self.assertNotEqual(
                    item["subject"][2], CK4, "0004 在基底未声明，不得出任何对勘提案: %r" % item
                )

        result = apply_round(self.base, view)
        keys = {
            item["assertion_id"]: item.get("collation_key")
            for item in result["knowledge"]["assertions"]
        }
        for relation in collation_kinds(result["knowledge"]):
            ends = {keys.get(relation["from_entity_id"]), keys.get(relation["to_entity_id"])}
            self.assertNotIn(CK4, ends, "0004 上不得出现对勘关系: %r" % relation)

        # 该单元必须如实入册（不得静默跳过）
        out = incremental.propose_incremental(self.base, [view], round_no=2)
        rows = [
            row for row in out["not_comparable"] or []
            if row.get("collation_key") == CK4
        ]
        self.assertEqual(
            len(rows), 1, "基底未声明的单元必须如实记进 not_comparable: %r" % (out["not_comparable"],)
        )

    # ------------------------------------------------------------------ §25.5
    def test_snapshot_editions_record_collation_units(self):
        """§25.5：`editions[].collation_units` 必填、按 `collation_key` 升序，创世与合并都写。"""
        expected_ed01 = [
            {"collation_key": CK1, "present": True},
            {"collation_key": CK2, "present": True},
            {"collation_key": CK3, "present": True},
            {"collation_key": CK5, "present": False},
        ]
        self.assertEqual(self.base["editions"][0]["collation_units"], expected_ed01)

        merged = apply_round(self.base, view_ed02())["knowledge"]
        by_source = {ed["source_id"]: ed for ed in merged["editions"]}
        self.assertEqual(
            by_source[SRC_ED02]["collation_units"],
            [
                {"collation_key": CK1, "present": True},
                {"collation_key": CK2, "present": False},
                {"collation_key": CK3, "present": True},
                {"collation_key": CK4, "present": True},
                {"collation_key": CK5, "present": True},
            ],
        )
        self.assertEqual(
            by_source[SRC_ED01]["collation_units"], expected_ed01, "合并不得改动基底版次声明"
        )

        # 创世轮同样必填
        view = view_ed01()
        proposals = genesis.propose_genesis(view["candidate_set"], view["reviewed_edition"])
        asm = genesis.assemble_genesis(
            view["candidate_set"], view["reviewed_edition"],
            proposals["proposals"], id_range=copy.deepcopy(GENESIS_ID_RANGE),
        )
        self.assertEqual(asm["knowledge"]["editions"][0]["collation_units"], expected_ed01)

        # model 必填校验（缺字段 / 未升序都要拒收）
        missing = copy.deepcopy(self.base)
        del missing["editions"][0]["collation_units"]
        with self.assertRaises(SchemaViolation):
            validate_snapshot_knowledge(missing)

        unsorted = copy.deepcopy(self.base)
        unsorted["editions"][0]["collation_units"] = list(
            reversed(unsorted["editions"][0]["collation_units"])
        )
        with self.assertRaises(SchemaViolation):
            validate_snapshot_knowledge(unsorted)

    # ------------------------------------------------------------------ §25.6
    def test_null_endpoint_only_for_addition_and_omission(self):
        """§25.6：`null` 端点只许出现在 addition / omission。"""
        addition_knowledge = apply_round(self.base, view_ed02())["knowledge"]
        validate_snapshot_knowledge(addition_knowledge)  # 正向：addition/omission 的 null 合法

        tampered = copy.deepcopy(addition_knowledge)
        alignment = [
            rel_ for rel_ in tampered["relations"] if rel_["relation_kind"] == "alignment"
        ][0]
        alignment["to_entity_id"] = None
        tampered["relations"] = sorted(tampered["relations"], key=lambda item: item["relation_key"])
        with self.assertRaises(SchemaViolation) as ctx:
            validate_snapshot_knowledge(tampered)
        self.assertIn("null", str(ctx.exception))

    # ------------------------------------------------------------------ R15
    def test_collation_all_four_kinds_end_to_end_through_run_m7(self):
        """R15：临时 Ledger 上 r1 → ed99 `run_m7`，四类关系全部产出且增量 Gate 全过。

        本用例**只读夹具数据**（决定集来自 `manifest.decisions[]`），不手写提案/决定，
        也不依赖 `acceptance.py`（ACT 30 的范围），自己灌账本、自己跑 `run_m7`。
        """
        from pipeline.assembly.apply import COLLATION_KINDS
        from pipeline.assembly.fixture_seed import _seed_one_edition, seed_release_package
        from pipeline.assembly.step import run_m7
        from pipeline.ledger.service import LedgerService

        manifest = yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))
        technique_id = manifest["technique_id"]
        ed01, ed99, rework = (
            manifest["editions"][0], manifest["editions"][1], manifest["rework"]
        )
        tmp = Path(tempfile.mkdtemp(prefix="test_i_collation_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        service = LedgerService(tmp / "ledger")
        self.addCleanup(service.close)
        seeded = seed_release_package(service, FIXTURE)["editions"]

        # 返工版次（同 source_id、同 edition_part_ids）不在 editions[] 里，单独播种
        lc = rework["ledger_constants"]
        view_dir = FIXTURE / rework["views_dir"]
        service.create_processing_run(
            "release_run",
            rework["edition_part_artifact_id"],
            technique_id,
            processing_run_id=lc["processing_run_id"],
        )
        rework_seeded = _seed_one_edition(
            service,
            technique_id,
            rework["edition_part_artifact_id"],
            lc["processing_run_id"],
            lc,
            json.loads((view_dir / "candidate_set.json").read_text(encoding="utf-8")),
            dict(
                json.loads((view_dir / "reviewed_edition.json").read_text(encoding="utf-8")),
                candidate_set_revision_id=lc["candidate_set_revision_id"],
                candidate_package_revision_id=lc["candidate_package_revision_id"],
            ),
            dict(
                json.loads(
                    (view_dir / "reviewed_edition_package.json").read_text(encoding="utf-8")
                ),
                reviewed_edition_revision_id=lc["reviewed_edition_revision_id"],
            ),
        )

        def decisions_for(round_no):
            rows = [row for row in manifest["decisions"] if row["round"] == round_no]
            self.assertTrue(rows, "夹具必须登记第 %d 轮的决定集" % round_no)
            return json.loads(
                (FIXTURE / rows[0]["file"]).read_text(encoding="utf-8")
            )["decisions"]

        def snapshot_doc(revision_id):
            revision = service.get_revision(revision_id)
            return json.loads(service.objects.get(revision["sha256"]).decode("utf-8"))

        r1 = run_m7(
            service,
            ed01["edition_part_artifact_id"],
            technique_id=technique_id,
            reviewed_package_revision_ids=[
                seeded[ed01["edition_key"]]["m6_package_revision_id"]
            ],
            id_range=manifest["id_range"],
        )
        self.assertEqual(r1["status"], "succeeded", "r1 创世轮未成功: %r" % r1)

        r2 = run_m7(
            service,
            ed99["edition_part_artifact_id"],
            technique_id=technique_id,
            reviewed_package_revision_ids=[
                seeded[ed99["edition_key"]]["m6_package_revision_id"]
            ],
            base_snapshot_revision_id=r1["snapshot_revision_id"],
            id_range=manifest["id_range"],
            decisions=decisions_for(2),
        )
        self.assertEqual(r2["status"], "succeeded", "r2 增量轮未成功: %r" % r2)

        r3 = run_m7(
            service,
            rework["edition_part_artifact_id"],
            technique_id=technique_id,
            reviewed_package_revision_ids=[rework_seeded["m6_package_revision_id"]],
            base_snapshot_revision_id=r2["snapshot_revision_id"],
            id_range=manifest["id_range"],
            decisions=decisions_for(3),
        )
        self.assertEqual(r3["status"], "succeeded", "r3 同书返工轮未成功: %r" % r3)

        produced = snapshot_doc(r2["snapshot_revision_id"])
        kinds = sorted(
            {
                rel_["relation_kind"]
                for rel_ in produced["relations"]
                if rel_["relation_kind"] in COLLATION_KINDS
            }
        )
        self.assertEqual(kinds, sorted(COLLATION_KINDS), "四类对勘关系必须全部实跑产出")

        sources = {item["assertion_id"]: item.get("source_id") for item in produced["assertions"]}
        keys = {
            item["assertion_id"]: item.get("collation_key")
            for item in produced["assertions"]
        }
        new_source = ed99["source_id"]
        for rel_ in produced["relations"]:
            if rel_["relation_kind"] not in COLLATION_KINDS:
                continue
            self.assertNotEqual(
                rel_["from_entity_id"],
                rel_["to_entity_id"],
                "不得出现自环对勘关系: %r" % rel_,
            )
            kind = rel_["relation_kind"]
            if kind in ("alignment", "variant_reading"):
                self.assertIsNotNone(rel_["to_entity_id"], "%s 不得有 null 端点" % kind)
                self.assertEqual(
                    sources[rel_["from_entity_id"]], new_source, "%s 的 from 必须是新版断言" % kind
                )
                self.assertNotEqual(
                    sources[rel_["to_entity_id"]], new_source, "%s 的 to 必须是旧版断言" % kind
                )
            elif kind == "addition":
                self.assertIsNone(rel_["to_entity_id"], "增文的 to 必须是 null")
                self.assertEqual(sources[rel_["from_entity_id"]], new_source)
            elif kind == "omission":
                self.assertIsNone(rel_["to_entity_id"], "缺文的 to 必须是 null")
                self.assertNotEqual(sources[rel_["from_entity_id"]], new_source)
            self.assertTrue(
                keys.get(rel_["from_entity_id"]), "对勘关系必须落在带单元键的断言上"
            )

    # ------------------------------------------------------------------ §28 Q5
    def test_view_undeclared_unit_is_not_comparable(self):
        """§28 Q5：视图有键但**自己没在 `collation_units` 里声明** → `view_undeclared`，不出关系。"""
        view = view_ed02()
        undeclared_key = "sanche-0006"
        extra = "as_qizheng_000199"
        view["candidate_set"]["assertions"].append(
            assertion(extra, "目録", undeclared_key, SPAN_C)
        )
        approve_assertion(view, extra)

        out = incremental.propose_incremental(self.base, [view], round_no=2)
        rows = [row for row in out["not_comparable"] if row.get("collation_key") == undeclared_key]
        self.assertEqual(
            rows,
            [
                {
                    "source_id": SRC_ED02,
                    "collation_key": undeclared_key,
                    "assertion_id": None,
                    "reason": "view_undeclared",
                }
            ],
            "视图未声明的单元必须按 view_undeclared 如实入册",
        )
        self.assertEqual(
            collation_subject_proposals(out["proposals"], undeclared_key),
            [],
            "view_undeclared 单元上不得出任何对勘提案",
        )

    # ------------------------------------------------------------------ §28 假设一
    def test_multiple_assertions_on_one_unit_are_not_comparable(self):
        """§28 假设一：同侧同键 >1 条已获批断言 → `multiple_assertions_per_unit`，不出关系。"""
        view = view_ed02()
        extra = "as_qizheng_000198"
        view["candidate_set"]["assertions"].append(
            assertion(extra, "三辰通載（重出）", CK1, SPAN_A)
        )
        approve_assertion(view, extra)

        out = incremental.propose_incremental(self.base, [view], round_no=2)
        rows = [row for row in out["not_comparable"] if row.get("collation_key") == CK1]
        self.assertEqual(
            rows,
            [
                {
                    "source_id": SRC_ED02,
                    "collation_key": CK1,
                    "assertion_id": None,
                    "reason": "multiple_assertions_per_unit",
                }
            ],
        )
        self.assertEqual(
            collation_subject_proposals(out["proposals"], CK1),
            [],
            "同侧同键多条断言时不得出任何对勘提案（不许挑一条）",
        )

    # ------------------------------------------------------------------ §28b / §29 Q11
    def test_not_comparable_list_shape_and_scope(self):
        """§28b / §29 Q11：形状恰为四键、按固定键排序、**只列视图一侧**的单元。"""
        view = view_ed02()
        out = incremental.propose_incremental(self.base, [view], round_no=2)
        rows = out["not_comparable"]
        self.assertEqual(
            rows,
            [
                {
                    "source_id": SRC_ED02,
                    "collation_key": CK4,
                    "assertion_id": None,
                    "reason": "base_undeclared",
                }
            ],
            "基底未声明的 0004 是唯一不可比单元",
        )
        for row in rows:
            self.assertEqual(
                set(row),
                {"source_id", "collation_key", "assertion_id", "reason"},
                "每项形状恰为 {source_id, collation_key, assertion_id, reason}: %r" % row,
            )
        self.assertEqual(
            rows,
            sorted(rows, key=lambda row: (row["source_id"], row["collation_key"] or "",
                                          row["assertion_id"] or "")),
            "清单必须按 (source_id, collation_key or \"\", assertion_id or \"\") 升序",
        )

        # 只列视图一侧：把视图对 CK5 的声明与断言都拿掉后，CK5 成为「基底声明过、视图既没声明
        # 也没断言」的键 → 不列（§28 Q5；基底一侧的键不许污染清单）。
        cset = view["candidate_set"]
        cset["assertions"] = [a for a in cset["assertions"] if a["assertion_id"] != E5]
        cset["collation_units"] = [
            u for u in cset["collation_units"] if u.get("collation_key") != CK5
        ]
        view["reviewed_edition"]["approved"] = [
            item for item in view["reviewed_edition"]["approved"] if item["entity_id"] != E5
        ]
        out2 = incremental.propose_incremental(self.base, [view], round_no=2)
        self.assertEqual(
            [row for row in out2["not_comparable"] if row.get("collation_key") == CK5],
            [],
            "基底声明过、视图既没声明也没断言的键不得进入清单",
        )

    # ------------------------------------------------------------------ §28 Q2
    def test_r07b_accept_alignment_lands_a_relation(self):
        """§28 Q2：`accept_alignment` → 按文本相等落 alignment（`mode=human`，detail 带键）。"""
        view = dedupe_approved(view_ed02(e1_subject_pattern=PAT2))
        proposals = propose(self.base, view)
        r07b = by_rule(proposals, "R07b")
        self.assertEqual(len(r07b), 1, "前置：0001 上必须有一条 R07b")

        result = apply_round(
            self.base, view, decisions=[decision_for(r07b[0], "accept_alignment")]
        )
        relation = relation_of(result["knowledge"], "alignment")
        self.assertEqual(
            (relation["from_entity_id"], relation["to_entity_id"]), (E1, A1)
        )
        self.assertEqual(
            relation["resolution"]["mode"], "human", "R07b 的落点必须是 human 裁定"
        )
        self.assertEqual(relation["detail"].get("collation_key"), CK1)

        # 文本不等 → 同一裁定落成 variant_reading（不是 alignment）
        view2 = dedupe_approved(view_ed02(e1_subject_pattern=PAT2))
        for item in view2["candidate_set"]["assertions"]:
            if item["assertion_id"] == E1:
                item["proposition"] = "三辰通載異文"
        proposals2 = propose(self.base, view2)
        r07b2 = by_rule(proposals2, "R07b")
        result2 = apply_round(
            self.base, view2, decisions=[decision_for(r07b2[0], "accept_alignment")]
        )
        landed = [
            rel_
            for rel_ in result2["knowledge"]["relations"]
            if rel_["relation_kind"] == "variant_reading" and rel_["from_entity_id"] == E1
        ]
        self.assertEqual(len(landed), 1, "文本不等必须落 variant_reading: %r" % landed)
        self.assertEqual(landed[0]["resolution"]["mode"], "human")
        self.assertTrue(landed[0]["detail"].get("opcodes"), "异文要带 difflib opcodes")

    # ------------------------------------------------------------------ §28 Q2 / §29 Q10
    def test_r07b_reject_alignment_lands_distinct_from(self):
        """§28 Q2 / §29 Q10：`reject_alignment` → 一条 `distinct_from`，`mode=human` + detail 带键。"""
        view = dedupe_approved(view_ed02(e1_subject_pattern=PAT2))
        proposals = propose(self.base, view)
        r07b = by_rule(proposals, "R07b")

        result = apply_round(
            self.base, view, decisions=[decision_for(r07b[0], "reject_alignment")]
        )
        distinct = [
            rel_
            for rel_ in result["knowledge"]["relations"]
            if rel_["relation_kind"] == "distinct_from"
            and rel_["detail"].get("collation_key")
        ]
        self.assertEqual(len(distinct), 1, "R07b 拒绝必须落一条对勘 distinct_from: %r" % distinct)
        relation = distinct[0]
        self.assertEqual((relation["from_entity_id"], relation["to_entity_id"]), (E1, A1))
        self.assertEqual(relation["resolution"]["mode"], "human")
        self.assertEqual(relation["detail"].get("collation_key"), CK1)

    # ------------------------------------------------------------------ §28 Q3
    def test_null_subject_goes_human(self):
        """§28 Q3：主体推不出（null）→ 不算同一正式对象 → R07b 人工。"""
        view = view_ed02()
        for pattern_ in view["candidate_set"]["patterns"]:
            pattern_["assertion_ids"] = [
                aid for aid in pattern_["assertion_ids"] if aid != E1
            ]
        proposals = propose(self.base, view)
        r07b = by_rule(proposals, "R07b")
        self.assertEqual(
            [item["targets"] for item in r07b],
            [[E1, A1]],
            "主体为 null 的 0001 必须走 R07b，不许停手上报也不许自动对齐",
        )
        self.assertEqual(by_rule(proposals, "R07"), [], "主体为 null 时不得出 R07")

    # ------------------------------------------------------------------ §29 Q9
    def test_base_without_collation_units_refused(self):
        """§29 Q9：基底缺 `collation_units` → 入口拒收（不许静默当空）。"""
        base = copy.deepcopy(self.base)
        del base["editions"][0]["collation_units"]
        view = view_ed02()
        with self.assertRaises(SchemaViolation) as ctx:
            m7_apply.apply_resolutions(base, [view], propose(self.base, view), [])
        self.assertIn("基底 Snapshot 缺 collation_units，须先迁移", str(ctx.exception))

    # ------------------------------------------------------------------ §29 Q8
    def test_rework_recomputes_relations_touching_view_source(self):
        """§29 Q8：同书返工时涉及视图 source 的对勘关系全部删除重算并记账，方向按本轮角色。"""
        r2 = apply_round(self.base, view_ed02())["knowledge"]
        before = [
            rel_
            for rel_ in r2["relations"]
            if rel_["relation_kind"] in ("alignment", "variant_reading", "addition", "omission")
        ]
        self.assertEqual(len(before), 4, "前置：r2 恰有四类对勘关系")

        view = view_rework_absent()
        # 直接调纯函数层时须自己模拟 D-14 的替换继承：仍声明 present 的 A1/A3 的 R11 提案
        # 由 `orchestrate.carry_forward_proposals` 剔除（否则会把保号携带的断言一并退役）。
        proposals = [
            item
            for item in propose(r2, view, round_no=3)
            if not (item["rule_id"] == "R11" and item["subject"][-1] in (A1, A3))
        ]
        result = m7_apply.apply_resolutions(r2, [view], proposals, [])
        knowledge = result["knowledge"]
        dropped = {row["relation_key"]: row["reason"] for row in result["report"]["dropped_relations"]}
        self.assertEqual(
            len(dropped), len(result["report"]["dropped_relations"]),
            "dropped_relations 不得含重复 relation_key: %r" % (result["report"]["dropped_relations"],),
        )
        self.assertTrue(
            [key for key, reason in dropped.items() if reason == "collation_recomputed"],
            "删掉重算的对勘关系必须记 collation_recomputed: %r" % (dropped,),
        )

        alignment = [
            rel_ for rel_ in knowledge["relations"] if rel_["relation_kind"] == "alignment"
        ]
        self.assertEqual(len(alignment), 1, "重算后 0001 上恰一条对齐")
        self.assertEqual(
            (alignment[0]["from_entity_id"], alignment[0]["to_entity_id"]),
            (A1, E1),
            "返工轮视图 = 新版：方向必须反向为 ed01 → ed99",
        )
        variant = [
            rel_ for rel_ in knowledge["relations"] if rel_["relation_kind"] == "variant_reading"
        ]
        self.assertEqual(
            [(rel_["from_entity_id"], rel_["to_entity_id"]) for rel_ in variant],
            [(A3, E3)],
        )


class FixtureDeclarationTest(unittest.TestCase):
    """§25.9：fixture 自己的声明必须与裁定逐条对上（由 build_fixture.py 实跑产出）。"""

    def test_ed01_declares_0005_absent_and_ed99_has_own_assertion_ids(self):
        manifest = yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))
        ed01, ed99 = manifest["editions"][0], manifest["editions"][1]
        ed01_cset = json.loads((FIXTURE / ed01["views_dir"] / "candidate_set.json").read_text(encoding="utf-8"))
        ed99_cset = json.loads((FIXTURE / ed99["views_dir"] / "candidate_set.json").read_text(encoding="utf-8"))

        ed01_units = {u["collation_key"]: u["present"] for u in ed01_cset["collation_units"] if u.get("collation_key")}
        self.assertEqual(ed01_units.get("sanche-0005"), False, "ed01 必须声明 0005 present:false")

        r1 = json.loads((FIXTURE / manifest["expected"]["round1"]).read_text(encoding="utf-8"))
        base_ids = {item["assertion_id"] for item in r1["assertions"]}
        reused = [a["assertion_id"] for a in ed99_cset["assertions"] if a["assertion_id"] in base_ids]
        self.assertEqual(reused, [], "ed99 必须给自己的断言发自己的号，不得沿用 ed01 的号")

        ed99_units = {u["collation_key"]: u["present"] for u in ed99_cset["collation_units"] if u.get("collation_key")}
        self.assertEqual(ed99_units.get("sanche-0002"), False, "ed99 必须声明 0002 present:false（缺文）")
        self.assertEqual(ed99_units.get("sanche-0005"), True, "ed99 的 0005 有断言且 present（增文）")


if __name__ == "__main__":
    unittest.main()

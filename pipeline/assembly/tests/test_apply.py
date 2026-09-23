"""M7 增量汇编 C 波：应用裁定 apply_resolutions 验收测试（act/impl-07/23）。

规格来源：`act/04.yaml:20-40`（逐字沿用：发号、merge_entities、split、retire、reject_alias、
accept_alias、attach、unify、对勘四类、content_status、返回键、IdentityDelta entry 键序）
＋ ACT 23 第一节 §11（difflib 只许在 apply.py 记录差异，不许参与配对判断）。

本文件的视图与裁定全部**在测试内构造**（不读 `var/`；真书证据见回报与探针脚本）。
唯一读 fixture 的用例是跨波等价性用例（apply 的创世轮必须逐字节等于已验收创世引擎的输出）。
"""

import copy
import json
import unittest
from pathlib import Path

import yaml

from pipeline.assembly import apply as m7_apply
from pipeline.assembly import incremental as m7_incremental
from pipeline.assembly import model as m7_model
from pipeline.assembly.canonical import canonical_json, make_key
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.genesis import propose_genesis
from pipeline.assembly.model import empty_snapshot_knowledge
from pipeline.ledger.errors import (
    DuplicateIdentifier,
    InvalidIdentifier,
    MissingReference,
    SchemaViolation,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"

TECH = "qizheng"
WORK = "sanche"


def const(prefix: str, suffix: str) -> str:
    """定长常量标识（32 位十六进制体，零填充）。"""
    body = ("0" * (32 - len(suffix)) + suffix).lower()
    assert len(body) == 32 and all(ch in "0123456789abcdef" for ch in body), suffix
    return prefix + body


# ---------------------------------------------------------------- 版次与对象常量
ART_ED1 = const("art_", "e1")
ART_ED2 = const("art_", "e2")
ART_ED3 = const("art_", "e3")
CS1, CP1, VAL1 = const("rev_", "11"), const("rev_", "12"), const("rev_", "13")
CS2, CP2, VAL2 = const("rev_", "21"), const("rev_", "22"), const("rev_", "23")
CS3, CP3, VAL3 = const("rev_", "31"), const("rev_", "32"), const("rev_", "33")

SPAN_A = "ss_sanche_ed01_p0001_s01"  # 三辰通載
SPAN_B = "ss_sanche_ed01_p0001_s02"  # （宋）錢如璧撰
SPAN_C = "ss_sanche_ed01_p0003_s03"  # 三辰通載目錄

A1 = "as_qizheng_000001"
A2 = "as_qizheng_000002"
A_B = "as_qizheng_000003"
A_C = "as_qizheng_000004"
PAT1 = "pat_qizheng_000001"
CO1 = "co_qizheng_000001"
SV1 = const("sv_", "1")
SV2 = const("sv_", "2")
CG1 = const("cg_", "1")
SCH1 = "sch_qizheng_001"
SCH2 = "sch_qizheng_002"

CK_TRANSCRIPT = "sanche-0001"
CK_AUTHOR = "sanche-0002"
REV_BASE = const("rev_", "b1")

PROPOSAL_FIELDS = (
    "proposal_key", "kind", "rule_id", "resolution", "subject", "targets",
    "options", "auto_choice", "decision_type", "basis_sha256", "depends_on",
)


# ---------------------------------------------------------------- 文档构造函数
def ev(span_id: str) -> dict:
    """一条证据（偏移与 reviewed_edition 的 evidence_links 逐字段一致）。"""
    return {
        "source_span_id": span_id,
        "start_offset": 0,
        "end_offset": 4,
        "quote_sha256": "a" * 64,
    }


def assertion(aid: str, proposition: str, collation_key, span_id: str, *, school_ids=(), spans=None) -> dict:
    return {
        "assertion_id": aid,
        "proposition_id": "pr_qizheng_%s" % aid.split("_")[-1],
        "proposition": proposition,
        "relation": "supports",
        "evidence": [ev(span) for span in (spans or [span_id])],
        "conditions": [],
        "exceptions": [],
        "concept_refs": [],
        "school_ids": list(school_ids),
        "layer": "general",
        "content_status": "machine_extracted",
        "collation_key": collation_key,
        "origin": {"lane": "main", "item_index": 0},
    }


def pattern(name: str, assertion_ids, *, pattern_id=None, candidate_key=None) -> dict:
    item = {
        "pattern_id": pattern_id,
        "name": name,
        "assertion_ids": list(assertion_ids),
        "evidence": [],
        "interpretation": "测试宿主",
        "interpretation_status": "captured",
        "recognition_rule_status": "not_captured",
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 0},
    }
    if candidate_key is not None:
        item["candidate_key"] = candidate_key
    return item


def concept_mention(surface: str, ref: str) -> dict:
    return {
        "surface": surface,
        "concept_ref": ref,
        "evidence": [ev(SPAN_A)],
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 0},
    }


def new_concept_candidate(surface: str) -> dict:
    return {
        "surface": surface,
        "technique_id": TECH,
        "evidence": [ev(SPAN_C)],
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 0},
    }


def school_view(svid: str, school_id: str, subject: str, *, source_id: str, cg_id=CG1) -> dict:
    return {
        "school_view_id": svid,
        "school_id": school_id,
        "subject_entity_id": subject,
        "claim_refs": [subject],
        "conflict_group_id": cg_id,
        "changes_current_judgment": True,
        "source_refs": [{"source_id": source_id, "source_span_id": SPAN_A}],
        "evidence": [],
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 0},
    }


def candidate_set(
    source_id: str,
    edition_part: str,
    *,
    assertions=(),
    patterns=(),
    school_views=(),
    concept_mentions=(),
    new_concept_candidates=(),
    collation_units=None,
) -> dict:
    doc = {
        "schema_version": "0.1.0-draft",
        "synthetic": True,
        "technique_id": TECH,
        "source_id": source_id,
        "edition_part_artifact_id": edition_part,
        "evidence_level": "glyphbox_level",
        "span_layer": "structural",
        "source_channels": {"assertion": {"main": "text"}},
        "assertions": list(assertions),
        "patterns": list(patterns),
        "school_views": list(school_views),
        "concept_mentions": list(concept_mentions),
        "new_concept_candidates": list(new_concept_candidates),
        "rejected": [],
        "disputes": [],
    }
    if collation_units is not None:
        doc["collation_units"] = list(collation_units)
    doc["counts"] = {
        key: len(doc[key])
        for key in (
            "assertions", "patterns", "school_views", "concept_mentions",
            "new_concept_candidates", "rejected", "disputes",
        )
    }
    return doc


def reviewed_edition(
    edition_part: str,
    *,
    candidate_set_revision_id: str,
    candidate_package_revision_id: str,
    validation_package_revision_id: str,
    approved=(),
    links=(),
    school_views=(),
    source_id: str,
) -> dict:
    approved_items = []
    decisions = []
    for index, (entity_id, kind) in enumerate(approved):
        rev = const("rev_", "%03d" % (index + 1))
        approved_items.append(
            {
                "entity_id": entity_id,
                "kind": kind,
                "artifact_revision_id": candidate_set_revision_id,
                "content_status": "machine_extracted",
                "decision_revision_ids": [rev],
            }
        )
        decisions.append(
            {
                "decision_revision_id": rev,
                "queue_item_id": "%s#review_source_fidelity" % entity_id,
                "target_entity_id": entity_id,
                "seen_artifact_revision_id": candidate_set_revision_id,
                "current_target_revision_id": candidate_set_revision_id,
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
        "edition_part_artifact_id": edition_part,
        "candidate_set_revision_id": candidate_set_revision_id,
        "candidate_package_revision_id": candidate_package_revision_id,
        "validation_package_revision_id": validation_package_revision_id,
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
        "school_views": list(school_views),
        "correction_request_revision_ids": [],
        "rework_impact_report_revision_id": None,
        "unresolved_count": 0,
        "source_id": source_id,
    }


def view_ed01() -> dict:
    """版次一（基准轮）：一条带形式号的断言 + 一条无号断言 + 格局 + 概念 + 学校观。"""
    source_id = "src_sanche_ed01"
    cset = candidate_set(
        source_id,
        ART_ED1,
        assertions=[
            assertion(A1, "三辰通載", CK_TRANSCRIPT, SPAN_A, school_ids=[SCH1]),
            assertion(A2, "（宋）錢如璧撰", CK_AUTHOR, SPAN_B, spans=[SPAN_B, SPAN_C]),
        ],
        patterns=[pattern("三辰通載貴格", [A1], pattern_id=PAT1)],
        school_views=[school_view(SV1, SCH1, A1, source_id=source_id)],
        concept_mentions=[concept_mention("三辰", CO1)],
        new_concept_candidates=[new_concept_candidate("通載")],
        collation_units=[
            {"collation_key": CK_TRANSCRIPT, "present": True},
            {"collation_key": CK_AUTHOR, "present": True},
        ],
    )
    reviewed = reviewed_edition(
        ART_ED1,
        candidate_set_revision_id=CS1,
        candidate_package_revision_id=CP1,
        validation_package_revision_id=VAL1,
        approved=[
            (A1, "assertion"), (A2, "assertion"), (PAT1, "pattern"),
            (CO1, "concept"), (SV1, "school_view"),
        ],
        links=[(A1, SPAN_A), (A2, SPAN_B), (A2, SPAN_C)],
        school_views=[
            {"school_view_id": SV1, "school_id": SCH1, "subject_entity_id": A1,
             "conflict_group_id": CG1, "changes_current_judgment": True}
        ],
        source_id=source_id,
    )
    return {"source_id": source_id, "candidate_set": cset, "reviewed_edition": reviewed}


def view_ed02() -> dict:
    """版次二（增量轮）：同名断言（同号同命题、不同证据）、异读断言、格局与概念并入。"""
    source_id = "src_sanche_ed02"
    cset = candidate_set(
        source_id,
        ART_ED2,
        assertions=[
            assertion(A1, "三辰通載", CK_TRANSCRIPT, SPAN_C, school_ids=[SCH1]),
            assertion(A_B, "三辰通載目錄", CK_TRANSCRIPT, SPAN_C, school_ids=[SCH2]),
        ],
        patterns=[pattern("三辰通載貴格", [A1, A_B], pattern_id=PAT1)],
        school_views=[school_view(SV2, SCH2, A_B, source_id=source_id)],
        concept_mentions=[concept_mention("通載", CO1)],
        collation_units=[{"collation_key": CK_TRANSCRIPT, "present": True}],
    )
    reviewed = reviewed_edition(
        ART_ED2,
        candidate_set_revision_id=CS2,
        candidate_package_revision_id=CP2,
        validation_package_revision_id=VAL2,
        approved=[
            (A1, "assertion"), (A_B, "assertion"), (PAT1, "pattern"),
            (CO1, "concept"), (SV2, "school_view"),
        ],
        links=[(A1, SPAN_C), (A_B, SPAN_C)],
        school_views=[
            {"school_view_id": SV2, "school_id": SCH2, "subject_entity_id": A_B,
             "conflict_group_id": CG1, "changes_current_judgment": True}
        ],
        source_id=source_id,
    )
    return {"source_id": source_id, "candidate_set": cset, "reviewed_edition": reviewed}


def doc_view(source_id, cset, reviewed, approved_index) -> dict:
    """已校验结果形状的视图（act/04 的「无号候选获批」路径需要它）。

    背景：冻结的 `validate_reviewed_edition` 要求 `approved[].entity_id` 必须是**正式**
    `pat_`/`as_`/`co_` 号，因此「无号候选（candidate_key）获批」无法经原始文档表达。
    act/04:29 却明写这条发号路径存在，故本用例按模块已支持的 `{"doc": …}` 形状构造
    （与 `propose_genesis` / `assemble_genesis` 的入参形状一致），并在回报 §3.5 记录
    这一 M6 侧 schema 缺口。
    """
    return {
        "source_id": source_id,
        "candidate_set": {"doc": cset, "source_id": source_id},
        "reviewed_edition": {"doc": reviewed, "approved_index": approved_index},
    }


def view_ed03(*, rogue_id="pat_qizheng_000009", approved_id="pat_qizheng_000003") -> dict:
    """版次三：一条**已获批**的新正式号 + 一条**未获批**却自带 pat_ 号的候选。

    两者共同验证 §8.1：号位只能按已获批对象取，未获批的自发号既不得抬高号位，
    也不得静默丢弃。
    """
    source_id = "src_sanche_ed03"
    cset = candidate_set(
        source_id,
        ART_ED3,
        assertions=[assertion(A_C, "三辰通載三十卷", CK_TRANSCRIPT, SPAN_A)],
        patterns=[
            pattern("已获批新格局", [A_C], pattern_id=approved_id),
            pattern("未获批野号格局", [A_C], pattern_id=rogue_id),
        ],
        collation_units=[{"collation_key": CK_TRANSCRIPT, "present": True}],
    )
    reviewed = reviewed_edition(
        ART_ED3,
        candidate_set_revision_id=CS3,
        candidate_package_revision_id=CP3,
        validation_package_revision_id=VAL3,
        approved=[(A_C, "assertion"), (approved_id, "pattern")],
        links=[(A_C, SPAN_A)],
        source_id=source_id,
    )
    return {"source_id": source_id, "candidate_set": cset, "reviewed_edition": reviewed}


def proposal(
    kind: str,
    rule_id: str,
    subject,
    *,
    resolution: str = "auto",
    options=(),
    auto_choice=None,
    targets=(),
    decision_type=None,
    depends_on=(),
) -> dict:
    return {
        "proposal_key": m7_incremental.proposal_key(kind, subject),
        "kind": kind,
        "rule_id": rule_id,
        "resolution": resolution,
        "subject": list(subject),
        "targets": list(targets),
        "options": list(options),
        "auto_choice": auto_choice,
        "decision_type": decision_type,
        "basis_sha256": None,
        "depends_on": list(depends_on),
    }


def decision(prop: dict, choice: str, *, targets=(), span_allocation=None) -> dict:
    item = {
        "proposal_set_revision_id": None,
        "proposal_key": prop["proposal_key"],
        "choice": choice,
        "target_entity_ids": list(targets),
        "seen_revision_id": None,
        "decision_type": prop["decision_type"],
    }
    if span_allocation is not None:
        item["span_allocation"] = copy.deepcopy(span_allocation)
    return item


def base_skeleton(*, meta=None) -> dict:
    base = empty_snapshot_knowledge(TECH, {"pat_%s" % TECH: [1, 999999]})
    if meta is not None:
        base["meta"] = copy.deepcopy(meta)
    return base


def round1(*, meta=None) -> dict:
    """基准轮：空基底 + ed01 视图 → r1 **knowledge**（本文件多数用例的基底）。"""
    return round1_result(meta=meta)["knowledge"]


def round1_result(*, meta=None) -> dict:
    """基准轮的完整返回值（返回键护栏用）。"""
    return m7_apply.apply_resolutions(base_skeleton(meta=meta), [view_ed01()], [], [])


def round2_proposals() -> list:
    """自造的增量轮提案集（覆盖 attach / alias / 对勘三类）。

    `R08` 的 `targets` 显式给出配对两侧（基底侧 A1 ↔ 候选侧 A_B）：**配对由提案确立**，
    apply 不得自己比对。B 波在同号情形下产出 R07b（人工），本用例用构造提案驱动
    `variant_reading`，目的是验证 §11.3（difflib 只记录、不裁定），见回报 §3.4。
    """
    return [
        proposal(
            "merge", "R01", ["pattern", "src_sanche_ed02", PAT1],
            auto_choice="attach:%s" % PAT1, targets=[PAT1],
        ),
        proposal(
            "alias", "R04", ["concept", "src_sanche_ed02", CO1],
            resolution="human", options=["accept_alias", "reject_alias"], targets=[CO1],
        ),
        proposal(
            "evidence", "R08", ["collation", "src_sanche_ed02", CK_TRANSCRIPT, "src_sanche_ed01"],
            auto_choice="variant_reading", targets=[A1, A_B],
        ),
    ]


def round2_decisions(props=None) -> list:
    """round2 提案集对应的人工决定（accept_alias）。"""
    props = props or round2_proposals()
    alias_prop = [item for item in props if item["kind"] == "alias"][0]
    return [decision(alias_prop, "accept_alias", targets=[CO1])]


def retire_proposal(assertion_id: str) -> dict:
    """R11 auto：一条失去全部 provenance 的断言 → retire。"""
    return proposal("conflict", "R11", ["provenance_lost", assertion_id], auto_choice="retire")


def find_relation(knowledge: dict, relation_kind: str) -> dict:
    matches = [rel for rel in knowledge["relations"] if rel["relation_kind"] == relation_kind]
    assert len(matches) == 1, "期望恰好一条 %s 关系，实得 %d 条" % (relation_kind, len(matches))
    return matches[0]


def strip_opcodes(node):
    """抹平全部 `opcodes` 值，用于比对「除 opcodes 外逐字节相同」。"""
    if isinstance(node, dict):
        return {
            key: ("STRIPPED" if key == "opcodes" else strip_opcodes(value))
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [strip_opcodes(item) for item in node]
    return node


class TestApplyResolutions(unittest.TestCase):
    # -------------------------------------------------------- §11.3 本波最重要
    def test_difflib_only_records_never_decides_pairing(self):
        """§11.1/§11.3：difflib 只许**记录**已确立配对的差异，不许参与任何配对/裁定判断。

        判据：把 `SequenceMatcher` 打桩成返回空 opcodes 后，
        **除 `variant_reading.detail.opcodes` 之外，产物逐字节不变**。
        """
        base = round1()

        real = m7_apply.apply_resolutions(
            base, [view_ed02()], round2_proposals(), round2_decisions()
        )
        opcodes = find_relation(real["knowledge"], "variant_reading")["detail"]["opcodes"]
        self.assertTrue(opcodes, "构造样本的两次异读文本必须产生非空 opcodes，否则判据是空的")

        original = m7_apply.difflib.SequenceMatcher

        class _Stub(original):  # 保留构造签名，只把 get_opcodes 变成恒空
            def get_opcodes(self):
                return []

        m7_apply.difflib.SequenceMatcher = _Stub
        try:
            stubbed = m7_apply.apply_resolutions(
                base, [view_ed02()], round2_proposals(), round2_decisions()
            )
        finally:
            m7_apply.difflib.SequenceMatcher = original

        self.assertEqual(
            find_relation(stubbed["knowledge"], "variant_reading")["detail"]["opcodes"],
            [],
            "打桩后 opcodes 必须为空（证明打桩生效，判据非空转）",
        )
        self.assertEqual(
            canonical_json(strip_opcodes(real["knowledge"])),
            canonical_json(strip_opcodes(stubbed["knowledge"])),
            "除 variant_reading.detail.opcodes 外，产物必须逐字节不变（difflib 不得参与裁定）",
        )
        self.assertEqual(
            canonical_json(real["identity_delta"]), canonical_json(stubbed["identity_delta"])
        )
        self.assertEqual(
            canonical_json(strip_opcodes(real["collation"])),
            canonical_json(strip_opcodes(stubbed["collation"])),
        )
        self.assertEqual(real["created_entity_ids"], stubbed["created_entity_ids"])
        self.assertEqual(real["resolution_log"], stubbed["resolution_log"])

    # -------------------------------------------------------- affected 原样拷贝
    def test_untouched_base_objects_are_copied_verbatim(self):
        """`affected` 集合外的基底对象必须从基座**原样拷贝**，不得重新构造。"""
        base = round1()
        base["patterns"][0]["aliases"] = ["keep-me-marker"]  # 重建必定丢掉的痕迹
        base_bytes = canonical_json(base["patterns"][0])

        result = m7_apply.apply_resolutions(
            base, [view_ed02()], round2_proposals(), round2_decisions(), affected={A1}
        )

        patterns = {item["pattern_id"]: item for item in result["knowledge"]["patterns"]}
        self.assertIn(PAT1, patterns)
        self.assertEqual(
            canonical_json(patterns[PAT1]),
            base_bytes,
            "集合外基底对象必须逐字节原样拷贝（含重建不会产生的字段）",
        )
        self.assertNotIn(
            PAT1, result["rebuilt_entity_ids"], "集合外对象不得计为「已重建」"
        )
        self.assertIn(A1, result["rebuilt_entity_ids"], "集合内对象须计为「已重建」")

    # -------------------------------------------------------- §8.1 发号
    def test_admit_new_allocates_from_approved_max_only(self):
        """§8.1：M7 发新号时，号位只从「已获批、进入 Snapshot 的对象」取最大号 + 1。

        判别力：未获批却自带 `pat_qizheng_000009` 的候选**不得**抬高号位——
        若它被计入，新号会变成 000010 而不是 000002。
        """
        base = round1()
        source_id = "src_sanche_ed03"
        cset = candidate_set(
            source_id,
            ART_ED3,
            assertions=[assertion(A_C, "三辰通載三十卷", CK_TRANSCRIPT, SPAN_A)],
            patterns=[
                pattern("新格局", [A_C], candidate_key="ck-new-pattern"),
                pattern("未获批野号格局", [A_C], pattern_id="pat_qizheng_000009"),
            ],
            collation_units=[{"collation_key": CK_TRANSCRIPT, "present": True}],
        )
        self.assertEqual(cset["counts"]["patterns"], 2)
        reviewed = reviewed_edition(
            ART_ED3,
            candidate_set_revision_id=CS3,
            candidate_package_revision_id=CP3,
            validation_package_revision_id=VAL3,
            approved=[(A_C, "assertion")],
            links=[(A_C, SPAN_A)],
            source_id=source_id,
        )
        approved_index = {
            A_C: {"kind": "assertion", "content_status": "machine_extracted"},
            "ck-new-pattern": {"kind": "pattern", "content_status": "machine_extracted"},
        }
        view = doc_view(source_id, cset, reviewed, approved_index)
        props = [
            proposal(
                "merge", "R03e", ["pattern", source_id, "ck-new-pattern"],
                auto_choice="admit_new",
            )
        ]
        result = m7_apply.apply_resolutions(base, [view], props, [])

        self.assertEqual(
            [item["pattern_id"] for item in result["knowledge"]["patterns"]],
            [PAT1, "pat_qizheng_000002"],
            "新号必须取已获批最大号 1 + 1 = 2；不得被未获批自发号 9 抬成 10",
        )
        self.assertEqual(result["knowledge"]["id_allocation"]["pat_%s" % TECH], 2)
        self.assertEqual(
            result["report"]["id_allocation"]["pat_%s" % TECH], 2, "报告里的号位须与 knowledge 一致"
        )
        self.assertEqual(
            [item["pattern_id"] for item in result["report"]["unapproved_with_self_issued_id"]],
            ["pat_qizheng_000009"],
            "同一轮里未获批的自发号既不得抬高号位，也不得静默丢弃",
        )

    def test_unapproved_self_issued_id_reported_not_counted(self):
        """§8.1：携带自发 `pat_` 号但未获批的候选必须**如实报告**，不得静默丢弃。"""
        base = round1()
        view = view_ed03()
        result = m7_apply.apply_resolutions(base, [view], [], [])

        reported = result["report"]["unapproved_with_self_issued_id"]
        self.assertEqual(
            reported,
            [
                {
                    "source_id": view["source_id"],
                    "pattern_id": "pat_qizheng_000009",
                    "reason": "unapproved_with_self_issued_id",
                }
            ],
            "未获批且携带自发号的候选须逐条进 assembly_report（键名逐字）",
        )
        self.assertNotIn(
            "pat_qizheng_000009",
            [item["pattern_id"] for item in result["knowledge"]["patterns"]],
            "未获批候选不得进入 Snapshot",
        )

    # -------------------------------------------------------- merge_entities
    def test_merge_entities_blocked_by_frozen_relations_endpoint_rule(self):
        """merge_entities 撞上冻结校验器：先把冲突本身钉死，再钉 apply 的 fail-closed。

        冲突事实（act/04.yaml:31 vs `model.validate_snapshot_knowledge`）：
        `merge_entities` 要求旧号进 `retired_entity_ids` 并写 `merged_into(旧, 新)`，
        而冻结的校验器要求 `relations` 端点必须是**活对象**，两者不可同时成立。
        本用例不被静默跳过：它逐字钉住两侧，并断言 apply 拒绝时零产出。
        （ACT 的具名用例 `test_merge_entities_retires_old_and_rewrites_subjects`
        在当前冻结校验器下无法绿——已改名，见回报 §3.1。）
        """
        # (1) spec 形状（旧号 retired + merged_into(旧, 新)）过不了冻结校验器
        retired = "pat_qizheng_000001"
        survivor = "pat_qizheng_000003"
        spec_shaped = {
            "technique_id": TECH,
            "id_allocation": {"pat_%s" % TECH: 3},
            "id_range": {"pat_%s" % TECH: [1, 999999]},
            "allocated_pattern_ids": [],
            "retired_entity_ids": [retired],
            "editions": [],
            "concepts": [],
            "patterns": [
                {
                    "pattern_id": survivor, "concept_id": None, "name": "合并后格局",
                    "aliases": [], "rules": [], "assertion_ids": [], "school_view_ids": [],
                    "recognition_rule_status": "not_captured", "provenance": [],
                }
            ],
            "assertions": [],
            "school_views": [],
            "conflict_groups": [],
            "relations": [
                {
                    "relation_key": make_key("merged_into", [retired, survivor]),
                    "from_entity_id": retired,
                    "to_entity_id": survivor,
                    "relation_kind": "merged_into",
                    "detail": {},
                    "resolution": {"mode": "human", "proposal_key": "merge:" + "0" * 32},
                }
            ],
        }
        with self.assertRaises(MissingReference) as ctx:
            m7_model.validate_snapshot_knowledge(spec_shaped)
        self.assertEqual(getattr(ctx.exception, "code", None), "REF_001")
        self.assertIn(retired, str(ctx.exception))
        base = round1()
        base["patterns"].append(
            {
                "pattern_id": "pat_qizheng_000002",
                "concept_id": None,
                "name": "三辰通載貴格（异名）",
                "aliases": [],
                "rules": [],
                "assertion_ids": [A2],
                "school_view_ids": [],
                "recognition_rule_status": "not_captured",
                "provenance": [
                    {"source_id": "src_sanche_ed01", "content_sha256": "b" * 64,
                     "content_status": "machine_extracted"}
                ],
            }
        )
        base["patterns"].sort(key=lambda p: p["pattern_id"])
        base["id_allocation"]["pat_%s" % TECH] = 2

        merge_prop = proposal(
            "merge", "R03d", ["pattern", "src_sanche_ed02", "pat_qizheng_000002"],
            resolution="human", options=["merge_entities"], targets=[PAT1, "pat_qizheng_000002"],
        )
        props = round2_proposals() + [merge_prop]
        decisions = round2_decisions(props) + [
            decision(merge_prop, "merge_entities", targets=[PAT1, "pat_qizheng_000002"])
        ]

        with self.assertRaises(AssemblyRefused) as ctx:
            m7_apply.apply_resolutions(base, [view_ed02()], props, decisions)
        message = str(ctx.exception)
        self.assertIn("merge_entities", message)
        self.assertIn("relations", message)

    # -------------------------------------------------------- split
    def test_split_allocates_and_retires_with_span_allocation(self):
        """split：每个占位名按升序发新号、旧号退役、IdentityDelta 一条 split 携带
        占位名替换为新号的 span_allocation。

        目标选 A2（无任何对象引用它）：act/04 未规定 split 后引用如何改指，
        本波对「被引用的号」直接 fail-closed 并上报（回报 §3.2）。
        """
        base = round1()
        old = [item for item in base["assertions"] if item["assertion_id"] == A2][0]
        self.assertEqual(old["source_span_ids"], [SPAN_B, SPAN_C])

        split_prop = proposal(
            "merge", "R03d", ["assertion", "src_sanche_ed02", A2],
            resolution="human", options=["split"], targets=[A2],
        )
        props = round2_proposals() + [split_prop]
        decisions = round2_decisions(props) + [
            decision(
                split_prop, "split", targets=[A2],
                span_allocation={"new_a": [SPAN_B], "new_b": [SPAN_C]},
            )
        ]
        result = m7_apply.apply_resolutions(base, [view_ed02()], props, decisions)

        self.assertIn(A2, result["knowledge"]["retired_entity_ids"], "旧号必须进 retired")
        self.assertNotIn(
            A2,
            [item["assertion_id"] for item in result["knowledge"]["assertions"]],
            "退役的旧号不得留在活对象里",
        )

        entries = [e for e in result["identity_delta"]["entries"] if e["change_type"] == "split"]
        self.assertEqual(len(entries), 1, "split 必须恰有一条 IdentityDelta")
        entry = entries[0]
        self.assertEqual(entry["from_entity_id"], A2)
        self.assertEqual(entry["entity_kind"], "assertion")
        allocation = entry["span_allocation"]
        self.assertEqual(
            sorted(allocation), ["as_qizheng_000004", "as_qizheng_000005"],
            "占位名须按升序替换为新号（在 A_B=000003 之后顺延，不依赖字典插入序）",
        )
        self.assertEqual(
            [allocation[key] for key in sorted(allocation)], [[SPAN_B], [SPAN_C]]
        )
        self.assertEqual(
            sorted(span for spans in allocation.values() for span in spans),
            [SPAN_B, SPAN_C],
            "span_allocation 的并集必须等于旧对象的全部 source_span_ids",
        )
        for new_id in allocation:
            self.assertIn(new_id, result["created_entity_ids"])

    def test_split_of_referenced_id_is_refused_until_rule_is_ruled(self):
        """被其它活对象引用的号：act/04 未规定引用改指 → fail-closed，绝不写悬空引用。"""
        base = round1()
        split_prop = proposal(
            "merge", "R03d", ["assertion", "src_sanche_ed02", A1],
            resolution="human", options=["split"], targets=[A1],
        )
        props = round2_proposals() + [split_prop]
        decisions = round2_decisions(props) + [
            decision(
                split_prop, "split", targets=[A1],
                span_allocation={"new_a": [SPAN_A], "new_b": [SPAN_C]},
            )
        ]
        with self.assertRaises(AssemblyRefused) as ctx:
            m7_apply.apply_resolutions(base, [view_ed02()], props, decisions)
        self.assertIn("引用", str(ctx.exception))

    # -------------------------------------------------------- R11 退役
    def test_retired_delta_uses_r11_proposal_key(self):
        """F5（ACT 28 contract 二）：退役写进 IdentityDelta 的 `proposal_key` 必须是
        **触发这次退役的 R11 提案键**，不得写死成字面量 `"retire"`——字面量不在任何提案集里，
        Gate 的 `identity_delta_contract`（回到草稿口径后按本轮提案键判）会恒红。
        """
        base = round1()
        prop = retire_proposal(A2)
        props = round2_proposals() + [prop]
        result = m7_apply.apply_resolutions(base, [view_ed02()], props, round2_decisions(props))

        self.assertIn(A2, result["knowledge"]["retired_entity_ids"], "退役目标必须进 retired")
        entries = [e for e in result["identity_delta"]["entries"] if e["change_type"] == "retired"]
        self.assertEqual(len(entries), 1, "本轮恰一条 retired 增量")
        entry = entries[0]
        self.assertEqual(entry["from_entity_id"], A2)
        self.assertEqual(entry["to_entity_ids"], [])
        self.assertEqual(entry["entity_kind"], "assertion")
        self.assertEqual(
            entry["reason_ref"],
            {"kind": "proposal", "proposal_key": prop["proposal_key"]},
            "退役的理由引用必须是触发它的那条 R11 提案键",
        )
        self.assertNotEqual(
            entry["reason_ref"]["proposal_key"], "retire", "不得再写死字面量 'retire'"
        )
        self.assertIn(
            entry["reason_ref"]["proposal_key"],
            {item["proposal_key"] for item in props},
            "理由引用必须落在本轮提案集内（否则 Gate 按草稿口径必红）",
        )

    # -------------------------------------------------------- as_/co_ 碰撞
    def test_as_co_collision_fails_closed(self):
        """contract 三：`as_`/`co_` 不由 M7 发号，只做碰撞检测，冲突即 ID_002 fail-closed。"""
        base = round1()
        clash = view_ed02()
        # 已正式号 A1 在基底上指向「三辰通載」；候选却用同一个号声称完全不同的命题
        clash["candidate_set"]["assertions"][0] = assertion(
            A1, "另一件完全不同的事", CK_TRANSCRIPT, SPAN_C
        )
        clash["candidate_set"]["assertions"][0]["proposition_id"] = "pr_qizheng_000001"

        with self.assertRaises(DuplicateIdentifier) as ctx:
            m7_apply.apply_resolutions(base, [clash], round2_proposals(), round2_decisions())
        self.assertEqual(getattr(ctx.exception, "code", None), "ID_002")

    # -------------------------------------------------------- IdentityDelta 键序
    def test_identity_delta_entry_key_order_verbatim(self):
        """IdentityDelta entry 键序逐字：from_entity_id, to_entity_ids, change_type,
        entity_kind, reason_ref(, span_allocation)；reason_ref 形状逐字。"""
        base = round1()
        props = round2_proposals() + [retire_proposal(A2)]
        result = m7_apply.apply_resolutions(
            base, [view_ed02()], props, round2_decisions(props)
        )
        delta = result["identity_delta"]

        self.assertEqual(
            sorted(delta.keys()), ["base_knowledge_sha256", "entries"], "identity_delta 键集逐字"
        )
        self.assertEqual(
            delta["base_knowledge_sha256"],
            m7_apply.sha256_hex(canonical_json(base)),
            "base_knowledge_sha256 必须是基座规范 JSON 的 sha256",
        )
        self.assertTrue(delta["entries"], "本轮须有身份增量")
        for entry in delta["entries"]:
            keys = list(entry.keys())
            self.assertEqual(
                keys[:5],
                ["from_entity_id", "to_entity_ids", "change_type", "entity_kind", "reason_ref"],
                "entry 键序逐字（多余键只能排在未尾）",
            )
            self.assertLessEqual(len(keys), 6)
            if len(keys) == 6:
                self.assertEqual(keys[5], "span_allocation")
            self.assertEqual(entry["reason_ref"]["kind"], "proposal")
            self.assertTrue(entry["reason_ref"]["proposal_key"])
        self.assertEqual(
            [(e["change_type"], e["from_entity_id"]) for e in delta["entries"]],
            sorted((e["change_type"], e["from_entity_id"]) for e in delta["entries"]),
            "entries 须按 (change_type, from_entity_id) 升序",
        )

    # -------------------------------------------------------- 确定性
    def test_apply_is_deterministic_same_input_same_bytes(self):
        """同一输入两次调用：knowledge_bytes / knowledge_sha256 / identity_delta 逐字节相同。"""
        base = round1()
        first = m7_apply.apply_resolutions(
            base, [view_ed02()], round2_proposals(), round2_decisions()
        )
        second = m7_apply.apply_resolutions(
            copy.deepcopy(base), [view_ed02()], round2_proposals(), round2_decisions()
        )
        self.assertEqual(first["knowledge_bytes"], second["knowledge_bytes"])
        self.assertEqual(first["knowledge_sha256"], second["knowledge_sha256"])
        self.assertEqual(canonical_json(first["identity_delta"]), canonical_json(second["identity_delta"]))
        self.assertEqual(canonical_json(first["collation"]), canonical_json(second["collation"]))
        self.assertEqual(first["resolution_log"], second["resolution_log"])

    # -------------------------------------------------------- §9.3 名实一致
    def test_prev_revision_and_meta_base_agree_still_holds(self):
        """§9.3 不得破坏：apply 的产出必须保住基座身份，使「prev ⟺ meta.base」恒成立。"""
        base = round1(meta={"base_snapshot_revision_id": REV_BASE, "assembly_seq": 2})
        result = m7_apply.apply_resolutions(
            base, [view_ed02()], round2_proposals(), round2_decisions()
        )

        meta = result["knowledge"]["meta"]
        self.assertEqual(
            meta["base_snapshot_revision_id"], REV_BASE,
            "apply 不得丢掉/清空基座身份（否则名实一致护栏可以被 null 蒙混过去）",
        )
        m7_incremental.assert_prev_meta_agreement(REV_BASE, result["knowledge"])
        with self.assertRaises(AssemblyRefused):
            m7_incremental.assert_prev_meta_agreement(None, result["knowledge"])

        genesis_round = m7_apply.apply_resolutions(base_skeleton(), [view_ed01()], [], [])
        self.assertNotIn(
            "meta", genesis_round["knowledge"], "创世轮不凭空写 meta（无基底就是无基底）"
        )
        m7_incremental.assert_prev_meta_agreement(None, genesis_round["knowledge"])

    def test_admit_new_without_formal_id_is_reported_not_dropped(self):
        """真书同形：无正式 `co_` 号的 concept 候选被 admit_new 后不会产生对象——
        必须如实报告（M7 不发 `co_` 号），不得静默丢弃。
        """
        # view_ed01 的 new_concept_candidates = [通載]（无 concept_ref，无正式号）
        r04_prop = proposal(
            "merge", "R04", ["concept", "src_sanche_ed01", "通載"],
            auto_choice="admit_new",
        )
        result = m7_apply.apply_resolutions(
            base_skeleton(), [view_ed01()], [r04_prop], []
        )

        self.assertEqual(
            [item["concept_id"] for item in result["knowledge"]["concepts"]],
            [CO1],
            "只有带正式 co_ 号的 concept_mention 才会产生概念对象",
        )
        rows = result["report"]["admit_new_without_object"]
        self.assertEqual(
            rows,
            [
                {
                    "proposal_key": r04_prop["proposal_key"],
                    "rule_id": "R04",
                    "kind": "concept",
                    "source_id": "src_sanche_ed01",
                    "subject_key": "通載",
                    "reason": "candidate_not_materialized",
                }
            ],
            "admit_new 却没产出对象的提案须逐条如实报告",
        )
        self.assertEqual(
            result["resolution_log"],
            [
                {
                    "proposal_key": r04_prop["proposal_key"],
                    "mode": "auto",
                    "choice": "admit_new",
                }
            ],
        )

    # -------------------------------------------------------- 返回键逐字
    def test_result_keys_verbatim(self):
        """返回键逐字按草稿（`report` 为 §8.1 追加项，见回报 §3.3）。"""
        result = round1_result()
        self.assertEqual(
            list(result.keys()),
            [
                "knowledge", "knowledge_bytes", "knowledge_sha256", "collation",
                "identity_delta", "created_entity_ids", "rebuilt_entity_ids",
                "resolution_log", "report",
            ],
        )
        self.assertEqual(sorted(result["collation"].keys()), ["not_comparable", "relations"])
        self.assertEqual(result["knowledge_bytes"], canonical_json(result["knowledge"]))
        self.assertEqual(result["knowledge_sha256"], m7_apply.sha256_hex(result["knowledge_bytes"]))
        self.assertEqual(result["created_entity_ids"], sorted(result["created_entity_ids"]))
        self.assertEqual(result["rebuilt_entity_ids"], sorted(result["rebuilt_entity_ids"]))
        m7_model.validate_snapshot_knowledge(result["knowledge"])

    # -------------------------------------------------------- 跨波等价（最强判据）
    def test_apply_round1_equals_accepted_genesis_gold(self):
        """apply 的创世轮必须逐字节等于已验收创世引擎在 mini_release01 ed01 上的输出。"""
        manifest = yaml.safe_load((FIXTURE / "manifest.yaml").read_text(encoding="utf-8"))
        ed01 = manifest["editions"][0]
        view_dir = FIXTURE / ed01["views_dir"]
        cset = json.loads((view_dir / "candidate_set.json").read_text(encoding="utf-8"))
        reviewed = json.loads((view_dir / "reviewed_edition.json").read_text(encoding="utf-8"))

        base = empty_snapshot_knowledge(
            manifest["technique_id"],
            {"pat_%s" % manifest["technique_id"]: list(manifest["id_range"]["pattern"])},
        )
        res = m7_apply.apply_resolutions(
            base,
            [{"source_id": ed01["source_id"], "candidate_set": cset, "reviewed_edition": reviewed}],
            propose_genesis(cset, reviewed)["proposals"],
            [],
        )
        golden = (FIXTURE / manifest["expected"]["round1"]).read_bytes()
        self.assertEqual(
            golden, res["knowledge_bytes"], "apply 的创世轮与已验收创世引擎输出不一致"
        )

    # -------------------------------------------------------- 裁定校验
    def test_choice_not_in_options_refused(self):
        """validate_decision：choice ∉ options → SchemaViolation(SCH_002)；未决提案必须拒收。"""
        base = round1()
        props = round2_proposals()
        alias_prop = [p for p in props if p["kind"] == "alias"][0]
        with self.assertRaises(SchemaViolation) as bad_choice:
            m7_apply.apply_resolutions(
                base, [view_ed02()], props,
                [decision(alias_prop, "attach:%s" % CO1)],
            )
        self.assertEqual(getattr(bad_choice.exception, "code", None), "SCH_002")

        with self.assertRaises(AssemblyRefused) as pending:
            m7_apply.apply_resolutions(base, [view_ed02()], [alias_prop], [])
        self.assertIn("未决", str(pending.exception))

        with self.assertRaises(MissingReference) as unknown:
            m7_apply.apply_resolutions(
                base, [view_ed02()],
                [alias_prop],
                [
                    decision(alias_prop, "accept_alias", targets=[CO1]),
                    {
                        "proposal_set_revision_id": None,
                        "proposal_key": "alias:" + "f" * 32,
                        "choice": "accept_alias",
                        "target_entity_ids": [],
                        "seen_revision_id": None,
                        "decision_type": None,
                    },
                ],
            )
        self.assertEqual(getattr(unknown.exception, "code", None), "REF_001")


if __name__ == "__main__":
    unittest.main()

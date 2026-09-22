#!/usr/bin/env python
"""mini_release01 多版次金标 fixture 的确定性生成器（act/impl-07/20，INC-F）。

用法（在仓库根目录执行）：

    .venv/bin/python pipeline/corpus/_fixture/mini_release01/tools/build_fixture.py
    .venv/bin/python pipeline/corpus/_fixture/mini_release01/tools/build_fixture.py \
        --out /tmp/mini_release01_rebuild        # 重放比对用

性质与约束
----------
1. 输入只有本文件内的**场景表**与只读的 `../mini_ed01/spans.yaml`；不写时间戳、
   不写绝对路径、不使用随机值。同一输入两次运行逐字节相同。
2. 两版次视图的 Span 引用**锚定 mini_ed01 真实 spans**（真实 span_id、真实偏移、
   `quote_sha256 = sha256(span.text)`），不复制、不改写 mini_ed01 任何文件。
3. 期望产物（多版本 Snapshot 金标）：
   - `expected/snapshot_r1.json`：由**已验收创世引擎**（`pipeline.assembly.genesis`）
     在本文件的 ed01 视图上现算，逐字节等于该引擎的 `knowledge_bytes`；
   - `expected/snapshot_r2.json`：由本文件内的**场景表逐项字面量**写出
     （D-10 采纳 A：不得实现通用增量汇编算法）。
4. `manifest.yaml` 的 `files[]` 只登记本生成器产出的文件（不含自身、README.md、
   verify.sh），避免 mini_ed01 README §6 第 2 条记录的哈希环。
5. `ed99` 与 `9000NN` 是**约定标识**，不是新 ID 前缀（不进
   `openspec/id-prefix-registry.md`）。
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
if not (REPO_ROOT / "openspec").is_dir():  # pragma: no cover - 防呆
    raise SystemExit("无法定位仓库根目录（自 %s 上溯 5 层）" % Path(__file__).resolve())

FIXTURE_DIR = Path(__file__).resolve().parents[1]
MINI_ED01_SPANS = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01" / "spans.yaml"

# mini_ed01 金标 sha256（impl-07 README §1.2 冻结值）；锚定失败即停手
MINI_ED01_SPANS_SHA256 = "ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef"

sys.path.insert(0, str(REPO_ROOT))
from pipeline.assembly.canonical import canonical_json, content_sha256, make_key, nfc_key, sha256_hex  # noqa: E402
from pipeline.assembly.genesis import assemble_genesis, propose_genesis  # noqa: E402
from pipeline.assembly.gate import evaluate_genesis  # noqa: E402
from pipeline.ledger import ids  # noqa: E402

TECHNIQUE_ID = "qizheng"
WORK_KEY = "sanche"
WORK_TITLE = "三辰通載三十卷"
EDITION_NOTE = "影宋鈔本（fixture ed99 为合成保留号，非真实第二版次）"

# 约定：合成对象号段与协议标记（不是新前缀）
SYNTHETIC_OBJECT_RANGE = [900001, 900099]
NON_PREFIX_MARKERS = ["ed99"]

# 夹具视图使用的已登记前缀家族（登记册 §3.1–§3.4；不含 ent_/rel_ 等 M8 下游前缀）
ID_FAMILIES_USED = [
    "art_", "as_", "cg_", "co_", "pat_", "pkg_", "pr_", "prun_", "rev_",
    "sch_", "src_", "srun_", "ss_", "sv_",
]


def const(prefix: str, suffix: str) -> str:
    """生成可读的定长常量标识（32 位十六进制体，零填充）。"""
    body = ("0" * (32 - len(suffix)) + suffix).lower()
    assert len(body) == 32 and all(c in "0123456789abcdef" for c in body), suffix
    return prefix + body


# --------------------------------------------------------------------- 版次常量
ED01 = {
    "edition_key": "ed01",
    "source_id": "src_sanche_ed01",
    "edition_part_artifact_id": const("art_", "e1"),
    "role": "first_edition",
    "validation_package_suffix": "b01",
    "ledger_constants": {
        "processing_run_id": const("prun_", "01"),
        "m4_step_run_id": const("srun_", "04"),
        "m6_step_run_id": const("srun_", "06"),
        "candidate_set_artifact_id": const("art_", "10"),
        "candidate_set_revision_id": const("rev_", "11"),
        "candidate_package_artifact_id": const("art_", "12"),
        "candidate_package_revision_id": const("rev_", "12"),
        "reviewed_edition_artifact_id": const("art_", "13"),
        "reviewed_edition_revision_id": const("rev_", "13"),
        "reviewed_edition_package_artifact_id": const("art_", "14"),
        "reviewed_edition_package_revision_id": const("rev_", "14"),
        "m6_stage_package_id": const("pkg_m6_", "e1"),
        "m6_package_revision_id": const("rev_", "e1"),
    },
}
ED99 = {
    "edition_key": "ed99",
    "source_id": "src_sanche_ed99",
    "edition_part_artifact_id": const("art_", "99"),
    "role": "second_edition_synthetic",
    "validation_package_suffix": "b02",
    "ledger_constants": {
        "processing_run_id": const("prun_", "02"),
        "m4_step_run_id": const("srun_", "99"),
        "m6_step_run_id": const("srun_", "98"),
        "candidate_set_artifact_id": const("art_", "90"),
        "candidate_set_revision_id": const("rev_", "90"),
        "candidate_package_artifact_id": const("art_", "91"),
        "candidate_package_revision_id": const("rev_", "91"),
        "reviewed_edition_artifact_id": const("art_", "92"),
        "reviewed_edition_revision_id": const("rev_", "92"),
        "reviewed_edition_package_artifact_id": const("art_", "93"),
        "reviewed_edition_package_revision_id": const("rev_", "93"),
        "m6_stage_package_id": const("pkg_m6_", "99"),
        "m6_package_revision_id": const("rev_", "99"),
    },
}

CORPUS_SPANS_REVISION_ID = const("rev_", "a01")
SNAPSHOT_ARTIFACT_ID = const("art_", "f1")
SNAPSHOT_REVISION_R1 = const("rev_", "f1")
SNAPSHOT_REVISION_R2 = const("rev_", "f2")

SV_1 = const("sv_", "1")
SV_2 = const("sv_", "2")
CG_1 = const("cg_", "1")

# --------------------------------------------------------------------- 场景表
# 三个真实 span（mini_ed01 前 3 页）承载全部证据；不新增任何原文。
SPAN_SURNAME = "ss_sanche_ed01_p0001_s01"      # 三辰通載
SPAN_AUTHOR = "ss_sanche_ed01_p0001_s02"       # （宋）錢如璧撰
SPAN_TITLE = "ss_sanche_ed01_p0003_s03"        # 三辰通載目錄
SPAN_PATTERN = "ss_sanche_ed01_p0003_s05"      # 貴格之圗

# 对齐单元（D-07 可比单元 = (work_key, collation_key)）；冒号/连字符形态，不作前缀
CK_TRANSCRIPT = "sanche-0001"
CK_AUTHOR = "sanche-0002"
CK_PATTERN = "sanche-0003"
CK_TITLE_INDEX = "sanche-0004"

A1 = "as_qizheng_900001"
A2 = "as_qizheng_900002"
A3 = "as_qizheng_900003"
A_NEW = "as_qizheng_900004"
PAT = "pat_qizheng_900001"
CO = "co_qizheng_900001"
SCH_CLASSIC = "sch_qizheng_001"
SCH_TIANGONG = "sch_qizheng_002"

ID_RANGE_CONFIG = {"pattern": list(SYNTHETIC_OBJECT_RANGE)}  # 独立副本，避免 YAML 输出锚点（非确定性风险）


def evidence(span: dict) -> dict:
    """由真实 span 生成一条证据（偏移与引文逐字取自金标 span）。"""
    return {
        "source_span_id": span["span_id"],
        "start_offset": span["start_offset"],
        "end_offset": span["end_offset"],
        "quote": span["text"],
        "quote_sha256": sha256_hex(span["text"].encode("utf-8")),
        "support_type": "direct",
    }


def evidence_link(entity_id: str, span: dict) -> dict:
    """M6 reviewed_edition 证据链（不含 quote 正文，含 corpus_spans 修订）。"""
    return {
        "entity_id": entity_id,
        "source_span_id": span["span_id"],
        "start_offset": span["start_offset"],
        "end_offset": span["end_offset"],
        "quote_sha256": sha256_hex(span["text"].encode("utf-8")),
        "corpus_spans_revision_id": CORPUS_SPANS_REVISION_ID,
    }


def candidate_assertion(assertion_id, proposition, collation_key, span, origin_index, school_ids):
    return {
        "assertion_id": assertion_id,
        "proposition_id": "pr_%s_%s" % (TECHNIQUE_ID, assertion_id.split("_")[-1]),
        "proposition": proposition,
        "relation": "supports",
        "evidence": [evidence(span)],
        "conditions": [],
        "exceptions": [],
        "concept_refs": [],
        "school_ids": list(school_ids),
        "layer": "general",
        "content_status": "machine_extracted",
        "collation_key": collation_key,
        "origin": {"lane": "main", "item_index": origin_index},
    }


def candidate_pattern(name, assertion_ids, interpretation):
    return {
        "pattern_id": PAT,
        "name": name,
        "assertion_ids": list(assertion_ids),
        "evidence": [],
        "interpretation": interpretation,
        "interpretation_status": "captured",
        "recognition_rule_status": "not_captured",
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 0},
    }


def candidate_school_view(sv_id, school_id, subject_entity_id, source_id, source_span_id):
    return {
        "school_view_id": sv_id,
        "school_id": school_id,
        "subject_entity_id": subject_entity_id,
        "claim_refs": [subject_entity_id],
        "conflict_group_id": CG_1,
        "changes_current_judgment": True,
        "source_refs": [{"source_id": source_id, "source_span_id": source_span_id}],
        "evidence": [],
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 0},
    }


def counts_of(cset: dict) -> dict:
    base = {
        "assertions": len(cset["assertions"]),
        "patterns": len(cset["patterns"]),
        "school_views": len(cset["school_views"]),
        "concept_mentions": len(cset["concept_mentions"]),
        "new_concept_candidates": len(cset["new_concept_candidates"]),
        "rejected": len(cset["rejected"]),
        "disputes": len(cset["disputes"]),
    }
    return base


def build_candidate_set(edition: dict, spans: dict, payload: dict) -> dict:
    cset = {
        "schema_version": "0.1.0-draft",
        "synthetic": True,
        "technique_id": TECHNIQUE_ID,
        "source_id": edition["source_id"],
        "edition_part_artifact_id": edition["edition_part_artifact_id"],
        "evidence_level": "glyphbox_level",
        "span_layer": "structural",
        "source_channels": {
            "assertion": {"main": "text"},
            "pattern": {"main": "text"},
            "concept_mention": {"main": "text"},
        },
        "collation_units": payload["collation_units"],
        "assertions": payload["assertions"],
        "patterns": payload["patterns"],
        "school_views": payload["school_views"],
        "concept_mentions": payload["concept_mentions"],
        "new_concept_candidates": payload["new_concept_candidates"],
        "rejected": [],
        "disputes": [],
    }
    cset["counts"] = counts_of(cset)
    return cset


def build_reviewed_edition(edition: dict, payload: dict) -> dict:
    suffix = payload["decision_suffix"]

    def decision_id(idx: int) -> str:
        return const("rev_", "%s%03d" % (suffix, idx + 1))

    approved = []
    for idx, item in enumerate(payload["approved"]):
        approved.append(
            {
                "entity_id": item[0],
                "kind": item[1],
                "artifact_revision_id": edition["ledger_constants"]["candidate_set_revision_id"],
                "content_status": "machine_extracted",
                "decision_revision_ids": [decision_id(idx)],
            }
        )
    decisions = []
    for idx, item in enumerate(payload["approved"]):
        decisions.append(
            {
                "decision_revision_id": decision_id(idx),
                "queue_item_id": "%s#review_source_fidelity" % item[0],
                "target_entity_id": item[0],
                "seen_artifact_revision_id": edition["ledger_constants"]["candidate_set_revision_id"],
                "current_target_revision_id": edition["ledger_constants"]["candidate_set_revision_id"],
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
    links = []
    for item in payload["evidence_link_targets"]:
        links.append(evidence_link(item[0], item[1]))
    return {
        "schema_version": "0.1.0-draft",
        "synthetic": True,
        "edition_part_artifact_id": edition["edition_part_artifact_id"],
        "candidate_set_revision_id": edition["ledger_constants"]["candidate_set_revision_id"],
        "candidate_package_revision_id": edition["ledger_constants"]["candidate_package_revision_id"],
        "validation_package_revision_id": const("rev_", edition["validation_package_suffix"]),
        "approved": approved,
        "rejected": [],
        "decisions": decisions,
        "evidence_links": links,
        "school_views": [
            {
                "school_view_id": sv["school_view_id"],
                "school_id": sv["school_id"],
                "subject_entity_id": sv["subject_entity_id"],
                "conflict_group_id": sv["conflict_group_id"],
                "changes_current_judgment": sv["changes_current_judgment"],
            }
            for sv in payload["school_views"]
        ],
        "correction_request_revision_ids": [],
        "rework_impact_report_revision_id": None,
        "unresolved_count": 0,
    }


def build_reviewed_edition_package(edition: dict, payload: dict) -> dict:
    return {
        "schema_version": "0.1.0-draft",
        "synthetic": True,
        "reviewed_edition_revision_id": edition["ledger_constants"]["reviewed_edition_revision_id"],
        "decision_revision_ids": [
            const("rev_", "%s%03d" % (payload["decision_suffix"], idx + 1))
            for idx in range(len(payload["approved"]))
        ],
        "decision_count": len(payload["approved"]),
        "approved_count": len(payload["approved"]),
        "rejected_count": 0,
        "unresolved_count": 0,
        "correction_request_revision_ids": [],
        "rework_impact_report_revision_id": None,
    }


def scenario_ed01(spans: dict) -> dict:
    a1 = candidate_assertion(A1, spans[SPAN_SURNAME]["text"], CK_TRANSCRIPT, spans[SPAN_SURNAME], 0, [SCH_CLASSIC])
    a2 = candidate_assertion(A2, spans[SPAN_AUTHOR]["text"], CK_AUTHOR, spans[SPAN_AUTHOR], 1, [])
    a3 = candidate_assertion(A3, spans[SPAN_PATTERN]["text"], CK_PATTERN, spans[SPAN_PATTERN], 2, [])
    pattern = candidate_pattern("三辰通載貴格", [A1, A3], "卷首目錄所見貴格，機器抽取未經人工複核")
    sv = candidate_school_view(SV_1, SCH_CLASSIC, A1, ED01["source_id"], SPAN_SURNAME)
    concept = {
        "surface": "三辰",
        "concept_ref": CO,
        "evidence": [evidence(spans[SPAN_SURNAME])],
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 0},
    }
    unbound = {
        "surface": "通載",
        "technique_id": TECHNIQUE_ID,
        "evidence": [evidence(spans[SPAN_TITLE])],
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 1},
    }
    return {
        "collation_units": [
            {"collation_key": CK_TRANSCRIPT, "present": True},
            {"collation_key": CK_AUTHOR, "present": True},
            {"collation_key": CK_PATTERN, "present": True},
        ],
        "assertions": [a1, a2, a3],
        "patterns": [pattern],
        "school_views": [sv],
        "concept_mentions": [concept],
        "new_concept_candidates": [unbound],
        "approved": [
            (A1, "assertion"), (A2, "assertion"), (A3, "assertion"),
            (PAT, "pattern"), (CO, "concept"), (SV_1, "school_view"),
        ],
        "evidence_link_targets": [(A1, spans[SPAN_SURNAME]), (A2, spans[SPAN_AUTHOR]), (A3, spans[SPAN_PATTERN])],
        "decision_suffix": "d",
    }


def scenario_ed99(spans: dict) -> dict:
    # A1 以基底已正式的 as_ 号携带（D-04 A：M4 全局唯一发号，M7 只做碰撞检测），
    # 命题与对齐单元与 ed01 逐字相同 → 并入（attach，保号）并新增一条证据。
    a1 = candidate_assertion(A1, spans[SPAN_SURNAME]["text"], CK_TRANSCRIPT, spans[SPAN_TITLE], 0, [])
    a_new = candidate_assertion(A_NEW, spans[SPAN_TITLE]["text"], CK_TITLE_INDEX, spans[SPAN_TITLE], 1, [SCH_TIANGONG])
    pattern = candidate_pattern("三辰通載貴格", [A1, A_NEW], "第二版次同格局，另添目錄主張")
    sv = candidate_school_view(SV_2, SCH_TIANGONG, A_NEW, ED99["source_id"], SPAN_TITLE)
    concept = {
        "surface": "通載",
        "concept_ref": CO,
        "evidence": [evidence(spans[SPAN_TITLE])],
        "content_status": "machine_extracted",
        "origin": {"lane": "main", "item_index": 0},
    }
    return {
        "collation_units": [
            {"collation_key": CK_TRANSCRIPT, "present": True},
            {"collation_key": CK_TITLE_INDEX, "present": True},
        ],
        "assertions": [a1, a_new],
        "patterns": [pattern],
        "school_views": [sv],
        "concept_mentions": [concept],
        "new_concept_candidates": [],
        "approved": [
            (A1, "assertion"), (A_NEW, "assertion"),
            (PAT, "pattern"), (CO, "concept"), (SV_2, "school_view"),
        ],
        "evidence_link_targets": [(A1, spans[SPAN_TITLE]), (A_NEW, spans[SPAN_TITLE])],
        "decision_suffix": "e",
    }


def scenario_r2(spans: dict, ed01_payload: dict, ed99_payload: dict) -> dict:
    """增量轮（第二轮）金标：逐项字面量（D-10 采纳 A，不实现通用算法）。"""
    ed01_cset_pattern = ed01_payload["patterns"][0]
    ed99_cset_pattern = ed99_payload["patterns"][0]

    def assertion(assertion_id, subject, source_id, proposition, collation_key, spans_used, sv_ids):
        prop_nfc = nfc_key(proposition)
        # Snapshot 的 evidence 形状与创世引擎一致：只保留 source_span_id / 偏移 / quote_sha256
        evs = sorted(
            (
                {
                    "source_span_id": spans[span_id]["span_id"],
                    "start_offset": spans[span_id]["start_offset"],
                    "end_offset": spans[span_id]["end_offset"],
                    "quote_sha256": sha256_hex(spans[span_id]["text"].encode("utf-8")),
                }
                for span_id in spans_used
            ),
            key=lambda x: (x["source_span_id"], x["start_offset"], x["end_offset"]),
        )
        return {
            "assertion_id": assertion_id,
            "subject_entity_id": subject,
            "source_id": source_id,
            "proposition": prop_nfc,
            "collation_key": collation_key,
            "text_sha256": sha256_hex(prop_nfc.encode("utf-8")),
            "source_span_ids": sorted({ev["source_span_id"] for ev in evs}),
            "evidence": evs,
            "school_view_ids": sv_ids,
            "content_status": "machine_extracted",
        }

    editions = [
        {
            "source_id": ED01["source_id"],
            "work_key": WORK_KEY,
            "reviewed_edition_package_revision_id": ED01["ledger_constants"]["reviewed_edition_package_revision_id"],
            "reviewed_edition_revision_id": ED01["ledger_constants"]["reviewed_edition_revision_id"],
            "stage_package_id": ED01["ledger_constants"]["m6_stage_package_id"],
            "edition_part_artifact_ids": [ED01["edition_part_artifact_id"]],
            "edition_complete": False,
            "evidence_level": "glyphbox_level",
            "corpus_spans_revision_id": CORPUS_SPANS_REVISION_ID,
        },
        {
            "source_id": ED99["source_id"],
            "work_key": WORK_KEY,
            "reviewed_edition_package_revision_id": ED99["ledger_constants"]["reviewed_edition_package_revision_id"],
            "reviewed_edition_revision_id": ED99["ledger_constants"]["reviewed_edition_revision_id"],
            "stage_package_id": ED99["ledger_constants"]["m6_stage_package_id"],
            "edition_part_artifact_ids": [ED99["edition_part_artifact_id"]],
            "edition_complete": False,
            "evidence_level": "glyphbox_level",
            "corpus_spans_revision_id": CORPUS_SPANS_REVISION_ID,
        },
    ]

    concepts = [
        {
            "concept_id": CO,
            "name": "三辰",
            "aliases": ["通載"],
            "provenance": [
                {
                    "source_id": ED01["source_id"],
                    "content_sha256": content_sha256({"name": "三辰", "aliases": []}),
                    "content_status": "machine_extracted",
                },
                {
                    "source_id": ED99["source_id"],
                    "content_sha256": content_sha256({"name": "通載", "aliases": []}),
                    "content_status": "machine_extracted",
                },
            ],
        }
    ]

    patterns = [
        {
            "pattern_id": PAT,
            "concept_id": None,
            "name": "三辰通載貴格",
            "aliases": [],
            "rules": [],
            "assertion_ids": sorted([A1, A3, A_NEW]),
            "school_view_ids": [],
            "recognition_rule_status": "not_captured",
            "provenance": [
                {
                    "source_id": ED01["source_id"],
                    "content_sha256": content_sha256(ed01_cset_pattern),
                    "content_status": "machine_extracted",
                },
                {
                    "source_id": ED99["source_id"],
                    "content_sha256": content_sha256(ed99_cset_pattern),
                    "content_status": "machine_extracted",
                },
            ],
        }
    ]

    assertions = [
        assertion(A1, PAT, ED01["source_id"], spans[SPAN_SURNAME]["text"], CK_TRANSCRIPT,
                  [SPAN_SURNAME, SPAN_TITLE], [SV_1]),
        assertion(A2, None, ED01["source_id"], spans[SPAN_AUTHOR]["text"], CK_AUTHOR,
                  [SPAN_AUTHOR], []),
        assertion(A3, PAT, ED01["source_id"], spans[SPAN_PATTERN]["text"], CK_PATTERN,
                  [SPAN_PATTERN], []),
        assertion(A_NEW, PAT, ED99["source_id"], spans[SPAN_TITLE]["text"], CK_TITLE_INDEX,
                  [SPAN_TITLE], [SV_2]),
    ]
    assertions.sort(key=lambda a: a["assertion_id"])

    school_views = [
        {
            "school_view_id": SV_1,
            "school_id": SCH_CLASSIC,
            "subject_entity_id": A1,
            "conflict_group_id": CG_1,
            "source_conflict_group_id": CG_1,
            "claim_refs": [A1],
            "changes_current_judgment": True,
            "content_status": "machine_extracted",
        },
        {
            "school_view_id": SV_2,
            "school_id": SCH_TIANGONG,
            "subject_entity_id": A_NEW,
            "conflict_group_id": CG_1,
            "source_conflict_group_id": CG_1,
            "claim_refs": [A_NEW],
            "changes_current_judgment": True,
            "content_status": "machine_extracted",
        },
    ]
    school_views.sort(key=lambda s: s["school_view_id"])

    conflict_groups = [
        {
            "conflict_group_id": CG_1,
            "member_school_view_ids": [SV_1, SV_2],
            "first_layer_display": True,
            "resolutions": [],
        }
    ]

    relations = [
        {
            "relation_key": make_key("distinct_from", [A1, A_NEW]),
            "from_entity_id": A_NEW,
            "to_entity_id": A1,
            "relation_kind": "distinct_from",
            "detail": {
                "reason": "near_identical_text_not_folded",
                "collation_keys": [CK_TRANSCRIPT, CK_TITLE_INDEX],
            },
            "resolution": {"mode": "auto"},
        }
    ]

    return {
        "technique_id": TECHNIQUE_ID,
        "id_allocation": {"pat_%s" % TECHNIQUE_ID: int(PAT.split("_")[-1])},
        "id_range": {"pat_%s" % TECHNIQUE_ID: list(SYNTHETIC_OBJECT_RANGE)},
        "allocated_pattern_ids": [],
        "retired_entity_ids": [],
        "editions": editions,
        "concepts": concepts,
        "patterns": patterns,
        "assertions": assertions,
        "school_views": school_views,
        "conflict_groups": conflict_groups,
        "relations": relations,
    }


def upstream_assumptions() -> list:
    return [
        {
            "id": "A1",
            "statement": "第二版次的 M4 视图可携带基底已正式的 pat_ 号（D-04 采纳 A）；M6 审核结论含 pattern/school_view/concept 三类（契约允许的 kind 闭集）。",
            "real_m6_observed": "真书 qianyuan_w8 的 m6 审核结论 26/26 全为 assertion，无 pattern/school_view；候选 candidate_set.patterns=2、school_views=0、concept_mentions=0。",
        },
        {
            "id": "A2",
            "statement": "每个版次视图声明 collation_units 与 assertion.collation_key（D-07 可比单元 (work_key, collation_key) 的前提）。",
            "real_m6_observed": "真书 candidate_set 无 collation_units 键，26 条 assertion 的 collation_key 全为 null。",
        },
        {
            "id": "A3",
            "statement": "两个版次共享同一 corpus_spans 修订（同一底本重出，evidence 锚定同一批真实 span）。",
            "real_m6_observed": "真书账本每版次各有自己的 corpus_spans 修订（rev_a163a3e4162c41b48e6829e676b11b01 等）。",
        },
        {
            "id": "A4",
            "statement": "视图对象号取自 9000NN 保留号段（约定标识，不是新 ID 前缀）。",
            "real_m6_observed": "真书对象号取自 000001 起的常规号段；两者不冲突（fixture 只进临时 Ledger）。",
        },
    ]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_fixture")
    parser.add_argument("--out", default=str(FIXTURE_DIR), help="输出目录（默认原地）")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()

    spans_raw = MINI_ED01_SPANS.read_bytes()
    actual_sha = hashlib.sha256(spans_raw).hexdigest()
    if actual_sha != MINI_ED01_SPANS_SHA256:
        print("FAIL mini_ed01 金标 spans.yaml sha256 已变：%s != %s" % (actual_sha, MINI_ED01_SPANS_SHA256))
        return 1
    spans_doc = yaml.safe_load(spans_raw.decode("utf-8"))
    spans = {s["span_id"]: s for s in spans_doc["spans"]}
    for span_id in (SPAN_SURNAME, SPAN_AUTHOR, SPAN_TITLE, SPAN_PATTERN):
        if span_id not in spans:
            print("FAIL 金标 spans.yaml 缺 span: %s" % span_id)
            return 1
    if spans_doc["evidence_level"] != "glyphbox_level":
        print("FAIL 金标 evidence_level 期望 glyphbox_level，实际 %r" % spans_doc["evidence_level"])
        return 1

    payload_ed01 = scenario_ed01(spans)
    payload_ed99 = scenario_ed99(spans)

    ed01_cset = build_candidate_set(ED01, spans, payload_ed01)
    ed01_reviewed = build_reviewed_edition(ED01, payload_ed01)
    ed01_package = build_reviewed_edition_package(ED01, payload_ed01)
    ed99_cset = build_candidate_set(ED99, spans, payload_ed99)
    ed99_reviewed = build_reviewed_edition(ED99, payload_ed99)
    ed99_package = build_reviewed_edition_package(ED99, payload_ed99)

    # ---- r1：由已验收创世引擎现算（不得手写）
    proposals = propose_genesis(ed01_cset, ed01_reviewed)
    asm = assemble_genesis(ed01_cset, ed01_reviewed, proposals["proposals"], id_range=ID_RANGE_CONFIG)
    gate = evaluate_genesis(candidate_set=ed01_cset, reviewed_edition=ed01_reviewed, knowledge=asm["knowledge"])
    if not gate["passed"]:
        failed = {k: v["detail"] for k, v in gate["checks"].items() if not v["passed"]}
        print("FAIL 创世引擎拒绝 fixture ed01 视图，Gate 未通过: %s" % failed)
        return 1
    r1_bytes = asm["knowledge_bytes"]

    # ---- r2：场景表逐项字面量 + 规范化哈希
    r2_knowledge = scenario_r2(spans, payload_ed01, payload_ed99)
    from pipeline.assembly.model import validate_snapshot_knowledge
    validate_snapshot_knowledge(r2_knowledge)
    r2_bytes = canonical_json(r2_knowledge)

    revisions_plan = {
        "technique_id": TECHNIQUE_ID,
        "snapshot_artifact_id": SNAPSHOT_ARTIFACT_ID,
        "note": "D-03 采纳 A：每 technique 一个 Snapshot Artifact，每轮写新 rev_，prev_revision_id 指向基底修订。",
        "round1_note": (
            "r1 由已验收创世引擎（pipeline.assembly.genesis）现算；其 editions[]."
            "reviewed_edition_package_revision_id / stage_package_id 仍是引擎当前未接线真实包身份时的"
            "占位值，B 波接线真实包身份后须按本生成器重建 r1。"
        ),
        "revisions": [
            {
                "assembly_seq": 1,
                "snapshot_revision_id": SNAPSHOT_REVISION_R1,
                "base_snapshot_revision_id": None,
                "prev_revision_id": None,
                "supersedes_revision_id": None,
                "knowledge_file": "expected/snapshot_r1.json",
                "knowledge_sha256": hashlib.sha256(r1_bytes).hexdigest(),
                "editions": [ED01["source_id"]],
            },
            {
                "assembly_seq": 2,
                "snapshot_revision_id": SNAPSHOT_REVISION_R2,
                "base_snapshot_revision_id": SNAPSHOT_REVISION_R1,
                "prev_revision_id": SNAPSHOT_REVISION_R1,
                "supersedes_revision_id": SNAPSHOT_REVISION_R1,
                "knowledge_file": "expected/snapshot_r2.json",
                "knowledge_sha256": hashlib.sha256(r2_bytes).hexdigest(),
                "editions": [ED01["source_id"], ED99["source_id"]],
            },
        ],
    }

    # ---- 落盘（确定性：视图为可读 JSON，金标为规范 JSON 字节）
    generated = {}
    generated["ed01/candidate_set.json"] = json.dumps(ed01_cset, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    generated["ed01/reviewed_edition.json"] = json.dumps(ed01_reviewed, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    generated["ed01/reviewed_edition_package.json"] = json.dumps(ed01_package, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    generated["ed99/candidate_set.json"] = json.dumps(ed99_cset, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    generated["ed99/reviewed_edition.json"] = json.dumps(ed99_reviewed, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    generated["ed99/reviewed_edition_package.json"] = json.dumps(ed99_package, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    generated["expected/snapshot_r1.json"] = r1_bytes.decode("utf-8")
    generated["expected/snapshot_r2.json"] = r2_bytes.decode("utf-8")
    generated["expected/snapshot_revisions.yaml"] = yaml.safe_dump(
        revisions_plan, allow_unicode=True, sort_keys=True, default_flow_style=False
    )

    for name in generated:
        write_text(out / name, generated[name])

    # ---- manifest（最后写：files[] 登记上文产物，不含自身/README/verify.sh）
    files = [
        {
            "path": name,
            "role": (
                "view_candidate_set" if name.endswith("candidate_set.json")
                else "view_reviewed_edition" if name.endswith("reviewed_edition.json")
                else "view_reviewed_edition_package" if name.endswith("reviewed_edition_package.json")
                else "expected_snapshot" if name.startswith("expected/snapshot_r")
                else "expected_snapshot_revisions"
            ),
            "sha256": hashlib.sha256(generated[name].encode("utf-8")).hexdigest(),
        }
        for name in sorted(generated)
    ]

    editions = []
    for edition in (ED01, ED99):
        block = {k: v for k, v in edition.items()}
        block["views_dir"] = edition["edition_key"]
        block["view_files"] = [
            "candidate_set.json", "reviewed_edition.json", "reviewed_edition_package.json"
        ]
        editions.append(block)

    manifest = {
        "fixture_id": "mini_release01",
        "synthetic": True,
        "content_status": "machine_extracted",
        "work_title": WORK_TITLE,
        "work_key": WORK_KEY,
        "edition_note": EDITION_NOTE,
        "technique_id": TECHNIQUE_ID,
        "note": "内容为结构验收宿主，不作知识来源、证据来源或发布输入。",
        "id_range": {"pattern": list(SYNTHETIC_OBJECT_RANGE)},
        "editions": editions,
        "span_anchor": {
            "path": "../mini_ed01/spans.yaml",
            "sha256": MINI_ED01_SPANS_SHA256,
            "evidence_level": spans_doc["evidence_level"],
            "corpus_spans_revision_id": CORPUS_SPANS_REVISION_ID,
            "note": "ed01/ed99 全部证据链锚定 mini_ed01 真实 span（id、偏移、quote_sha256 逐字一致）；本目录不含任何页图。",
        },
        "conventions": {
            "synthetic_edition_seq": "ed99",
            "synthetic_object_seq_range": list(SYNTHETIC_OBJECT_RANGE),
            "non_prefix_markers": list(NON_PREFIX_MARKERS),
            "note": "ed99 与 9000NN 是约定标识，不是新 ID 前缀；不写入 openspec/id-prefix-registry.md。",
        },
        "id_families_used": ID_FAMILIES_USED,
        "upstream_assumptions": upstream_assumptions(),
        "expected": {
            "snapshot_revisions": "expected/snapshot_revisions.yaml",
            "round1": "expected/snapshot_r1.json",
            "round2": "expected/snapshot_r2.json",
        },
        "files": files,
    }
    write_text(out / "manifest.yaml", yaml.safe_dump(manifest, allow_unicode=True, sort_keys=True, default_flow_style=False))

    # 常量自检（防呆：任何非法标识都在生成时暴露）
    for edition in (ED01, ED99):
        ids.validate("source_id", edition["source_id"])
        ids.validate("artifact_id", edition["edition_part_artifact_id"])
        for key, value in edition["ledger_constants"].items():
            kind = "stage_package_id" if key == "m6_stage_package_id" else (
                "artifact_id" if key.endswith("artifact_id") else
                "processing_run_id" if key == "processing_run_id" else
                "step_run_id" if key.endswith("step_run_id") else "artifact_revision_id"
            )
            if kind == "stage_package_id":
                ids.validate("stage_package_id", value)
            else:
                ids.validate(kind, value)
    ids.validate("artifact_id", SNAPSHOT_ARTIFACT_ID)
    ids.validate("artifact_revision_id", SNAPSHOT_REVISION_R1)
    ids.validate("artifact_revision_id", SNAPSHOT_REVISION_R2)
    ids.validate("artifact_revision_id", CORPUS_SPANS_REVISION_ID)

    print("BUILD OK %s" % out)
    for item in files:
        print("  %s  %s" % (item["sha256"], item["path"]))
    print("  r1 knowledge_sha256=%s" % revisions_plan["revisions"][0]["knowledge_sha256"])
    print("  r2 knowledge_sha256=%s" % revisions_plan["revisions"][1]["knowledge_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

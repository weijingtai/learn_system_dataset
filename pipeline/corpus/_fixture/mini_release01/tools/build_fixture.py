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
3. 期望产物（多版本 Snapshot 金标）——**一律由实跑产出，不许手写**（CHARTER §17、§19.3）：
   - `expected/snapshot_r1.json`：由**已验收创世引擎**（`pipeline.assembly.genesis`）
     在本文件的 ed01 视图上现算，逐字节等于该引擎的 `knowledge_bytes`；
   - `expected/snapshot_r2.json`：由**增量引擎实跑**产出——
     `orchestrate.assemble(r1 金标, [ed99 视图], [], incremental=True, base_snapshot_revision_id=r1 修订号)`
     的 `knowledge_bytes`（基底号用 `expected/snapshot_revisions.yaml` 的固定常量，
     故逐字节可复现；Ledger 路径上基底号每轮不同，那里只比「除 `meta` 外相同」）。
   - `--check`：重新生成到临时目录并与盘上金标逐字节比对，不改盘上文件。
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

import tempfile  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[5]
if not (REPO_ROOT / "openspec").is_dir():  # pragma: no cover - 防呆
    raise SystemExit("无法定位仓库根目录（自 %s 上溯 5 层）" % Path(__file__).resolve())

FIXTURE_DIR = Path(__file__).resolve().parents[1]
MINI_ED01_SPANS = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01" / "spans.yaml"

# mini_ed01 金标 sha256（impl-07 README §1.2 冻结值）；锚定失败即停手
MINI_ED01_SPANS_SHA256 = "ec6d77b90aa1408d040465babc28a81f59aadf6d6edd9ba8db66ff8ead0b44ef"

sys.path.insert(0, str(REPO_ROOT))
from typing import Any  # noqa: E402

from pipeline.assembly import incremental, orchestrate  # noqa: E402
from pipeline.assembly.canonical import canonical_json, sha256_hex  # noqa: E402
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

# 同书返工版次（ed01r2）：与 ed01 **同一 source_id、同一 edition_part** → D-14 替换；
# 只换包身份（第二份 m6 包），故 ledger_constants 全部新发。
ED01R2 = {
    "edition_key": "ed01r2",
    "source_id": ED01["source_id"],
    "edition_part_artifact_id": ED01["edition_part_artifact_id"],
    "role": "first_edition_rework",
    "validation_package_suffix": "b03",
    "ledger_constants": {
        "processing_run_id": const("prun_", "03"),
        "m4_step_run_id": const("srun_", "07"),
        "m6_step_run_id": const("srun_", "08"),
        "candidate_set_artifact_id": const("art_", "20"),
        "candidate_set_revision_id": const("rev_", "21"),
        "candidate_package_artifact_id": const("art_", "22"),
        "candidate_package_revision_id": const("rev_", "22"),
        "reviewed_edition_artifact_id": const("art_", "23"),
        "reviewed_edition_revision_id": const("rev_", "23"),
        "reviewed_edition_package_artifact_id": const("art_", "24"),
        "reviewed_edition_package_revision_id": const("rev_", "24"),
        "m6_stage_package_id": const("pkg_m6_", "e2"),
        "m6_package_revision_id": const("rev_", "e2"),
    },
}

CORPUS_SPANS_REVISION_ID = const("rev_", "a01")
SNAPSHOT_ARTIFACT_ID = const("art_", "f1")
SNAPSHOT_REVISION_R1 = const("rev_", "f1")
SNAPSHOT_REVISION_R2 = const("rev_", "f2")
SNAPSHOT_REVISION_R3 = const("rev_", "f3")
#: 决定集引用的提案集修订（可读常量；apply 只要求是合法 rev_ 形态）
PROPOSAL_SET_REVISION = const("rev_", "31")
#: 带人工决定的版次 → 决定集文件（ed99 出现在 r2；ed01r2 出现在 r3）
DECISION_FILES = {
    ED99["edition_key"]: "ed99/decisions.json",
    ED01R2["edition_key"]: "ed01r2/decisions.json",
}

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
# 格局（pattern）号（ed01 保持一号不动，两个同名号只在 r2 才出现）：
#  900001 —— ed01 的格局（r1 只有这一号）；
#  900002 —— ed99 的**同题重发号**（R03b 人工裁定 admit_new）→ 同名歧义在 r2 成立；
#  900003 —— ed99 另见之新题格局（R02 自动 admit_new）：留在号段顶部，使返工轮退役的
#            不是命名空间最大号（model 冻结口径：id_allocation 不低于 max(活 ∪ 退役 ∪ 补发)）；
#  900004 —— 返工版次的同题新号（M4 重发）：返工轮 R03d 的触发者。
PAT_ED01_B = "pat_qizheng_900002"
PAT_ED99_NEW = "pat_qizheng_900003"
PAT_REWORK = "pat_qizheng_900004"
PAT_NAME = "三辰通載貴格"
PAT_NEW_NAME = "貴格別録"
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


def candidate_pattern_variant(
    name, assertion_ids, interpretation, *, pattern_id=None, candidate_key=None, aliases=()
):
    """格局候选的变体（默认 `candidate_pattern` 一律带 `PAT` 号）。

    - `pattern_id=None` + `candidate_key`：M4 未发号的候选；
    - `pattern_id=<别的正式号>`：同一版次重发号（R02 自动入账）；
    - `aliases`：格局别名键（与正式对象的 `aliases` 同一语义；B 波的名称命中按
      `name`/`surface`/`aliases` 全体取键，见 `incremental._name_keys`）。
    """
    item = candidate_pattern(name, assertion_ids, interpretation)
    item["pattern_id"] = pattern_id
    if candidate_key:
        item["candidate_key"] = candidate_key
    if aliases:
        item["aliases"] = list(aliases)
    return item


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
    pattern = candidate_pattern(PAT_NAME, [A1, A3], "卷首目錄所見貴格，機器抽取未經人工複核")
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


#: 各轮的人工裁定口径（按 rule_id 写死，出现表外规则即停手上报）
DECISION_CHOICES = {
    2: {
        "R03b": "admit_new",        # 同名重发号：裁定另立一号（r2 才有两个同名 Pattern）
    },
    3: {
        "R03d": "merge_entities",   # 名称命中≥ 2 → 人工合并（CHARTER §21 ④；较小号存活）
        "R04": "accept_alias",      # 同概念的新 surface → 接受为别名
        "R06": "unify",             # 视图声明的组就是某基底组的来源组 → 落到基底组号
    },
}


def scenario_ed01r2(spans: dict) -> dict:
    """同书返工版次（ACT 28 四）：删一条断言、归并两个格局、其余不变。

    与 ed01 **同 `(source_id, edition_part_ids)`** → D-14 替换；内容改动：

    - **删** `A2`（作者行）：其 `collation_key`（`sanche-0002`）同时不再声明 present，
      否则 D-14 会把 R11 也当作「仍在视图里」剔除（CHARTER §21 ⑤）→ 应 `retired`；
    - 格局改为**无正式号的新候选** `cX`，名称为「三辰通載貴格」、别名取 ed99 新格局之题
      → 名称命中两个基底格局（`pat_qizheng_900001` / `…900002`）→ R03d（人工）；
    - `A1` / `A3` 原样（保号携带）、证据链与对勘单元照旧，`SV_1` 与 `三辰` 概念提及照旧
      → 应 `carried`（R11 被 D-14 剔除）；
    - 概念侧新增一条**未绑号**的 `通載` 候选（与 ed01 同）→ R04 别名（人工）。
    """
    a1 = candidate_assertion(A1, spans[SPAN_SURNAME]["text"], CK_TRANSCRIPT, spans[SPAN_SURNAME], 0, [SCH_CLASSIC])
    a3 = candidate_assertion(A3, spans[SPAN_PATTERN]["text"], CK_PATTERN, spans[SPAN_PATTERN], 2, [])
    pattern = candidate_pattern_variant(
        PAT_NAME,
        [A1, A3],
        "返工重审：本版次重发之同题格局（名称命中基底两处 → R03d 待裁）",
        pattern_id=PAT_REWORK,
    )
    sv = candidate_school_view(SV_1, SCH_CLASSIC, A1, ED01R2["source_id"], SPAN_SURNAME)
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
            {"collation_key": CK_PATTERN, "present": True},
            # `sanche-0002`（A2）本次**不再声明**：删断言时同时删该单元的声明
        ],
        "assertions": [a1, a3],
        "patterns": [pattern],
        "school_views": [sv],
        "concept_mentions": [concept],
        "new_concept_candidates": [unbound],
        "approved": [
            (A1, "assertion"), (A3, "assertion"),
            (PAT_REWORK, "pattern"), (CO, "concept"), (SV_1, "school_view"),
        ],
        "evidence_link_targets": [(A1, spans[SPAN_SURNAME]), (A3, spans[SPAN_PATTERN])],
        "decision_suffix": "f",
    }


def scenario_ed99(spans: dict) -> dict:
    # A1 以基底已正式的 as_ 号携带（D-04 A：M4 全局唯一发号，M7 只做碰撞检测），
    # 命题与对齐单元与 ed01 逐字相同 → 并入（attach，保号）并新增一条证据。
    a1 = candidate_assertion(A1, spans[SPAN_SURNAME]["text"], CK_TRANSCRIPT, spans[SPAN_TITLE], 0, [])
    a_new = candidate_assertion(A_NEW, spans[SPAN_TITLE]["text"], CK_TITLE_INDEX, spans[SPAN_TITLE], 1, [SCH_TIANGONG])
    pattern = candidate_pattern("三辰通載貴格", [A1, A_NEW], "第二版次同格局，另添目錄主張")
    # 版次二**同题另一号**（M4 重发号，名字与基底 r1 的格局逐字相同）→ R03b（人工）：
    # 裁定 `admit_new` 后 r2 就出现两个同名 Pattern（返工轮的 R03d 前提）。
    pattern_same_name = candidate_pattern_variant(
        PAT_NAME, [A_NEW], "第二版次同题重发号，待人工裁定是否并入", pattern_id=PAT_ED01_B
    )
    # 版次二另见一条**新题**的格局（名字不命中基底任何格局）→ R02 自动 admit_new（无需人工决定）。
    # 它使 r2 的格局号段不为单点：返工轮「小号存活、大号退役」时，退役号不是命名空间最大号
    # （model 冻结口径：id_allocation 不得低于 max(活 ∪ 退役 ∪ 补发)）。
    pattern_new = candidate_pattern_variant(
        PAT_NEW_NAME, [A_NEW], "第二版次另立之格局", pattern_id=PAT_ED99_NEW
    )
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
            # 声明了一个**位置但无 collation_key** 的单元：真书 26 条断言全部无键
            # （CHARTER §8.2），它必须如实进 `collation.not_comparable`、且上面不得
            # 出现任何对勘关系。声明名 `sanche-unkeyed` 只作可读标注，不进任何配对。
            {"collation_key": None, "present": True, "note": "unkeyed_position"},
        ],
        "assertions": [a1, a_new],
        "patterns": [pattern, pattern_same_name, pattern_new],
        "school_views": [sv],
        "concept_mentions": [concept],
        "new_concept_candidates": [],
        "approved": [
            (A1, "assertion"), (A_NEW, "assertion"),
            (PAT, "pattern"), (PAT_ED01_B, "pattern"), (PAT_ED99_NEW, "pattern"),
            (CO, "concept"), (SV_2, "school_view"),
        ],
        "evidence_link_targets": [(A1, spans[SPAN_TITLE]), (A_NEW, spans[SPAN_TITLE])],
        "decision_suffix": "e",
    }


def canonical_json_bytes(doc: Any) -> bytes:
    """规范 JSON 字节（与 `apply` / `verify.sh` 同一口径：sort_keys + 紧凑分隔符 + 末尾换行）。"""
    return canonical_json(doc)


def decisions_doc(edition: dict, round_no: int, rows: list, *, replaces: str = None) -> dict:
    """决定集落盘为**夹具数据**（全栈用例直接读它，不再手写决定）。"""
    doc = {
        "schema_version": "0.1.0-draft",
        "synthetic": True,
        "round": round_no,
        "edition_key": edition["edition_key"],
        "source_id": edition["source_id"],
        "proposal_set_revision_id": PROPOSAL_SET_REVISION,
        "seen_revision_id": edition["ledger_constants"]["reviewed_edition_revision_id"],
        "note": (
            "决定由本轮真实提案按 build_fixture.py 的 DECISION_CHOICES 表推出，不是手写期望。"
        ),
        "decisions": list(rows),
    }
    if replaces:
        doc["replaces_edition_key"] = replaces
    return doc


def round_decisions(base_knowledge: dict, view: dict, round_no: int, choices: dict) -> list:
    """本轮决定集（fixture 数据）。

    决定**不由人编写**：先让 B 波按真实规则生成本轮提案，再把其中的待决提案按
    `choices` 逐条给出选择。出现表外规则即停手（抛 ``SystemExit``）——夹具不得静默
    吞掉任何未预期的人工提案。
    """
    edition = ED99 if round_no == 2 else ED01R2
    proposals = incremental.propose_incremental(base_knowledge, [view], round_no=round_no)["proposals"]
    decisions = []
    for proposal in proposals:
        if proposal["resolution"] != "human":
            continue
        rule_id = proposal["rule_id"]
        if rule_id not in choices:
            raise SystemExit(
                "FAIL 第 %d 轮出现未预期的待决提案（%s / %s）：夹具决定集无此口径"
                % (round_no, rule_id, proposal["proposal_key"])
            )
        choice = choices[rule_id]
        if rule_id in ("R03d", "R03b"):
            # 并入 / 合并的候选目标就是选择项里的 attach 目标（合并时按号升序传给 apply，
            # apply 侧的「小号存活」不依赖决定的顺序，见 CHARTER §21 ④）
            targets = sorted(
                option.split(":", 1)[1]
                for option in proposal["options"]
                if option.startswith("attach:")
            )
        else:
            targets = list(proposal.get("targets") or [])
        decisions.append(
            {
                "proposal_set_revision_id": PROPOSAL_SET_REVISION,
                "proposal_key": proposal["proposal_key"],
                "choice": choice,
                "target_entity_ids": targets,
                "seen_revision_id": edition["ledger_constants"]["reviewed_edition_revision_id"],
                "decision_type": proposal.get("decision_type"),
            }
        )
    return decisions


def rework_block() -> dict:
    """manifest 的返工段。

    `ed01r2` 与 `ed01` **同 `source_id`**，而 `editions[]` 要求 source 唯一（别一张表），
    故返工版次单列在 `rework` 下：它只在第三轮（r3）作为替换视图使用。
    """
    block = {key: value for key, value in ED01R2.items()}
    block["views_dir"] = ED01R2["edition_key"]
    block["view_files"] = [
        "candidate_set.json", "reviewed_edition.json", "reviewed_edition_package.json",
        "decisions.json",
    ]
    block["decisions_file"] = "%s/decisions.json" % ED01R2["edition_key"]
    block["replaces_edition_key"] = ED01["edition_key"]
    return block


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
    parser.add_argument(
        "--check",
        action="store_true",
        help="重跑生成到临时目录并与盘上金标逐字节比对（不写盘上任何文件）",
    )
    args = parser.parse_args(argv)
    check_root = None
    if args.check:
        check_root = Path(tempfile.mkdtemp(prefix="mini_release01_check_"))
        out = check_root
    else:
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
    payload_ed01r2 = scenario_ed01r2(spans)

    ed01_cset = build_candidate_set(ED01, spans, payload_ed01)
    ed01_reviewed = build_reviewed_edition(ED01, payload_ed01)
    ed01_package = build_reviewed_edition_package(ED01, payload_ed01)
    ed99_cset = build_candidate_set(ED99, spans, payload_ed99)
    ed99_reviewed = build_reviewed_edition(ED99, payload_ed99)
    ed99_package = build_reviewed_edition_package(ED99, payload_ed99)
    ed01r2_cset = build_candidate_set(ED01R2, spans, payload_ed01r2)
    ed01r2_reviewed = build_reviewed_edition(ED01R2, payload_ed01r2)
    ed01r2_package = build_reviewed_edition_package(ED01R2, payload_ed01r2)

    # ---- r1：由已验收创世引擎现算（不得手写）
    proposals = propose_genesis(ed01_cset, ed01_reviewed)
    asm = assemble_genesis(ed01_cset, ed01_reviewed, proposals["proposals"], id_range=ID_RANGE_CONFIG)
    gate = evaluate_genesis(candidate_set=ed01_cset, reviewed_edition=ed01_reviewed, knowledge=asm["knowledge"])
    if not gate["passed"]:
        failed = {k: v["detail"] for k, v in gate["checks"].items() if not v["passed"]}
        print("FAIL 创世引擎拒绝 fixture ed01 视图，Gate 未通过: %s" % failed)
        return 1
    r1_bytes = asm["knowledge_bytes"]

    # ---- r2：r1 → ed99 增量**实跑**（金标一律由实跑产出；CHARTER §19.3 的固定基底号口径）
    ed99_view = {
        "source_id": ED99["source_id"],
        "candidate_set": ed99_cset,
        "reviewed_edition": ed99_reviewed,
    }
    r2_decisions = round_decisions(asm["knowledge"], ed99_view, 2, DECISION_CHOICES[2])
    r2_run = orchestrate.assemble(
        asm["knowledge"],
        [ed99_view],
        r2_decisions,
        incremental=True,
        base_snapshot_revision_id=SNAPSHOT_REVISION_R1,
    )
    if r2_run["status"] != "complete":
        print(
            "FAIL 增量实跑未完成合并: status=%s pending=%r"
            % (r2_run["status"], r2_run.get("pending"))
        )
        return 1
    r2_knowledge = r2_run["result"]["knowledge"]
    r2_bytes = r2_run["result"]["knowledge_bytes"]
    if r2_knowledge.get("meta", {}).get("base_snapshot_revision_id") != SNAPSHOT_REVISION_R1:
        print("FAIL 增量实跑的 meta.base_snapshot_revision_id 不是固定的 r1 修订号")
        return 1

    # ---- r3：r2 → ed01r2（同书返工）增量**实跑**（ACT 28 四）
    rework_view = {
        "source_id": ED01R2["source_id"],
        "candidate_set": ed01r2_cset,
        "reviewed_edition": ed01r2_reviewed,
    }
    rework_decision_rows = round_decisions(r2_knowledge, rework_view, 3, DECISION_CHOICES[3])
    r3_run = orchestrate.assemble(
        r2_knowledge,
        [rework_view],
        rework_decision_rows,
        incremental=True,
        base_snapshot_revision_id=SNAPSHOT_REVISION_R2,
    )
    if r3_run["status"] != "complete":
        print(
            "FAIL 返工轮实跑未完成合并: status=%s pending=%r"
            % (r3_run["status"], r3_run.get("pending"))
        )
        return 1
    r3_knowledge = r3_run["result"]["knowledge"]
    r3_bytes = r3_run["result"]["knowledge_bytes"]
    r3_delta = r3_run["result"]["identity_delta"]
    if r3_knowledge.get("meta", {}).get("base_snapshot_revision_id") != SNAPSHOT_REVISION_R2:
        print("FAIL 返工轮实跑的 meta.base_snapshot_revision_id 不是固定的 r2 修订号")
        return 1
    if r3_knowledge.get("meta", {}).get("assembly_seq") != 3:
        print("FAIL 返工轮实跑的 meta.assembly_seq 不是 3")
        return 1
    # 三类身份变化必须都在（删断言 → retired / 合并 → merged / 其余不动）
    changes = sorted(entry["change_type"] for entry in r3_delta["entries"])
    if changes != ["merged", "retired"]:
        print("FAIL 返工轮身份变化不符预期（期望 merged+retired，实得 %r）" % (changes,))
        return 1
    live_patterns = [item["pattern_id"] for item in r3_knowledge["patterns"]]
    if live_patterns != sorted([PAT, PAT_ED99_NEW, PAT_REWORK]):
        print("FAIL 返工轮后存活的格局不是预期的三号: %r" % (live_patterns,))
        return 1
    if PAT_ED01_B in live_patterns:
        print("FAIL 被合并退役的格局仍在总账: %s" % PAT_ED01_B)
        return 1

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
            {
                # 同书返工（ed01r2）：同一 source_id，第三次汇编；基底是 r2。
                # `identity_delta_file` 是同一轮的身份变化金标（逐字节比对）。
                "assembly_seq": 3,
                "snapshot_revision_id": SNAPSHOT_REVISION_R3,
                "base_snapshot_revision_id": SNAPSHOT_REVISION_R2,
                "prev_revision_id": SNAPSHOT_REVISION_R2,
                "supersedes_revision_id": SNAPSHOT_REVISION_R2,
                "knowledge_file": "expected/snapshot_r3.json",
                "knowledge_sha256": hashlib.sha256(r3_bytes).hexdigest(),
                "identity_delta_file": "expected/identity_delta_r3.json",
                "identity_delta_sha256": hashlib.sha256(
                    canonical_json_bytes(r3_delta)
                ).hexdigest(),
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
    generated["ed99/decisions.json"] = json.dumps(
        decisions_doc(ED99, 2, r2_decisions), ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n"
    generated["ed01r2/candidate_set.json"] = json.dumps(ed01r2_cset, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    generated["ed01r2/reviewed_edition.json"] = json.dumps(ed01r2_reviewed, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    generated["ed01r2/reviewed_edition_package.json"] = json.dumps(ed01r2_package, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    generated["ed01r2/decisions.json"] = json.dumps(
        decisions_doc(ED01R2, 3, rework_decision_rows, replaces=ED01["edition_key"]),
        ensure_ascii=False, sort_keys=True, indent=2,
    ) + "\n"
    generated["expected/snapshot_r1.json"] = r1_bytes.decode("utf-8")
    generated["expected/snapshot_r2.json"] = r2_bytes.decode("utf-8")
    generated["expected/snapshot_r3.json"] = r3_bytes.decode("utf-8")
    generated["expected/identity_delta_r3.json"] = canonical_json_bytes(r3_delta).decode("utf-8")
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
                else "rework_decisions" if name.endswith("decisions.json")
                else "expected_snapshot" if name.startswith("expected/snapshot_r")
                else "expected_identity_delta" if name.startswith("expected/identity_delta")
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
        if edition["edition_key"] in DECISION_FILES:
            # 该版次带人工决定集（fixture 数据；全栈用例直接读它，不手写提案/决定）
            block["view_files"] = block["view_files"] + ["decisions.json"]
            block["decisions_file"] = DECISION_FILES[edition["edition_key"]]
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
        "decisions": [
            {
                "round": 2,
                "edition_key": ED99["edition_key"],
                "source_id": ED99["source_id"],
                "file": DECISION_FILES[ED99["edition_key"]],
            },
            {
                "round": 3,
                "edition_key": ED01R2["edition_key"],
                "source_id": ED01R2["source_id"],
                "replaces_edition_key": ED01["edition_key"],
                "file": DECISION_FILES[ED01R2["edition_key"]],
            },
        ],
        "rework": rework_block(),
        "expected": {
            "snapshot_revisions": "expected/snapshot_revisions.yaml",
            "round1": "expected/snapshot_r1.json",
            "round2": "expected/snapshot_r2.json",
            "round3": "expected/snapshot_r3.json",
            "identity_delta_r3": "expected/identity_delta_r3.json",
        },
        "files": files,
    }
    write_text(out / "manifest.yaml", yaml.safe_dump(manifest, allow_unicode=True, sort_keys=True, default_flow_style=False))

    # 常量自检（防呆：任何非法标识都在生成时暴露）
    for edition in (ED01, ED99, ED01R2):
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
    ids.validate("artifact_revision_id", SNAPSHOT_REVISION_R3)
    for pattern_id in (PAT, PAT_ED01_B, PAT_ED99_NEW, PAT_REWORK):
        ids.validate("pattern_id", pattern_id)
    ids.validate("artifact_revision_id", CORPUS_SPANS_REVISION_ID)

    print("BUILD OK %s" % out)
    for item in files:
        print("  %s  %s" % (item["sha256"], item["path"]))
    print("  r1 knowledge_sha256=%s" % revisions_plan["revisions"][0]["knowledge_sha256"])
    print("  r2 knowledge_sha256=%s" % revisions_plan["revisions"][1]["knowledge_sha256"])
    if check_root is not None:
        return _compare_with_fixture(check_root)
    return 0


def _compare_with_fixture(tmp: Path) -> int:
    """把重跑产物与盘上金标逐字节比对（`--check`；只读盘上文件，不写任何文件）。"""
    regenerated = sorted(
        path.relative_to(tmp).as_posix() for path in tmp.rglob("*") if path.is_file()
    )
    bad = []
    for name in regenerated:
        on_disk = FIXTURE_DIR / name
        if not on_disk.is_file():
            bad.append("%s 盘上缺失" % name)
        elif on_disk.read_bytes() != (tmp / name).read_bytes():
            bad.append("%s 与盘上金标逐字节不同" % name)
    print("CHECK files=%d mismatched=%d" % (len(regenerated), len(bad)))
    for item in bad[:5]:
        print("  FAIL %s" % item)
    if bad:
        print("CHECK FAILED: 重跑生成与盘上金标不一致（先跑不带 --check 的生成）")
        return 1
    print("CHECK OK: 重跑生成与盘上金标逐字节一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

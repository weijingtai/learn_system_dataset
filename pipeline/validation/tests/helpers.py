"""M5 纯函数测试脚手架：从 mini_ed01 fixture 合成 ``fixture_context()``。

``fixture_context()`` 不访问 Ledger，只读 fixture 文件，产出与
``context.build_context`` 同形的上下文，供 K1 纯函数 Validator 测试使用。
上下文全部为普通 dict / list，测试对副本施加篡改，绝不写回 fixture 目录。

另含 **offset 档合成脚手架**（R83）：
``offset_fixture_context()`` 为纯函数上下文，``text_chain()`` 在临时 Ledger 上
走真实写路径 ``run_m1 → run_m2 → run_m3_text``，供电子文本端到端用例使用。
两者都不使用仓库内的真书宿主。

上下文键（与 ``pipeline.validation.context.build_context`` 对齐）：
    manifest, ocr_page_set, page_docs, terminal_states, human_events,
    spans_doc, corpus_package, coverage_report, m3_package, configuration,
    evidence_level, raw_text, cleaned_text, patches, sanitization_report,
    batch_assignments, raw_text_revision_id, cleaned_text_revision_id,
    patch_set_revision_id, sanitization_report_revision_id,
    page_revision_ids, batch_revision_ids, corpus_spans_revision_id,
    corpus_package_revision_id, m3_package_revision_id, revision_roles,
    frozen_revision_ids, technique_id, target_consumption_level, raw
``raw["frozen"]`` 为 ``{修订: {sha256, actual_sha256, doc, status, artifact_type,
artifact_id}}``，其中 ``status``/``artifact_type``/``artifact_id`` 供
引用闭合校验使用（同 impl-02 经只读 SELECT 取得的元数据）。
"""

import hashlib
import json
from pathlib import Path

import yaml

from pipeline.corpus_compiler import M3_TOOL, M3_TOOL_VERSION

# 页名（manifest 页序）
_PAGES = ("page_001", "page_002", "page_003")
# 5 个批次
_BATCHES = ("sanche_b001", "sanche_b002", "sanche_b003", "sanche_b004", "sanche_b005")

# ---- offset 档合成数据（R83）：不读仓库内真书宿主 ----
OFFSET_EDITION_PART = "art_00000000000000000000000000000001"
OFFSET_PAGE = "qianyuan_ed01_text"
OFFSET_WORK = "qianyuan"
OFFSET_EDITION = "ed01"
OFFSET_RAW_TEXT = "乾元秘旨\n甲？乙\n丙\n"
OFFSET_CLEANED_TEXT = "乾元秘旨\n甲乙\n丙\n"
# 确定性补丁：删掉 raw[6:7] 的「？」，故 cleaned 侧长度零区间 [6, 6)
OFFSET_PATCHES = [
    {
        "patch_id": "p0001",
        "raw_start": 6,
        "raw_end": 7,
        "cleaned_start": 6,
        "cleaned_end": 6,
        "action": "delete",
        "basis": "CTP",
        "replacement": "",
    }
]

# ---- offset 档含「已知不可解决」私用区码位的合成数据（第 103 条 D1）----
# raw 经 OFFSET_PUA_PATCHES 删去 raw[5:6] 的 "X" 后得 cleaned；PUA 码位
# U+E03D 有意保留（第 79 条 D4），其原始偏移为 6、清洗偏移为 5。
OFFSET_PUA_RAW_TEXT = "乾元秘旨\nX\uE03D甲乙\n丙\n"
OFFSET_PUA_CLEANED_TEXT = "乾元秘旨\n\uE03D甲乙\n丙\n"
OFFSET_PUA_PATCHES = [
    {
        "patch_id": "p0001",
        "raw_start": 5,
        "raw_end": 6,
        "cleaned_start": 5,
        "cleaned_end": 5,
        "action": "delete",
        "basis": "CTP",
        "replacement": "",
    }
]
# M2 清洗报告中对上述码位的唯一登记（raw[6:7] == U+E03D）
OFFSET_PUA_FINDING = {
    "finding_id": "private_use_area@6-7",
    "kind": "private_use_area",
    "raw_start": 6,
    "raw_end": 7,
    "raw_excerpt": "\uE03D",
    "context": "甲\uE03D乙",
    "action": "kept",
    "patch_id": None,
    "basis": "保留 PUA 原码位，待字形层查证（§79 D4）",
    "terminal_state": "known_unresolvable",
}


def default_fixture_dir():
    """返回仓库内 mini_ed01 fixture 的绝对路径。"""
    return (
        Path(__file__).resolve().parents[3]
        / "pipeline"
        / "corpus"
        / "_fixture"
        / "mini_ed01"
    )


def _hex32(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rev(tag):
    return "rev_" + _hex32("mini_ed01:rev:" + tag)


def _art(tag):
    return "art_" + _hex32("mini_ed01:art:" + tag)


def _ref(rev, artifact_type, tag):
    return {
        "schema_version": "1.0.0",
        "artifact_kind": "artifact",
        "artifact_id": _art(tag),
        "artifact_revision_id": rev,
        "artifact_type": artifact_type,
    }


def _json_bytes(doc):
    return json.dumps(doc, sort_keys=True, ensure_ascii=False).encode("utf-8")


def fixture_context(fixture_dir=None):
    """从 mini_ed01 构造纯函数测试上下文。"""
    root = Path(fixture_dir) if fixture_dir is not None else default_fixture_dir()

    manifest = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))
    spans_bytes = (root / "spans.yaml").read_bytes()
    spans_doc = yaml.safe_load(spans_bytes.decode("utf-8"))
    anomalies = yaml.safe_load((root / "anomalies.yaml").read_text(encoding="utf-8"))

    page_docs = {}
    page_bytes = {}
    for page in _PAGES:
        data = (root / "pages" / ("%s.json" % page)).read_bytes()
        page_bytes[page] = data
        page_docs[page] = json.loads(data.decode("utf-8"))

    terminal_states = {}
    human_events = []
    for entry in anomalies.get("entries", []):
        terminal_states[entry["page"]] = entry["terminal_state"]
        human_events.append(
            {"page": entry["page"], "terminal_state": entry["terminal_state"]}
        )

    # ---- 冻结修订角色（顺序固定，共 17 个） ----
    revs = {
        "m3_package": _rev("m3_package"),
        "corpus_package": _rev("corpus_package"),
        "corpus_spans": _rev("corpus_spans"),
        "coverage_report": _rev("coverage_report"),
        "validation_report": _rev("validation_report"),
        "configuration": _rev("configuration"),
        "source_manifest": _rev("source_manifest"),
        "ocr_page_set": _rev("ocr_page_set"),
        "human_event": _rev("human_event"),
    }
    for batch in _BATCHES:
        revs[batch] = _rev(batch)
    for page in _PAGES:
        revs[page] = _rev(page)

    coverage = {"page_001": 1.0, "page_003": 1.0}
    excluded_pages = {"page_002": "known_unrecognizable"}
    corpus_package = {
        "spans_revision_id": revs["corpus_spans"],
        "coverage_report_revision_id": revs["coverage_report"],
        "coverage": coverage,
        "excluded_pages": excluded_pages,
        "gate_profile": "structural_only",
        "semantic": "not_evaluated",
    }
    ocr_page_set = {
        "ocr_pages": [
            {"page": page, "sha256": hashlib.sha256(page_bytes[page]).hexdigest()}
            for page in _PAGES
        ],
        "terminal_states": dict(terminal_states),
    }
    configuration = {
        "stage": "m3",
        "tool": M3_TOOL,
        "tool_version": M3_TOOL_VERSION,
        "batch_size": 10,
        "gate_profile": "structural_only",
    }
    coverage_report = {
        "gate_profile": "structural_only",
        "structural": "passed",
        "semantic": "not_evaluated",
        "coverage": coverage,
        "excluded_pages": excluded_pages,
    }
    validation_report = {
        "gate_profile": "structural_only",
        "structural": "passed",
        "semantic": "not_evaluated",
        "failed_checks": [],
    }

    m3_package = {
        "schema_version": "1.0.0",
        "stage_package_id": "pkg_m3_" + _hex32("mini_ed01:pkg"),
        "artifact_revision_id": revs["m3_package"],
        "stage": "m3",
        "status": "sealed",
        "payload": {
            "spans_revision_id": revs["corpus_spans"],
            "coverage": coverage,
            "excluded_pages": excluded_pages,
            "gate_profile": "structural_only",
            "semantic": "not_evaluated",
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": "prun_" + _hex32("mini_ed01:prun"),
            "step_run_id": "srun_" + _hex32("mini_ed01:srun:m3"),
            "input_artifacts": [
                _ref(revs["source_manifest"], "source_manifest", "source_manifest"),
                _ref(revs["ocr_page_set"], "ocr_page_set", "ocr_page_set"),
            ]
            + [_ref(revs[page], "ocr_page", page) for page in _PAGES]
            + [_ref(revs["human_event"], "human_event", "human_event")],
            "output_artifacts": [
                _ref(revs["corpus_package"], "corpus_package", "corpus_package")
            ],
            "counts": {"spans": 43, "batches": 5},
            "content_sha256": hashlib.sha256(spans_bytes).hexdigest(),
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [
                _ref(revs["ocr_page_set"], "ocr_page_set", "ocr_page_set"),
                _ref(revs["source_manifest"], "source_manifest", "source_manifest"),
            ],
            "transformations": [],
        },
        "logs": [],
        "failures": [],
    }

    # ---- raw.frozen：全部 17 个冻结修订 ----
    spans = spans_doc.get("spans", [])
    docs = {
        "m3_package": m3_package,
        "corpus_package": corpus_package,
        "corpus_spans": spans_doc,
        "coverage_report": coverage_report,
        "validation_report": validation_report,
        "configuration": configuration,
        "source_manifest": manifest,
        "ocr_page_set": ocr_page_set,
        "human_event": human_events[0] if human_events else {},
    }
    for page in _PAGES:
        docs[page] = page_docs[page]
    for batch in _BATCHES:
        docs[batch] = [span for span in spans if span.get("batch_id") == batch]

    # 登记 sha256：页修订与 spans 修订必须等于其真实文件字节哈希
    # （G1 页登记与内容哈希按文件字节比对），其余按规范 JSON 复算。
    file_sha = {"corpus_spans": hashlib.sha256(spans_bytes).hexdigest()}
    for page in _PAGES:
        file_sha[page] = hashlib.sha256(page_bytes[page]).hexdigest()

    role_type = {
        "m3_package": "stage_package",
        "corpus_package": "corpus_package",
        "corpus_spans": "corpus_spans",
        "coverage_report": "coverage_report",
        "validation_report": "validation_report",
        "configuration": "configuration",
        "source_manifest": "source_manifest",
        "ocr_page_set": "ocr_page_set",
        "human_event": "human_event",
    }
    for page in _PAGES:
        role_type[page] = "ocr_page"
    for batch in _BATCHES:
        role_type[batch] = "corpus_batch"

    raw_frozen = {}
    for role, rev in revs.items():
        doc = docs.get(role)
        sha = file_sha.get(role) or hashlib.sha256(_json_bytes(doc)).hexdigest()
        raw_frozen[rev] = {
            "sha256": sha,
            "actual_sha256": sha,
            "doc": doc,
            "status": "sealed",
            "artifact_type": role_type[role],
            "artifact_id": _art(role),
        }

    frozen_order = [
        revs["m3_package"],
        revs["corpus_package"],
        revs["corpus_spans"],
        revs["coverage_report"],
        revs["validation_report"],
        revs["configuration"],
    ] + [revs[batch] for batch in _BATCHES] + [
        revs["source_manifest"],
        revs["ocr_page_set"],
    ] + [revs[page] for page in _PAGES] + [revs["human_event"]]

    return {
        "manifest": manifest,
        "ocr_page_set": ocr_page_set,
        "page_docs": page_docs,
        "terminal_states": terminal_states,
        "human_events": human_events,
        "spans_doc": spans_doc,
        "corpus_package": corpus_package,
        "coverage_report": coverage_report,
        "m3_package": m3_package,
        "configuration": configuration,
        "evidence_level": spans_doc.get("evidence_level"),
        "raw_text": None,
        "cleaned_text": None,
        "patches": [],
        "sanitization_report": {},
        "batch_assignments": {},
        "raw_text_revision_id": None,
        "cleaned_text_revision_id": None,
        "patch_set_revision_id": None,
        "sanitization_report_revision_id": None,
        "technique_id": manifest.get("technique_id"),
        "target_consumption_level": "INTERNAL_DEMO",
        "page_revision_ids": {page: revs[page] for page in _PAGES},
        "batch_revision_ids": [revs[batch] for batch in _BATCHES],
        "corpus_spans_revision_id": revs["corpus_spans"],
        "corpus_package_revision_id": revs["corpus_package"],
        "m3_package_revision_id": revs["m3_package"],
        "frozen_revision_ids": frozen_order,
        "revision_roles": {role: rev for role, rev in revs.items()},
        "raw": {"frozen": raw_frozen},
    }


# ================================================================ offset 档脚手架
_M2_TEXT_ROLES = (
    "raw_text",
    "cleaned_text_revision",
    "deterministic_patch_set",
    "sanitization_report",
)


def _text_span(span_id, sequence, start_offset, end_offset, text, raw_start, raw_end, revs):
    """构造一条电子文本 Span（8 键有序，锚点 7 键有序，第 78 条）。"""
    quote_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "span_id": span_id,
        "sequence": sequence,
        "start_offset": start_offset,
        "end_offset": end_offset,
        "text": text,
        "quote_sha256": quote_sha256,
        "evidence_level": "offset_level",
        "source_anchor": {
            "raw_text_revision_id": revs["raw_text"],
            "raw_start": raw_start,
            "raw_end": raw_end,
            "cleaned_text_revision_id": revs["cleaned_text_revision"],
            "start_offset": start_offset,
            "end_offset": end_offset,
            "quote_sha256": quote_sha256,
        },
    }


def offset_fixture_context():
    """构造电子文本档（``offset_level``）的纯函数上下文（合成数据，不读 Ledger）。

    文本为 ``OFFSET_RAW_TEXT``，经 ``OFFSET_PATCHES`` 删去 raw[6:7] 的「？」后
    得 ``OFFSET_CLEANED_TEXT``，切成 3 条片段（cleaned 偏移 [0,5)/[5,8)/[8,10)，
    对应 raw 偏移 [0,5)/[5,9)/[9,11)）。全部值均为独立手算，不调用 M3。
    """
    revs = _offset_revs()
    return _offset_context(
        revs=revs,
        raw_text=OFFSET_RAW_TEXT,
        cleaned_text=OFFSET_CLEANED_TEXT,
        patches=OFFSET_PATCHES,
        spans=[
            _text_span(
                "ss_%s_%s_o0000000" % (OFFSET_WORK, OFFSET_EDITION),
                1, 0, 5, OFFSET_CLEANED_TEXT[0:5], 0, 5, revs,
            ),
            _text_span(
                "ss_%s_%s_o0000005" % (OFFSET_WORK, OFFSET_EDITION),
                2, 5, 8, OFFSET_CLEANED_TEXT[5:8], 5, 9, revs,
            ),
            _text_span(
                "ss_%s_%s_o0000009" % (OFFSET_WORK, OFFSET_EDITION),
                3, 8, 10, OFFSET_CLEANED_TEXT[8:10], 9, 11, revs,
            ),
        ],
        report_findings=[],
        patch_ids=["p0001"],
    )


def offset_pua_fixture_context():
    """构造含「已知不可解决」私用区码位的电子文本上下文（第 103 条 D1 合成数据）。

    ``OFFSET_PUA_RAW_TEXT`` 经 ``OFFSET_PUA_PATCHES`` 删去 raw[5:6] 的 ``X`` 后
    得 ``OFFSET_PUA_CLEANED_TEXT``（PUA 码位 **有意保留**，与 M2 第 79 条 D4
    一致）。片段 cleaned 偏移 [0,5)/[5,9)/[9,11)，对应 raw 偏移
    [0,5)/[6,10)/[10,12)；清洗报告恰一条 `private_use_area@6-7`
    （``terminal_state: known_unresolvable``）覆盖该码位的原始偏移 6。
    """
    revs = _offset_revs()
    return _offset_context(
        revs=revs,
        raw_text=OFFSET_PUA_RAW_TEXT,
        cleaned_text=OFFSET_PUA_CLEANED_TEXT,
        patches=OFFSET_PUA_PATCHES,
        spans=[
            _text_span(
                "ss_%s_%s_o0000000" % (OFFSET_WORK, OFFSET_EDITION),
                1, 0, 5, OFFSET_PUA_CLEANED_TEXT[0:5], 0, 5, revs,
            ),
            _text_span(
                "ss_%s_%s_o0000006" % (OFFSET_WORK, OFFSET_EDITION),
                2, 5, 9, OFFSET_PUA_CLEANED_TEXT[5:9], 6, 10, revs,
            ),
            _text_span(
                "ss_%s_%s_o0000010" % (OFFSET_WORK, OFFSET_EDITION),
                3, 9, 11, OFFSET_PUA_CLEANED_TEXT[9:11], 10, 12, revs,
            ),
        ],
        report_findings=[dict(OFFSET_PUA_FINDING)],
        patch_ids=["p0001"],
    )


def _offset_revs():
    """offset 档上下文的全部修订号（两套合成夹具共用同一形态）。"""
    revs = {role: _rev("text:" + role) for role in _M2_TEXT_ROLES}
    revs.update(
        {
            "m3_package": _rev("text:m3_package"),
            "corpus_package": _rev("text:corpus_package"),
            "corpus_spans": _rev("text:corpus_spans"),
            "coverage_report": _rev("text:coverage_report"),
            "validation_report": _rev("text:validation_report"),
            "configuration": _rev("text:configuration"),
            "source_manifest": _rev("text:source_manifest"),
            "batch_001": _rev("text:batch_001"),
        }
    )
    return revs


def _offset_context(
    *,
    revs,
    raw_text,
    cleaned_text,
    patches,
    spans,
    report_findings,
    patch_ids,
):
    """由给定文本/补丁/片段/清洗发现装配 offset 档纯函数上下文（内部共用）。"""
    page = OFFSET_PAGE
    spans_doc = {
        "work": OFFSET_WORK,
        "source_id": "src_%s_%s" % (OFFSET_WORK, OFFSET_EDITION),
        "edition_part_artifact_id": OFFSET_EDITION_PART,
        "evidence_level": "offset_level",
        "content_status": "machine_extracted",
        "span_count": len(spans),
        "spans": spans,
    }
    raw_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    manifest = {
        "source_id": "src_%s_%s" % (OFFSET_WORK, OFFSET_EDITION),
        "work_title": "合成电子文本",
        "technique_id": "qizheng",
        "edition_part": {
            "artifact_id": OFFSET_EDITION_PART,
            "label": "合成电子文本（单文件）",
            "pages": [page],
        },
        "source_assets": [
            {
                "page": page,
                "path_ref": "%s.md" % page,
                "sha256": raw_sha256,
                "normalized_sha256": raw_sha256,
                "original_encoding": "utf-8",
                "size": len(raw_text.encode("utf-8")),
                "width": None,
                "height": None,
                "object_store": "local",
                "in_git": False,
            }
        ],
        "content_status": "machine_extracted",
    }
    coverage_value = (
        float(sum(len(span["text"]) for span in spans)) / len(cleaned_text)
        if cleaned_text
        else 0.0
    )
    coverage_report = {
        "gate_profile": "structural_only",
        "structural": "passed",
        "semantic": "not_evaluated",
        "checks": {
            name: {"ok": True, "failures": []}
            for name in (
                "text_contiguous_coverage",
                "text_strict_offset",
                "raw_anchor_fidelity",
                "identity_and_stability",
                "evidence_level_honest",
                "header_counts",
            )
        },
        "pages": {
            page: {
                "status": "covered",
                "terminal_state": None,
                "line_count": len(raw_text.splitlines()),
                "span_count": len(spans),
                "coverage": coverage_value,
                "gaps": [],
                "overlaps": [],
            }
        },
    }
    corpus_package = {
        "spans_revision_id": revs["corpus_spans"],
        "coverage_report_revision_id": revs["coverage_report"],
        "coverage": {page: coverage_value},
        "excluded_pages": {},
        "gate_profile": "structural_only",
        "semantic": "not_evaluated",
    }
    configuration = {
        "stage": "m3",
        "tool": "pipeline.corpus_compiler.step_offset",
        "tool_version": "0.1.0",
        "evidence_level": "offset_level",
        "batch_size": 10,
        "gate_profile": "structural_only",
    }
    validation_report = {
        "gate_profile": "structural_only",
        "structural": "passed",
        "semantic": "not_evaluated",
        "failed_checks": [],
    }
    sanitization_report = {
        "schema_version": "0.1.0-draft",
        "findings": [dict(entry) for entry in report_findings],
        "patches": list(patch_ids),
        "summary": {
            "deferred_count": 0,
            "private_use_area": sum(
                1 for entry in report_findings if entry.get("kind") == "private_use_area"
            ),
        },
    }
    spans_bytes = yaml.dump(
        spans_doc, allow_unicode=True, default_flow_style=False, sort_keys=False
    ).encode("utf-8")
    spans_sha256 = hashlib.sha256(spans_bytes).hexdigest()

    m3_package = {
        "schema_version": "1.0.0",
        "stage_package_id": "pkg_m3_" + _hex32("text:pkg"),
        "artifact_revision_id": revs["m3_package"],
        "stage": "m3",
        "status": "sealed",
        "payload": {
            "spans_revision_id": revs["corpus_spans"],
            "coverage": {page: coverage_value},
            "excluded_pages": {},
            "gate_profile": "structural_only",
            "semantic": "not_evaluated",
        },
        "manifest": {
            "schema_version": "1.0.0",
            "processing_run_id": "prun_" + _hex32("text:prun"),
            "step_run_id": "srun_" + _hex32("text:srun:m3"),
            "input_artifacts": [
                _ref(revs[role], role, "text:" + role) for role in _M2_TEXT_ROLES
            ],
            "output_artifacts": [
                _ref(revs["corpus_package"], "corpus_package", "text:corpus_package")
            ],
            "counts": {"spans": len(spans), "batches": 1},
            "content_sha256": spans_sha256,
        },
        "validation": {"passed": True, "report_artifacts": []},
        "lineage": {
            "upstream_artifacts": [
                _ref(revs[role], role, "text:" + role) for role in _M2_TEXT_ROLES
            ],
            "transformations": [],
        },
        "logs": [],
        "failures": [],
    }

    docs = {
        "m3_package": m3_package,
        "corpus_package": corpus_package,
        "corpus_spans": spans_doc,
        "coverage_report": coverage_report,
        "validation_report": validation_report,
        "configuration": configuration,
        "source_manifest": manifest,
        "raw_text": raw_text,
        "cleaned_text_revision": cleaned_text,
        "deterministic_patch_set": patches,
        "sanitization_report": sanitization_report,
        "batch_001": spans,
    }
    role_type = {
        "m3_package": "stage_package",
        "corpus_package": "corpus_package",
        "corpus_spans": "corpus_spans",
        "coverage_report": "coverage_report",
        "validation_report": "validation_report",
        "configuration": "configuration",
        "source_manifest": "source_manifest",
        "raw_text": "raw_text",
        "cleaned_text_revision": "cleaned_text_revision",
        "deterministic_patch_set": "deterministic_patch_set",
        "sanitization_report": "sanitization_report",
        "batch_001": "corpus_batch",
    }
    file_sha = {"corpus_spans": spans_sha256, "raw_text": raw_sha256}
    raw_frozen = {}
    for role, rev in revs.items():
        doc = docs[role]
        sha = file_sha.get(role) or hashlib.sha256(_json_bytes(doc)).hexdigest()
        raw_frozen[rev] = {
            "sha256": sha,
            "actual_sha256": sha,
            "doc": doc,
            "status": "sealed",
            "artifact_type": role_type[role],
            "artifact_id": _art(role),
        }

    frozen_order = [
        revs["m3_package"],
        revs["corpus_package"],
        revs["corpus_spans"],
        revs["coverage_report"],
        revs["validation_report"],
        revs["configuration"],
        revs["batch_001"],
        revs["source_manifest"],
    ] + [revs[role] for role in _M2_TEXT_ROLES]

    return {
        "manifest": manifest,
        "ocr_page_set": {},
        "page_docs": {},
        "terminal_states": {},
        "human_events": [],
        "spans_doc": spans_doc,
        "corpus_package": corpus_package,
        "coverage_report": coverage_report,
        "m3_package": m3_package,
        "configuration": configuration,
        "evidence_level": "offset_level",
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "patches": list(patches),
        "sanitization_report": sanitization_report,
        "batch_assignments": {"batch_001": [span["span_id"] for span in spans]},
        "raw_text_revision_id": revs["raw_text"],
        "cleaned_text_revision_id": revs["cleaned_text_revision"],
        "patch_set_revision_id": revs["deterministic_patch_set"],
        "sanitization_report_revision_id": revs["sanitization_report"],
        "technique_id": manifest["technique_id"],
        "target_consumption_level": "INTERNAL_DEMO",
        "page_revision_ids": {},
        "batch_revision_ids": [revs["batch_001"]],
        "corpus_spans_revision_id": revs["corpus_spans"],
        "corpus_package_revision_id": revs["corpus_package"],
        "m3_package_revision_id": revs["m3_package"],
        "frozen_revision_ids": frozen_order,
        "revision_roles": {role: rev for role, rev in revs.items()},
        "raw": {"frozen": raw_frozen},
    }


def text_chain(service, source_dir):
    """在真实 Ledger 上走 M1→M2→M3 电子文本写路径，返回各阶段摘要。

    ``source_dir`` 必须已含一个以 ``OFFSET_PAGE`` 为 stem 的文本文件（调用方用
    ``write_offset_source`` 生成）。全程使用合成文本，不读仓库内真书宿主。
    """
    from pipeline.digitization.step import run_m2
    from pipeline.intake.source import read_source_files
    from pipeline.intake.step import run_m1

    from pipeline.corpus_compiler.step_offset import run_m3_text

    source_info = {
        "source_id": "src_%s_%s" % (OFFSET_WORK, OFFSET_EDITION),
        "work_title": "合成电子文本",
        "edition_note": "测试用合成电子文本",
        "technique_id": "qizheng",
        "rights_status": "测试数据",
        "release_policy": "reference_and_hash_only",
        "edition_part": {
            "artifact_id": OFFSET_EDITION_PART,
            "label": "合成电子文本（单文件）",
            "pages": [OFFSET_PAGE],
        },
        "source_site": "example.invalid",
        "source_url": "https://example.invalid/synthetic.md",
        "file_sha256": hashlib.sha256(
            (Path(source_dir) / ("%s.md" % OFFSET_PAGE)).read_bytes()
        ).hexdigest(),
        "pages": [OFFSET_PAGE],
    }
    files = read_source_files(Path(source_dir), [OFFSET_PAGE])
    m1 = run_m1(service, source_info, files, OFFSET_EDITION_PART)
    raw_text_revision_id = m1["raw_text_revision_ids"][0]
    m2 = run_m2(service, raw_text_revision_id, source_info, OFFSET_EDITION_PART)
    m3 = run_m3_text(service, OFFSET_EDITION_PART)
    return {"source_info": source_info, "m1": m1, "m2": m2, "m3": m3}


def write_offset_source(directory):
    """把合成原文写入 ``directory/<page>.md``，返回目录路径。"""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    (target / ("%s.md" % OFFSET_PAGE)).write_text(OFFSET_RAW_TEXT, encoding="utf-8")
    return target

"""M5 纯函数测试脚手架：从 mini_ed01 fixture 合成 ``fixture_context()``。

``fixture_context()`` 不访问 Ledger，只读 fixture 文件，产出与
``context.build_context`` 同形的上下文，供 K1 纯函数 Validator 测试使用。
上下文全部为普通 dict / list，测试对副本施加篡改，绝不写回 fixture 目录。

上下文键（与 ``pipeline.validation.context.build_context`` 对齐）：
    manifest, ocr_page_set, page_docs, terminal_states, human_events,
    spans_doc, corpus_package, m3_package, configuration,
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
        "m3_package": m3_package,
        "configuration": configuration,
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

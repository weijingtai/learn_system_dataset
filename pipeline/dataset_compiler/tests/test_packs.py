"""ACT impl-04/01：纯函数子包编译器的测试。

测试可读 fixture 文件作为纯函数输入（manifest.yaml、pages/*.json、spans.yaml、
anomalies.yaml）；asset_records / ocr_page_revision_ids 由测试按契约从清单派生。
"""

import copy
import hashlib
import json
import os
import re
import struct
import unittest
import unittest.mock

import yaml

from pipeline.dataset_compiler import packs
from pipeline.dataset_compiler.canonical import canonical_bytes, sha256_hex
from pipeline.dataset_compiler.errors import DatasetRefused
from pipeline.ledger.errors import (
    DuplicateIdentifier,
    HashMismatch,
    InvalidIdentifier,
    MissingReference,
    SchemaViolation,
)

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_TESTS_DIR, os.pardir, os.pardir, os.pardir))
_FIXTURE_DIR = os.path.join(_REPO_ROOT, "pipeline", "corpus", "_fixture", "mini_ed01")

EXCLUDED_PAGES = {"page_002": "known_unrecognizable"}


def _load_yaml(name):
    with open(os.path.join(_FIXTURE_DIR, name), encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_json(name):
    with open(os.path.join(_FIXTURE_DIR, name), encoding="utf-8") as handle:
        return json.load(handle)


def _manifest():
    return _load_yaml("manifest.yaml")


def _spans_doc():
    return _load_yaml("spans.yaml")


def _page_docs():
    return {
        page: _load_json("pages/%s.json" % page)
        for page in ("page_001", "page_002", "page_003")
    }


def _asset_records(base=1):
    manifest = _manifest()
    return {
        item["page"]: {
            "artifact_revision_id": "rev_%032x" % (base + index),
            "sha256": item["sha256"],
            "size": 0,
            "width": item["width"],
            "height": item["height"],
        }
        for index, item in enumerate(manifest["source_assets"])
    }


def _ocr_revision_ids(base=101):
    return {
        "page_001": "rev_%032x" % (base + 0),
        "page_002": "rev_%032x" % (base + 1),
        "page_003": "rev_%032x" % (base + 2),
    }


def _source_pack(asset_records=None):
    return packs.build_source_asset_pack(
        manifest=_manifest(),
        asset_records=asset_records if asset_records is not None else _asset_records(),
    )


def _evidence_pack(
    source_pack=None,
    spans_doc=None,
    page_docs=None,
    ocr_revision_ids=None,
    excluded_pages=None,
    snapshot_knowledge=None,
):
    return packs.build_evidence_map_pack(
        spans_doc=spans_doc if spans_doc is not None else _spans_doc(),
        page_docs=page_docs if page_docs is not None else _page_docs(),
        ocr_page_revision_ids=(
            ocr_revision_ids if ocr_revision_ids is not None else _ocr_revision_ids()
        ),
        source_asset_pack=(
            source_pack if source_pack is not None else _source_pack()
        )["pack"],
        excluded_pages=(
            excluded_pages if excluded_pages is not None else EXCLUDED_PAGES
        ),
        snapshot_knowledge=snapshot_knowledge,
    )


def _admission(level="INTERNAL_DEMO"):
    return {
        "consumption_level": level,
        "source_release": "dev",
        "admitted": True,
        "unmet": [],
        "watermark_required": True,
        "isolation": "internal_only" if level == "INTERNAL_DEMO" else "none",
    }


def _find_span(spans_doc, span_id):
    for span in spans_doc["spans"]:
        if span["span_id"] == span_id:
            return span
    raise AssertionError("未找到 span: %s" % span_id)


class SourceAssetPackTests(unittest.TestCase):
    """build_source_asset_pack 的正常与拒绝路径。"""

    def test_source_asset_pack_pages_follow_manifest_order(self):
        manifest = _manifest()
        records = _asset_records()
        result = _source_pack(records)
        pack = result["pack"]
        self.assertEqual(
            [page["page"] for page in pack["pages"]],
            manifest["edition_part"]["pages"],
        )
        self.assertEqual(pack["content_level"], "derived_page_images_only")
        for page_entry, source in zip(pack["pages"], manifest["source_assets"]):
            self.assertEqual(page_entry["sha256"], source["sha256"])
            self.assertEqual(
                (page_entry["width"], page_entry["height"]),
                (source["width"], source["height"]),
            )
            self.assertEqual(
                page_entry["asset_artifact_revision_id"],
                records[source["page"]]["artifact_revision_id"],
            )
        self.assertEqual(set(result.keys()), {"pack", "bytes", "sha256"})
        self.assertEqual(result["sha256"], hashlib.sha256(result["bytes"]).hexdigest())

    def test_source_asset_pack_sha_mismatch_SRC_003(self):
        records = _asset_records()
        records["page_001"]["sha256"] = "0" * 64
        with self.assertRaises(HashMismatch) as ctx:
            _source_pack(records)
        self.assertEqual(ctx.exception.code, "SRC_003")

    def test_source_asset_pack_dimension_mismatch_SRC_003(self):
        records = _asset_records()
        records["page_001"]["width"] += 1
        with self.assertRaises(HashMismatch) as ctx:
            _source_pack(records)
        self.assertEqual(ctx.exception.code, "SRC_003")
        self.assertIn("尺寸", str(ctx.exception))

    def test_source_asset_pack_missing_page_REF_001(self):
        records = _asset_records()
        del records["page_003"]
        with self.assertRaises(MissingReference) as ctx:
            _source_pack(records)
        self.assertEqual(ctx.exception.code, "REF_001")

        manifest = _manifest()
        manifest["source_assets"] = [
            item
            for item in manifest["source_assets"]
            if item["page"] != "page_002"
        ]
        with self.assertRaises(MissingReference) as ctx2:
            packs.build_source_asset_pack(manifest=manifest, asset_records=_asset_records())
        self.assertEqual(ctx2.exception.code, "REF_001")

    def test_source_asset_pack_extra_page_SCH_002(self):
        records = _asset_records()
        records["page_004"] = copy.deepcopy(records["page_001"])
        with self.assertRaises(SchemaViolation) as ctx:
            _source_pack(records)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_source_asset_pack_other_policy_refused(self):
        manifest = _manifest()
        manifest["release_policy"] = "full_scan"
        with self.assertRaises(DatasetRefused) as ctx:
            packs.build_source_asset_pack(manifest=manifest, asset_records=_asset_records())
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertIn("derived_page_images_only", str(ctx.exception))


class EvidenceMapPackTests(unittest.TestCase):
    """build_evidence_map_pack 的 fixture 数字与拒绝路径。"""

    def test_evidence_map_fixture_counts(self):
        result = _evidence_pack()
        self.assertEqual(result["pack"]["span_count"], 43)
        self.assertEqual(len(result["span_keys"]), 43)
        self.assertEqual(result["highlight_counts"], {"glyph": 41, "line_bbox": 2})
        self.assertEqual(result["glyph_count"], 230)

    def test_line_bbox_spans_exact(self):
        result = _evidence_pack()
        entries = result["pack"]["entries"]
        line_bbox = [
            span_id
            for span_id in result["span_keys"]
            if entries[span_id]["highlight_level"] == "line_bbox"
        ]
        self.assertEqual(
            line_bbox,
            ["ss_sanche_ed01_p0001_s03", "ss_sanche_ed01_p0001_s04"],
        )

    def test_page_index_fixture(self):
        spans_doc = _spans_doc()
        result = _evidence_pack()
        page_index = result["pack"]["page_index"]
        expected = {"page_001": [], "page_002": [], "page_003": []}
        for span in spans_doc["spans"]:
            expected[span["page"]].append(span["span_id"])
        self.assertEqual(page_index, expected)
        self.assertEqual(len(page_index["page_001"]), 4)
        self.assertEqual(page_index["page_002"], [])
        self.assertEqual(len(page_index["page_003"]), 39)

    def test_entries_keyed_by_full_span_id_not_seq(self):
        spans_doc = _spans_doc()
        result = _evidence_pack()
        expected_keys = {span["span_id"] for span in spans_doc["spans"]}
        self.assertEqual(set(result["span_keys"]), expected_keys)
        # 按 build_index.py 的 (source_id, int(sNN)) 规则取键会塌缩
        legacy = {}
        groups = {}
        for span in spans_doc["spans"]:
            seq = int(span["span_id"].rsplit("_s", 1)[1])
            legacy[(spans_doc["source_id"], seq)] = span["span_id"]
            groups.setdefault((spans_doc["source_id"], seq), []).append(span["span_id"])
        self.assertEqual(len(legacy), 39)
        collisions = sum(1 for members in groups.values() if len(members) > 1)
        self.assertEqual(collisions, 4)
        self.assertEqual(len(result["span_keys"]), 43)

    def test_span_id_page_mismatch_ID_001(self):
        spans_doc = copy.deepcopy(_spans_doc())
        _find_span(spans_doc, "ss_sanche_ed01_p0003_s01")["page"] = "page_001"
        with self.assertRaises(InvalidIdentifier) as ctx:
            _evidence_pack(spans_doc=spans_doc)
        self.assertEqual(ctx.exception.code, "ID_001")
        self.assertIn("页号", str(ctx.exception))

    def test_span_seq_mismatch_ID_001(self):
        spans_doc = copy.deepcopy(_spans_doc())
        _find_span(spans_doc, "ss_sanche_ed01_p0001_s01")["line_index"] = 3
        with self.assertRaises(InvalidIdentifier) as ctx:
            _evidence_pack(spans_doc=spans_doc)
        self.assertEqual(ctx.exception.code, "ID_001")
        self.assertIn("行序", str(ctx.exception))

    def test_duplicate_span_id_ID_002(self):
        spans_doc = copy.deepcopy(_spans_doc())
        spans_doc["spans"].append(copy.deepcopy(spans_doc["spans"][0]))
        spans_doc["span_count"] = len(spans_doc["spans"])
        with self.assertRaises(DuplicateIdentifier) as ctx:
            _evidence_pack(spans_doc=spans_doc)
        self.assertEqual(ctx.exception.code, "ID_002")

    def test_anchor_page_mismatch_refused(self):
        spans_doc = copy.deepcopy(_spans_doc())
        _find_span(spans_doc, "ss_sanche_ed01_p0001_s01")["source_anchor"]["page"] = "page_003"
        with self.assertRaises(DatasetRefused) as ctx:
            _evidence_pack(spans_doc=spans_doc)
        self.assertEqual(ctx.exception.code, "REF_001")
        self.assertIn("锚点页", str(ctx.exception))

    def test_image_sha_mismatch_SRC_003(self):
        spans_doc = copy.deepcopy(_spans_doc())
        _find_span(spans_doc, "ss_sanche_ed01_p0001_s01")["source_anchor"][
            "image_sha256"
        ] = "0" * 64
        with self.assertRaises(HashMismatch) as ctx:
            _evidence_pack(spans_doc=spans_doc)
        self.assertEqual(ctx.exception.code, "SRC_003")

    def test_frame_mismatch_refused(self):
        page_docs = _page_docs()
        page_docs["page_001"]["width"] = page_docs["page_001"]["width"] + 1
        with self.assertRaises(DatasetRefused) as ctx:
            _evidence_pack(page_docs=page_docs)
        self.assertEqual(ctx.exception.code, "SRC_003")
        self.assertIn("坐标系", str(ctx.exception))

    def test_box_out_of_frame_refused(self):
        spans_doc = copy.deepcopy(_spans_doc())
        box = _find_span(spans_doc, "ss_sanche_ed01_p0001_s01")["source_anchor"]["bbox"]
        box["x"] = 1203.0
        box["w"] = 1.0
        with self.assertRaises(DatasetRefused) as ctx:
            _evidence_pack(spans_doc=spans_doc)
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertIn("越界", str(ctx.exception))

    def test_span_on_excluded_page_refused(self):
        spans_doc = copy.deepcopy(_spans_doc())
        span = spans_doc["spans"][0]
        span["span_id"] = "ss_sanche_ed01_p0002_s01"
        span["page"] = "page_002"
        span["line_index"] = 0
        span["source_anchor"]["page"] = "page_002"
        with self.assertRaises(DatasetRefused) as ctx:
            _evidence_pack(spans_doc=spans_doc)
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertIn("排除页", str(ctx.exception))

    def test_deterministic_bytes_twice(self):
        first = _evidence_pack()
        second = _evidence_pack()
        self.assertEqual(first["bytes"], second["bytes"])
        self.assertEqual(first["sha256"], second["sha256"])

    def test_normalized_sha_ignores_revision_ids(self):
        first = _evidence_pack(
            source_pack=_source_pack(_asset_records(base=1)),
            ocr_revision_ids=_ocr_revision_ids(base=101),
        )
        second = _evidence_pack(
            source_pack=_source_pack(_asset_records(base=201)),
            ocr_revision_ids=_ocr_revision_ids(base=301),
        )
        self.assertNotEqual(first["bytes"], second["bytes"])
        self.assertEqual(first["normalized_sha256"], second["normalized_sha256"])


class EvidenceMapKnowledgeChainFlagTests(unittest.TestCase):
    """ACT 13 / D-W8-13b：``knowledge_chain`` 由 Snapshot 事实推导（packs 内部，非调用方字面量）。"""

    def test_knowledge_chain_not_compiled_without_snapshot(self):
        res = _evidence_pack()
        self.assertEqual(res["pack"]["knowledge_chain"], "not_compiled")
        # 本切片链段仍为四段，本 ACT 不改（见 D-W8-13b）
        self.assertEqual(len(res["pack"]["chain_segments"]), 4)
        self.assertEqual(res["pack"]["chain_segments"], packs.CHAIN_SEGMENTS)

    def test_knowledge_chain_compiled_with_snapshot(self):
        res = _evidence_pack(
            snapshot_knowledge={"patterns": [], "assertions": [], "concepts": []}
        )
        self.assertEqual(res["pack"]["knowledge_chain"], "compiled")
        defects = packs.compute_known_defects(
            evidence_map_pack=res["pack"],
            m3_gate_profile="structural_only",
            rights_status=_manifest()["rights_status"],
        )
        self.assertNotIn(
            "knowledge_chain_not_compiled", [item["code"] for item in defects]
        )

    def test_snapshot_presence_changes_only_the_flag(self):
        without = _evidence_pack()
        with_snapshot = _evidence_pack(
            snapshot_knowledge={"patterns": [], "assertions": [], "concepts": []}
        )
        self.assertEqual(without["pack"]["entries"], with_snapshot["pack"]["entries"])
        self.assertEqual(
            without["pack"]["chain_segments"], with_snapshot["pack"]["chain_segments"]
        )
        self.assertNotEqual(
            without["pack"]["knowledge_chain"],
            with_snapshot["pack"]["knowledge_chain"],
        )


class KnownDefectsTests(unittest.TestCase):
    """compute_known_defects 的代码闭集。"""

    def test_known_defects_fixture_codes(self):
        evidence = _evidence_pack()
        defects = packs.compute_known_defects(
            evidence_map_pack=evidence["pack"],
            m3_gate_profile="structural_only",
            rights_status=_manifest()["rights_status"],
        )
        self.assertEqual(
            [item["code"] for item in defects],
            [
                "excluded_page",
                "glyph_text_mismatch",
                "knowledge_chain_not_compiled",
                "machine_content",
                "rights_unconfirmed",
                "semantic_not_evaluated",
            ],
        )
        detail = {item["code"]: item["detail"] for item in defects}
        self.assertEqual(detail["excluded_page"], "page_002=known_unrecognizable")
        self.assertEqual(
            detail["glyph_text_mismatch"],
            "ss_sanche_ed01_p0001_s03,ss_sanche_ed01_p0001_s04",
        )

    def test_known_defects_offset_level_skips_glyph_check(self):
        """offset 档跳过 glyph 检查，不抛 KeyError，且无 glyph_text_mismatch。"""
        offset_evidence = _offset_evidence_pack()["pack"]
        self.assertEqual(offset_evidence["evidence_level"], "offset_level")
        defects = packs.compute_known_defects(
            evidence_map_pack=offset_evidence,
            m3_gate_profile="structural_only",
            rights_status="站方声明免费下载、未附许可证",
        )
        codes = [item["code"] for item in defects]
        self.assertNotIn("glyph_text_mismatch", codes)

    def test_known_defects_offset_level_emits_no_new_code(self):
        """offset 档不产出任何新 code（闭集未扩大）。"""
        offset_evidence = _offset_evidence_pack()["pack"]
        defects = packs.compute_known_defects(
            evidence_map_pack=offset_evidence,
            m3_gate_profile="structural_only",
            rights_status="站方声明免费下载、未附许可证",
        )
        codes = [item["code"] for item in defects]
        allowed_codes = {
            "excluded_page",
            "glyph_text_mismatch",
            "knowledge_chain_not_compiled",
            "machine_content",
            "rights_unconfirmed",
            "semantic_not_evaluated",
        }
        for code in codes:
            self.assertIn(code, allowed_codes)

    def test_known_defects_glyphbox_missing_highlight_level_still_raises(self):
        """glyphbox 档若丢失 highlight_level 键，仍须报错（驳回 .get() 免疫写法）。"""
        bad_evidence = copy.deepcopy(_evidence_pack()["pack"])
        self.assertEqual(bad_evidence["evidence_level"], "glyphbox_level")
        first_key = next(iter(bad_evidence["entries"]))
        bad_evidence["entries"][first_key].pop("highlight_level", None)
        with self.assertRaises(KeyError):
            packs.compute_known_defects(
                evidence_map_pack=bad_evidence,
                m3_gate_profile="structural_only",
                rights_status=_manifest()["rights_status"],
            )

    def test_known_defects_glyphbox_level_unchanged(self):
        """OCR 档回归护栏：证据级别为 glyphbox_level 时行为逐字不变。"""
        evidence = _evidence_pack()
        self.assertEqual(evidence["pack"]["evidence_level"], "glyphbox_level")
        defects = packs.compute_known_defects(
            evidence_map_pack=evidence["pack"],
            m3_gate_profile="structural_only",
            rights_status=_manifest()["rights_status"],
        )
        self.assertEqual(
            [item["code"] for item in defects],
            [
                "excluded_page",
                "glyph_text_mismatch",
                "knowledge_chain_not_compiled",
                "machine_content",
                "rights_unconfirmed",
                "semantic_not_evaluated",
            ],
        )
        detail = {item["code"]: item["detail"] for item in defects}
        self.assertEqual(detail["glyph_text_mismatch"], "ss_sanche_ed01_p0001_s03,ss_sanche_ed01_p0001_s04")


class ReleaseManifestTests(unittest.TestCase):
    """build_release_manifest 的哈希、排序与 fail-closed。"""

    def _packs(self):
        return [
            {
                "pack_type": "source_asset_pack",
                "artifact_revision_id": "rev_%032x" % 11,
                "sha256": "a" * 64,
                "size": 10,
            },
            {
                "pack_type": "evidence_map_pack",
                "artifact_revision_id": "rev_%032x" % 12,
                "sha256": "b" * 64,
                "size": 20,
            },
        ]

    def _reconciliation(self):
        return [
            {
                "artifact_revision_id": "rev_%032x" % 22,
                "artifact_type": "corpus_spans",
                "sha256": "c" * 64,
            },
            {
                "artifact_revision_id": "rev_%032x" % 21,
                "artifact_type": "source_manifest",
                "sha256": "d" * 64,
            },
        ]

    def _build(self, **overrides):
        kwargs = {
            "release_id": "rel_%032x" % 7,
            "admission": _admission(),
            "release_scope": {"edition_part_ids": ["art_%032x" % 1]},
            "technique_id": "qizheng",
            "packs": self._packs(),
            "input_reconciliation": self._reconciliation(),
            "schema_versions": {
                "evidence_map_pack": "0.1.0-draft",
                "release_manifest": "0.1.0-draft",
                "source_asset_pack": "0.1.0-draft",
            },
            "min_app_version": None,
            "known_defects": [],
            "watermark_text": packs.INTERNAL_DEMO_WATERMARK,
        }
        kwargs.update(overrides)
        return packs.build_release_manifest(**kwargs)

    def test_release_manifest_canonical_hash_and_sorting(self):
        result = self._build()
        manifest = result["manifest"]
        self.assertEqual(
            [item["pack_type"] for item in manifest["packs"]],
            ["evidence_map_pack", "source_asset_pack"],
        )
        expected_hash = sha256_hex(
            canonical_bytes(
                [
                    ["evidence_map_pack", "b" * 64],
                    ["source_asset_pack", "a" * 64],
                ]
            )
        )
        self.assertEqual(result["canonical_hash"], expected_hash)
        self.assertEqual(manifest["canonical_hash"], expected_hash)
        self.assertEqual(result["sha256"], sha256_hex(result["bytes"]))
        recon_ids = [
            item["artifact_revision_id"] for item in manifest["input_reconciliation"]
        ]
        self.assertEqual(recon_ids, sorted(recon_ids))
        self.assertEqual(manifest["authoritative"], False)
        self.assertEqual(manifest["completeness_claim"], "partial")

    def test_release_manifest_refuses_not_admitted(self):
        admission = _admission()
        admission["admitted"] = False
        with self.assertRaises(DatasetRefused) as ctx:
            self._build(admission=admission)
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertIn("fail-closed", str(ctx.exception))

    def test_release_manifest_refuses_dev_search_even_if_admitted_flag(self):
        admission = _admission(level="DEV_SEARCH")
        admission["admitted"] = True
        with self.assertRaises(DatasetRefused) as ctx:
            self._build(admission=admission)
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertIn("fail-closed", str(ctx.exception))

    def test_release_manifest_duplicate_pack_type_ID_002(self):
        packs_in = self._packs()
        packs_in.append(copy.deepcopy(packs_in[0]))
        with self.assertRaises(DuplicateIdentifier) as ctx:
            self._build(packs=packs_in)
        self.assertEqual(ctx.exception.code, "ID_002")


class GraphProjectionPackTests(unittest.TestCase):
    """build_graph_projection_pack 纯函数编译与契约草案（INTERFACES §3.15，ACT 09）。"""

    def _sample_pack_args(self, level="INTERNAL_DEMO"):
        release_id = "rel_018f9e74e27670008000000000000001"
        canonical_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        nodes = [
            {
                "node_id": "as_synth_000001",
                "kind": "assertion",
                "label": "合成断言甲",
                "content_status": "machine_extracted",
            },
            {
                "node_id": "co_synth_000001",
                "kind": "concept",
                "label": "合成概念甲",
                "content_status": "machine_extracted",
            },
            {
                "node_id": "pat_synth_000001",
                "kind": "pattern",
                "label": "合成格局甲",
                "content_status": "machine_extracted",
            },
        ]
        edges = [
            {
                "source": "as_synth_000001",
                "relation": "belongs_to_concept",
                "target": "co_synth_000001",
                "content_status": "machine_extracted",
            },
            {
                "source": "pat_synth_000001",
                "relation": "has_assertion",
                "target": "as_synth_000001",
                "content_status": "machine_extracted",
            },
        ]
        return {
            "release_id": release_id,
            "canonical_hash": canonical_hash,
            "consumption_level": level,
            "nodes": nodes,
            "edges": edges,
        }

    def test_graph_projection_structure_matches_registered_schema(self):
        args = self._sample_pack_args()
        result = packs.build_graph_projection_pack(**args)
        pack = result["pack"]
        expected_keys = {
            "schema_version",
            "release_id",
            "canonical_hash",
            "consumption_level",
            "nodes",
            "edges",
            "node_count",
            "edge_count",
        }
        self.assertEqual(set(pack.keys()), expected_keys)
        self.assertEqual(pack["schema_version"], "0.1.0-draft")
        self.assertEqual(pack["node_count"], 3)
        self.assertEqual(pack["edge_count"], 2)

    def test_graph_projection_edges_have_no_id(self):
        args = self._sample_pack_args()
        result = packs.build_graph_projection_pack(**args)
        pack = result["pack"]
        for edge in pack["edges"]:
            self.assertNotIn("edge_id", edge)
            self.assertNotIn("id", edge)
        # 显式篡改/传入带有 edge_id 的边 → 拒绝
        bad_args = self._sample_pack_args()
        bad_args["edges"][0]["edge_id"] = "e_018f9e74e27670008000000000000001"
        with self.assertRaises(SchemaViolation) as ctx:
            packs.build_graph_projection_pack(**bad_args)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_graph_projection_sorted_nodes_and_edge_triples(self):
        args = self._sample_pack_args()
        # 逆序输入
        args["nodes"] = list(reversed(args["nodes"]))
        args["edges"] = list(reversed(args["edges"]))
        result = packs.build_graph_projection_pack(**args)
        pack = result["pack"]
        node_ids = [n["node_id"] for n in pack["nodes"]]
        self.assertEqual(node_ids, sorted(node_ids))
        edge_triples = [(e["source"], e["relation"], e["target"]) for e in pack["edges"]]
        self.assertEqual(edge_triples, sorted(edge_triples))

    def test_graph_projection_shares_release_id_and_canonical_hash(self):
        args = self._sample_pack_args()
        result = packs.build_graph_projection_pack(**args)
        pack = result["pack"]
        self.assertEqual(pack["release_id"], args["release_id"])
        self.assertEqual(pack["canonical_hash"], args["canonical_hash"])

    def test_graph_projection_node_ids_use_registered_prefixes(self):
        args = self._sample_pack_args()
        # 非法前缀 c_ 或 未知前缀
        bad_args = self._sample_pack_args()
        bad_args["nodes"].append({
            "node_id": "c_synth_000001",
            "kind": "concept",
            "label": "非法前缀概念",
            "content_status": "machine_extracted",
        })
        with self.assertRaises(InvalidIdentifier) as ctx:
            packs.build_graph_projection_pack(**bad_args)
        self.assertEqual(ctx.exception.code, "ID_001")

    def test_graph_projection_relation_closed_set(self):
        bad_args = self._sample_pack_args()
        bad_args["edges"].append({
            "source": "as_synth_000001",
            "relation": "unregistered_relation",
            "target": "co_synth_000001",
            "content_status": "machine_extracted",
        })
        with self.assertRaises(SchemaViolation) as ctx:
            packs.build_graph_projection_pack(**bad_args)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_graph_projection_internal_demo_watermarks_machine_content(self):
        args = self._sample_pack_args(level="INTERNAL_DEMO")
        result = packs.build_graph_projection_pack(**args)
        pack = result["pack"]
        for node in pack["nodes"]:
            if node["content_status"].startswith("machine_"):
                self.assertTrue(node["watermark"])
        for edge in pack["edges"]:
            if edge["content_status"].startswith("machine_"):
                self.assertTrue(edge["watermark"])

    def test_graph_projection_bytes_deterministic(self):
        args = self._sample_pack_args()
        res1 = packs.build_graph_projection_pack(**args)
        res2 = packs.build_graph_projection_pack(**args)
        self.assertEqual(res1["bytes"], res2["bytes"])
        self.assertEqual(res1["sha256"], res2["sha256"])

    def test_graph_projection_mirrors_knowledge_data_entities(self):
        # 从 KnowledgeDataPack 结构同构生成节点
        kd = {
            "release_id": "rel_018f9e74e27670008000000000000001",
            "technique_id": "synth",
            "consumption_level": "INTERNAL_DEMO",
            "concepts": [
                {"concept_id": "co_synth_000001", "name": "合成概念A", "content_status": "machine_extracted"},
            ],
            "assertions": [
                {"assertion_id": "as_synth_000001", "proposition": "合成命题A", "status": "machine_extracted"},
                {"assertion_id": "as_synth_000002", "proposition": "合成命题B", "status": "machine_extracted"},
            ],
            "patterns": [
                {"pattern_id": "pat_synth_000001", "name": "合成格局A", "content_status": "machine_extracted"},
            ],
        }
        result = packs.build_graph_projection_pack(
            release_id=kd["release_id"],
            canonical_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            consumption_level=kd["consumption_level"],
            knowledge_data=kd,
        )
        pack = result["pack"]
        projected_node_ids = {n["node_id"] for n in pack["nodes"]}
        expected_node_ids = {"co_synth_000001", "as_synth_000001", "as_synth_000002", "pat_synth_000001"}
        self.assertEqual(projected_node_ids, expected_node_ids)


class OffsetEvidenceAndReferenceOnlyTests(unittest.TestCase):
    """ACT 10：reference_and_hash_only 策略与 offset 七段证据链（INTERFACES §3.10、§3.11）。"""

    def test_source_asset_pack_reference_and_hash_only_has_no_bytes_or_text(self):
        manifest = _manifest()
        manifest["release_policy"] = "reference_and_hash_only"
        records = _asset_records()
        result = packs.build_source_asset_pack(
            manifest=manifest,
            asset_records=records,
        )
        pack = result["pack"]
        self.assertEqual(pack["content_level"], "reference_and_hash_only")
        for page in pack["pages"]:
            self.assertFalse(page["bytes_included"])
            self.assertIn("rights_note", page)
            self.assertIn("sha256", page)
            self.assertIn("asset_artifact_revision_id", page)
            self.assertNotIn("width", page)
            self.assertNotIn("height", page)
            self.assertNotIn("size", page)
            self.assertNotIn("text", page)

    def _sample_offset_chain_args(self, policy="derived_page_images_only"):
        return {
            "entry_id": "ent_018f9e74e27670008000000000000001",
            "assertion_id": "as_synth_000001",
            "evidence_link": {
                "assertion_id": "as_synth_000001",
                "source_span_id": "ss_synth_ed01_o0000100",
                "start_offset": 100,
                "end_offset": 120,
                "quote": "合成测试引文",
                "quote_sha256": sha256_hex("合成测试引文".encode("utf-8")),
            },
            "source_span": {
                "source_span_id": "ss_synth_ed01_o0000100",
                "source_id": "src_synth_ed01",
                "page": None,
                "start_offset": 100,
                "end_offset": 120,
                "text": "合成测试片段正文",
            },
            "source_anchor": {
                "source_id": "src_synth_ed01",
                "edition_part_id": "art_018f9e74e27670008000000000000001",
                "span_layer": "structural",
                "start_offset": 100,
                "end_offset": 120,
                "cleaned_text_sha256": "0" * 64,
                "anchor_stability": "permanent",
            },
            "evidence_level": "offset_level",
            "release_policy": policy,
            "text_mapping": {
                "raw_text_revision_id": "rev_018f9e74e27670008000000000000001",
                "cleaned_text_revision_id": "rev_018f9e74e27670008000000000000002",
                "patch_set_revision_id": "rev_018f9e74e27670008000000000000003",
                "raw_start": 98,
                "raw_end": 118,
            },
            "source_asset": {
                "page": None,
                "sha256": "a" * 64,
            },
        }

    def test_evidence_map_offset_chain_has_exactly_seven_keys(self):
        args = self._sample_offset_chain_args()
        chain = packs.build_evidence_chain(**args)
        expected_keys = {
            "entry_id",
            "assertion_id",
            "evidence_link",
            "source_span",
            "source_anchor",
            "text_mapping",
            "source_asset",
        }
        self.assertEqual(set(chain.keys()), expected_keys)
        self.assertEqual(len(chain.keys()), 7)

    def test_evidence_map_offset_text_mapping_fields(self):
        args = self._sample_offset_chain_args()
        chain = packs.build_evidence_chain(**args)
        expected_tm_keys = {
            "raw_text_revision_id",
            "cleaned_text_revision_id",
            "patch_set_revision_id",
            "raw_start",
            "raw_end",
        }
        self.assertEqual(set(chain["text_mapping"].keys()), expected_tm_keys)

    def test_evidence_map_reference_and_hash_only_nulls_quote_and_text(self):
        args = self._sample_offset_chain_args(policy="reference_and_hash_only")
        chain = packs.build_evidence_chain(**args)
        self.assertIsNone(chain["evidence_link"]["quote"])
        self.assertIsNone(chain["source_span"]["text"])
        self.assertIsNotNone(chain["evidence_link"]["quote_sha256"])

    def test_evidence_map_glyphbox_chain_bytes_unchanged(self):
        res = _evidence_pack()
        self.assertEqual(
            res["sha256"],
            "b79a7380d79ca8892ae15ad6b4a0034b298765c4240af3c99412153940566fc8",
        )

    def test_offset_span_identity_via_ledger_ids(self):
        span_id = "ss_synth_ed01_o0000100"
        pno, offset = packs.parse_span_identity(span_id)
        self.assertIsNone(pno)
        self.assertEqual(offset, 100)
        # 非法 span_id
        with self.assertRaises(InvalidIdentifier) as ctx:
            packs.parse_span_identity("ss_synth_ed01_bad")
        self.assertEqual(ctx.exception.code, "ID_001")

    def test_no_private_span_regex_in_dataset_compiler(self):
        pkg_dir = os.path.join(_REPO_ROOT, "pipeline", "dataset_compiler")
        for fname in os.listdir(pkg_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(pkg_dir, fname)
            with open(fpath, encoding="utf-8") as handle:
                text = handle.read()
            # 检查是否有自有 ss_ 正则（除从 ids 导入外）
            for m in re.finditer(r're\.compile\(r?["\'][^"\']*ss_[^"\']*["\']\)', text):
                self.fail("文件 %s 包含自有 ss_ 正则: %s（第 102 条）" % (fname, m.group(0)))


# ---- ACT 14：offset 档输入事实（取自真书只读实测形状，硬编码作断言事实，不依赖 var/）----
_OFFSET_RAW_TEXT_REV = "rev_299e1d31000e44ca91666c6deefb42fb"
_OFFSET_CLEANED_REV = "rev_cf79eb3b11e5497daa6ac1e36af9a3a8"
_OFFSET_RAW_TEXT_SHA = (
    "3f7170cd504e496096bc933ab5ed8805d68fa98625c91c5c09a9e3a61fcecdbb"
)
_OFFSET_EDITION_PART = "art_00000000000000000000000000000001"
_OFFSET_PAGE_UNIT = "qianyuan_ed01_text"
# 裁定 78 D3：offset 档 SourceAnchor 七键
_ANCHOR_SEVEN_KEYS = (
    "cleaned_text_revision_id",
    "end_offset",
    "quote_sha256",
    "raw_end",
    "raw_start",
    "raw_text_revision_id",
    "start_offset",
)
# 裁定 78 D3 / README:375：offset 档链段八段（D-W8-14 逐字采用）
_OFFSET_CHAIN_SEGMENTS = [
    "KnowledgeEntry",
    "Assertion",
    "EvidenceLink",
    "SourceSpan",
    "SourceAnchor",
    "DeterministicPatchSet",
    "RawText",
    "SourceAsset",
]
# OCR 档 derived_page_images_only 的页条目键集（既有行为，逐字不变）
_OCR_SOURCE_PAGE_KEYS = (
    "page",
    "asset_artifact_revision_id",
    "sha256",
    "size",
    "width",
    "height",
)

# 真书前两个 span 的逐字文本与其 quote_sha256（只读实测）
_OFFSET_SPAN_TEXTS = (
    ("ss_qianyuan_ed01_o0000478", "\n", 0, 1, 478, 479),
    (
        "ss_qianyuan_ed01_o0000479",
        "[七政四余]乾元秘旨--舒继英    \n",
        1,
        21,
        479,
        503,
    ),
)


def _offset_anchor(span_id, text, start, end, raw_start, raw_end, *, extra=None):
    anchor = {
        "raw_text_revision_id": _OFFSET_RAW_TEXT_REV,
        "raw_start": raw_start,
        "raw_end": raw_end,
        "cleaned_text_revision_id": _OFFSET_CLEANED_REV,
        "start_offset": start,
        "end_offset": end,
        "quote_sha256": sha256_hex(text.encode("utf-8")),
    }
    if extra is not None:
        anchor[extra] = "额外键"
    return anchor


def _offset_spans_doc(*, drop_anchor_key=None, add_anchor_key=None, tamper_quote=False):
    spans = []
    for sequence, (span_id, text, start, end, raw_start, raw_end) in enumerate(
        _OFFSET_SPAN_TEXTS, start=1
    ):
        anchor = _offset_anchor(span_id, text, start, end, raw_start, raw_end)
        if drop_anchor_key is not None:
            anchor.pop(drop_anchor_key)
        if add_anchor_key is not None:
            anchor[add_anchor_key] = "额外键"
        quote = sha256_hex(text.encode("utf-8"))
        if tamper_quote and sequence == 1:
            quote = sha256_hex(b"tampered")
        spans.append(
            {
                "span_id": span_id,
                "sequence": sequence,
                "start_offset": start,
                "end_offset": end,
                "text": text,
                "quote_sha256": quote,
                "evidence_level": "offset_level",
                "source_anchor": anchor,
            }
        )
    return {
        "work": "qianyuan",
        "source_id": "src_qianyuan_ed01",
        "edition_part_artifact_id": _OFFSET_EDITION_PART,
        "evidence_level": "offset_level",
        "content_status": "machine_extracted",
        "span_count": len(spans),
        "spans": spans,
    }


def _offset_manifest():
    """offset 档清单：字段与真书 source_manifest 同形（含 width/height 为 null 的干扰键）。"""
    return {
        "source_id": "src_qianyuan_ed01",
        "work_title": "乾元秘旨",
        "technique_id": "qizheng",
        "rights_status": "站方声明免费下载、未附许可证",
        "release_policy": "reference_and_hash_only",
        "content_status": "machine_extracted",
        "edition_part": {
            "artifact_id": _OFFSET_EDITION_PART,
            "label": "乾元秘旨·全篇（单文件，无页码）",
            "pages": [_OFFSET_PAGE_UNIT],
        },
        "source_assets": [
            {
                "page": _OFFSET_PAGE_UNIT,
                "path_ref": "qianyuan_ed01_text.md",
                "sha256": _OFFSET_RAW_TEXT_SHA,
                "normalized_sha256": _OFFSET_RAW_TEXT_SHA,
                "original_encoding": "utf-8",
                "size": 50451,
                "object_store": "local",
                "in_git": False,
                "width": None,
                "height": None,
                "repo_commit": "aa2b70789d153f2542e5f4786265157c7356ab76",
                "source_site": "github.com/daizhige-org/daizhigev20",
            }
        ],
    }


def _offset_source_pack(raw_text_sha256=_OFFSET_RAW_TEXT_SHA, manifest=None):
    return packs.build_source_asset_pack(
        manifest=_offset_manifest() if manifest is None else manifest,
        asset_records={},
        raw_text_sha256=raw_text_sha256,
    )


def _offset_evidence_pack(spans_doc=None, excluded_pages=None, source_pack=None):
    """offset 档证据包编译。

    默认传空 source_asset_pack：offset 变体**不读**该包（ACT 14 二.1），
    传空字典本身就是这条契约的护栏。
    """
    return packs.build_evidence_map_pack(
        spans_doc=_offset_spans_doc() if spans_doc is None else spans_doc,
        page_docs={},
        ocr_page_revision_ids={},
        source_asset_pack={} if source_pack is None else source_pack,
        excluded_pages={} if excluded_pages is None else excluded_pages,
        snapshot_knowledge=None,
    )


class OffsetLevelPackVariantTests(unittest.TestCase):
    """ACT 14：EvidenceMapPack / SourceAssetPack 的 offset 变体（D-W8-14、裁定 78 D3/81/103 D1）。"""

    def test_evidence_map_pack_offset_level_accepts_seven_key_anchor(self):
        result = _offset_evidence_pack()
        pack = result["pack"]
        self.assertEqual(pack["pack_type"], "evidence_map_pack")
        self.assertEqual(pack["evidence_level"], "offset_level")
        self.assertEqual(pack["span_count"], 2)
        self.assertEqual(
            list(pack["entries"]),
            ["ss_qianyuan_ed01_o0000478", "ss_qianyuan_ed01_o0000479"],
        )
        for span_id, text, start, end, raw_start, raw_end in _OFFSET_SPAN_TEXTS:
            entry = pack["entries"][span_id]
            self.assertEqual(sorted(entry["source_anchor"]), sorted(_ANCHOR_SEVEN_KEYS))
            # I-11：偏移逐字透传，不加不减
            self.assertEqual(entry["start_offset"], start)
            self.assertEqual(entry["end_offset"], end)
            self.assertEqual(entry["source_anchor"]["raw_start"], raw_start)
            self.assertEqual(entry["source_anchor"]["raw_end"], raw_end)
            self.assertEqual(entry["text"], text)
            self.assertEqual(entry["quote_sha256"], sha256_hex(text.encode("utf-8")))
            # offset 档不得出现字框/页字段
            for absent in ("page", "line_index", "bbox", "glyphs", "frame"):
                self.assertNotIn(absent, entry)

    def test_evidence_map_pack_offset_level_refuses_anchor_missing_key(self):
        for missing in _ANCHOR_SEVEN_KEYS:
            with self.assertRaises(SchemaViolation) as ctx:
                _offset_evidence_pack(
                    spans_doc=_offset_spans_doc(drop_anchor_key=missing)
                )
            self.assertEqual(ctx.exception.code, "SCH_002")
            self.assertIn("ss_qianyuan_ed01_o0000478", str(ctx.exception))
            self.assertIn(missing, str(ctx.exception))

    def test_evidence_map_pack_offset_level_refuses_anchor_extra_key(self):
        with self.assertRaises(SchemaViolation) as ctx:
            _offset_evidence_pack(spans_doc=_offset_spans_doc(add_anchor_key="bbox"))
        self.assertEqual(ctx.exception.code, "SCH_002")
        self.assertIn("bbox", str(ctx.exception))

    def test_evidence_map_pack_offset_level_chain_segments_are_the_eight(self):
        pack = _offset_evidence_pack()["pack"]
        self.assertEqual(pack["chain_segments"], _OFFSET_CHAIN_SEGMENTS)
        self.assertEqual(len(pack["chain_segments"]), 8)

    def test_evidence_map_pack_offset_level_page_index_is_empty_dict_not_absent(self):
        pack = _offset_evidence_pack()["pack"]
        self.assertIn("page_index", pack)
        self.assertEqual(pack["page_index"], {})

    def test_evidence_map_pack_offset_level_detects_quote_sha_mismatch(self):
        with self.assertRaises(HashMismatch) as ctx:
            _offset_evidence_pack(spans_doc=_offset_spans_doc(tamper_quote=True))
        self.assertEqual(ctx.exception.code, "SRC_003")

    def test_source_asset_pack_offset_level_binds_raw_text_sha256(self):
        result = _offset_source_pack()
        pack = result["pack"]
        self.assertEqual(pack["pack_type"], "source_asset_pack")
        self.assertEqual(pack["content_level"], "reference_and_hash_only")
        self.assertEqual(len(pack["pages"]), 1)
        entry = pack["pages"][0]
        self.assertEqual(
            sorted(entry),
            [
                "normalized_sha256",
                "original_encoding",
                "page",
                "path_ref",
                "sha256",
                "size",
            ],
        )
        self.assertEqual(entry["page"], _OFFSET_PAGE_UNIT)
        self.assertEqual(entry["sha256"], _OFFSET_RAW_TEXT_SHA)
        # 页图几何字段不得以 0/None 占位出现
        for absent in ("width", "height", "asset_artifact_revision_id"):
            self.assertNotIn(absent, entry)
        # raw_text 修订 sha256 与条目不符 → SRC_003
        with self.assertRaises(HashMismatch) as ctx:
            _offset_source_pack(raw_text_sha256="0" * 64)
        self.assertEqual(ctx.exception.code, "SRC_003")

    def test_glyphbox_level_packs_unchanged(self):
        evidence = _evidence_pack()
        self.assertEqual(evidence["pack"]["evidence_level"], "glyphbox_level")
        self.assertEqual(evidence["pack"]["chain_segments"], packs.CHAIN_SEGMENTS)
        self.assertEqual(evidence["pack"]["chain_segments"], [
            "SourceSpan",
            "SourceAnchor",
            "OcrPage",
            "SourceAsset",
        ])
        self.assertEqual(
            evidence["sha256"],
            "b79a7380d79ca8892ae15ad6b4a0034b298765c4240af3c99412153940566fc8",
        )
        source = _source_pack()["pack"]
        self.assertEqual(sorted(source["pages"][0]), sorted(_OCR_SOURCE_PAGE_KEYS))


class KnowledgeDataPackTests(unittest.TestCase):
    """ACT 11：知识链前三段 KnowledgeEntry→Assertion→EvidenceLink（裁决 107 Q-M8-01/Q-M8-02）。"""

    def _snapshot_knowledge(self):
        """合成 Snapshot knowledge（genesis.py 形状；不引用任何书中文句）。"""
        return {
            "technique_id": "qizheng",
            "patterns": [
                {
                    "pattern_id": "pat_qizheng_000001",
                    "name": "示例格局一",
                    "assertion_ids": ["as_qizheng_000001"],
                    "school_view_ids": [],
                    "recognition_rule_status": "not_captured",
                    "concept_id": None,
                },
            ],
            "concepts": [
                {"concept_id": "co_qizheng_000001", "name": "示例概念一", "aliases": []},
            ],
            "assertions": [
                {
                    "assertion_id": "as_qizheng_000001",
                    "proposition": "示例断言甲",
                    "subject_entity_id": "pat_qizheng_000001",
                    "evidence": [
                        {
                            "source_span_id": "ss_synth_ed01_o0000010",
                            "start_offset": 10,
                            "end_offset": 20,
                            "quote_sha256": "0" * 64,
                        }
                    ],
                    "school_view_ids": [],
                    "content_status": "machine_extracted",
                },
                {
                    "assertion_id": "as_qizheng_000002",
                    "proposition": "示例断言乙",
                    "subject_entity_id": None,
                    "evidence": [
                        {
                            "source_span_id": "ss_synth_ed01_o0000020",
                            "start_offset": 20,
                            "end_offset": 30,
                            "quote_sha256": "1" * 64,
                        }
                    ],
                    "school_view_ids": [],
                    "content_status": "machine_extracted",
                },
                {
                    "assertion_id": "as_qizheng_000003",
                    "proposition": "示例断言丙",
                    "subject_entity_id": None,
                    "concept_refs": ["co_qizheng_000001"],
                    "evidence": [
                        {
                            "source_span_id": "ss_synth_ed01_o0000030",
                            "start_offset": 30,
                            "end_offset": 40,
                            "quote_sha256": "2" * 64,
                        }
                    ],
                    "school_view_ids": [],
                    "content_status": "machine_extracted",
                },
                {
                    # 有证据共现（evidence 挂在概念命名 span 上）但无任何显式引用 → 不得推断
                    "assertion_id": "as_qizheng_000004",
                    "proposition": "示例断言丁",
                    "subject_entity_id": None,
                    "evidence": [
                        {
                            "source_span_id": "ss_synth_ed01_o0000030",
                            "start_offset": 30,
                            "end_offset": 40,
                            "quote_sha256": "2" * 64,
                        }
                    ],
                    "school_view_ids": [],
                    "content_status": "machine_extracted",
                },
            ],
            "school_views": [],
            "conflict_groups": [],
        }

    def _allocation(self):
        return {
            "pat_qizheng_000001": "ent_" + "a" * 32,
            "co_qizheng_000001": "ent_" + "b" * 32,
        }

    def test_entry_subjects_dual_track_pattern_and_concept(self):
        knowledge = self._snapshot_knowledge()
        res = packs.build_knowledge_data_pack(
            snapshot_knowledge=knowledge,
            entry_id_allocation=self._allocation(),
            release_id="rel_" + "c" * 32,
            consumption_level="INTERNAL_DEMO",
            technique_id="qizheng",
        )
        pack = res["pack"]
        subjects = {e["subject_entity_id"] for e in pack["entries"]}
        self.assertEqual(
            subjects, {"pat_qizheng_000001", "co_qizheng_000001"}
        )
        pat_entry = next(
            e for e in pack["entries"]
            if e["subject_entity_id"] == "pat_qizheng_000001"
        )
        co_entry = next(
            e for e in pack["entries"]
            if e["subject_entity_id"] == "co_qizheng_000001"
        )
        self.assertEqual(pat_entry["entry_id"], "ent_" + "a" * 32)
        self.assertEqual(co_entry["entry_id"], "ent_" + "b" * 32)
        self.assertEqual(pat_entry["assertion_ids"], ["as_qizheng_000001"])
        self.assertEqual(co_entry["assertion_ids"], ["as_qizheng_000003"])

    def test_assertion_without_subject_is_reported_not_inferred(self):
        knowledge = self._snapshot_knowledge()
        res = packs.build_knowledge_data_pack(
            snapshot_knowledge=knowledge,
            entry_id_allocation=self._allocation(),
            release_id="rel_" + "c" * 32,
            consumption_level="INTERNAL_DEMO",
            technique_id="qizheng",
        )
        self.assertEqual(
            res["assertion_without_subject"],
            ["as_qizheng_000002", "as_qizheng_000004"],
        )
        subject_ids = {e["subject_entity_id"] for e in res["pack"]["entries"]}
        self.assertNotIn("as_qizheng_000002", subject_ids)
        self.assertNotIn("as_qizheng_000004", subject_ids)

    def test_no_subject_inference_from_evidence_cooccurrence(self):
        knowledge = self._snapshot_knowledge()
        # as_qizheng_000004 的证据偏移与 co_qizheng_000001 的断言证据完全共现，
        # 但无显式引用 → 不得为它生成 entry，也不得并入概念词条。
        res = packs.build_knowledge_data_pack(
            snapshot_knowledge=knowledge,
            entry_id_allocation=self._allocation(),
            release_id="rel_" + "c" * 32,
            consumption_level="INTERNAL_DEMO",
            technique_id="qizheng",
        )
        co_entry = next(
            e for e in res["pack"]["entries"]
            if e["subject_entity_id"] == "co_qizheng_000001"
        )
        self.assertEqual(co_entry["assertion_ids"], ["as_qizheng_000003"])
        self.assertIn("as_qizheng_000004", res["assertion_without_subject"])

    def test_entry_requires_at_least_one_assertion(self):
        knowledge = self._snapshot_knowledge()
        # 无主体的格局（assertion_ids 为空）→ 不生成 entry
        knowledge["patterns"].append(
            {
                "pattern_id": "pat_qizheng_000003",
                "name": "示例格局三",
                "assertion_ids": [],
                "school_view_ids": [],
                "recognition_rule_status": "not_captured",
                "concept_id": None,
            }
        )
        res = packs.build_knowledge_data_pack(
            snapshot_knowledge=knowledge,
            entry_id_allocation=self._allocation(),
            release_id="rel_" + "c" * 32,
            consumption_level="INTERNAL_DEMO",
            technique_id="qizheng",
        )
        subject_ids = {e["subject_entity_id"] for e in res["pack"]["entries"]}
        self.assertNotIn("pat_qizheng_000003", subject_ids)
        self.assertIn(
            "pat_qizheng_000003", res["subjects_without_entry"]
        )
        # 发号表里给缺号主体也必须抛错（不得临时生成）
        with self.assertRaises(SchemaViolation) as ctx:
            packs.build_knowledge_data_pack(
                snapshot_knowledge=knowledge,
                entry_id_allocation={},
                release_id="rel_" + "c" * 32,
                consumption_level="INTERNAL_DEMO",
                technique_id="qizheng",
            )
        self.assertEqual(ctx.exception.code, "ID_001")

    def test_pack_builder_never_calls_uuid(self):
        knowledge = self._snapshot_knowledge()
        with unittest.mock.patch(
            "uuid.uuid4", side_effect=AssertionError("纯函数层禁止调用 uuid")
        ):
            res = packs.build_knowledge_data_pack(
                snapshot_knowledge=knowledge,
                entry_id_allocation=self._allocation(),
                release_id="rel_" + "c" * 32,
                consumption_level="INTERNAL_DEMO",
                technique_id="qizheng",
            )
        self.assertTrue(res["pack"]["entries"])

    def test_missing_allocation_raises(self):
        knowledge = self._snapshot_knowledge()
        with self.assertRaises(SchemaViolation) as ctx:
            packs.build_knowledge_data_pack(
                snapshot_knowledge=knowledge,
                entry_id_allocation={"pat_qizheng_000001": "ent_" + "a" * 32},
                release_id="rel_" + "c" * 32,
                consumption_level="INTERNAL_DEMO",
                technique_id="qizheng",
            )
        self.assertEqual(ctx.exception.code, "ID_001")
        self.assertIn("co_qizheng_000001", str(ctx.exception))

    def test_allocate_entry_ids_reuses_previous_and_issues_uuid4_for_new(self):
        from pipeline.dataset_compiler import entry_ids

        previous = {"pat_qizheng_000001": "ent_" + "a" * 32}
        res = entry_ids.allocate_entry_ids(
            previous_allocation=previous,
            subject_entity_ids=["pat_qizheng_000001", "co_qizheng_000001"],
            release_id="rel_" + "c" * 32,
        )
        # 旧号沿用
        self.assertEqual(res["pat_qizheng_000001"], "ent_" + "a" * 32)
        # 新号 UUIDv4：ent_ + 32hex，且版本位为 4
        new_id = res["co_qizheng_000001"]
        self.assertRegex(new_id, r"^ent_[0-9a-f]{32}$")
        self.assertEqual(new_id[16], "4")  # uuid4 版本位（ent_ 后第 13 个 hex）
        # 不修改入参
        self.assertEqual(previous, {"pat_qizheng_000001": "ent_" + "a" * 32})

    def test_knowledge_data_pack_bytes_deterministic_given_allocation(self):
        knowledge = self._snapshot_knowledge()
        kwargs = dict(
            snapshot_knowledge=knowledge,
            entry_id_allocation=self._allocation(),
            release_id="rel_" + "c" * 32,
            consumption_level="INTERNAL_DEMO",
            technique_id="qizheng",
        )
        first = packs.build_knowledge_data_pack(**kwargs)
        second = packs.build_knowledge_data_pack(**kwargs)
        self.assertEqual(first["bytes"], second["bytes"])
        self.assertEqual(first["sha256"], second["sha256"])
        # 内部键序确定：entries 按 subject_entity_id 升序
        subjects = [e["subject_entity_id"] for e in first["pack"]["entries"]]
        self.assertEqual(subjects, sorted(subjects))

    def test_evidence_link_offsets_absolute_per_i11(self):
        """EvidenceLink 前三段材料：偏移取 Snapshot evidence 的绝对偏移（I-11）逐字透传。"""
        knowledge = self._snapshot_knowledge()
        res = packs.build_knowledge_data_pack(
            snapshot_knowledge=knowledge,
            entry_id_allocation=self._allocation(),
            release_id="rel_" + "c" * 32,
            consumption_level="INTERNAL_DEMO",
            technique_id="qizheng",
        )
        chains = res["evidence_chains"]
        self.assertEqual(len(chains), 2)
        for chain in chains:
            self.assertEqual(
                set(chain.keys()), {"entry_id", "assertion_id", "evidence_link"}
            )
            link = chain["evidence_link"]
            # evidence 中的偏移即为绝对偏移，逐字进入 EvidenceLink（不加减）
            self.assertEqual(
                (link["start_offset"], link["end_offset"]),
                (10, 20) if chain["assertion_id"] == "as_qizheng_000001" else (30, 40),
            )
            self.assertTrue(chain["evidence_link"]["quote_sha256"])
            self.assertEqual(
                link["source_span_id"],
                "ss_synth_ed01_o0000010"
                if chain["assertion_id"] == "as_qizheng_000001"
                else "ss_synth_ed01_o0000030",
            )


class MiscPacksTests(unittest.TestCase):
    """png_size 与模块纯函数性。"""

    def test_png_size_and_non_png_SCH_002(self):
        data = (
            b"\x89PNG\r\n\x1a\n"
            + (13).to_bytes(4, "big")
            + b"IHDR"
            + struct.pack(">II", 1203, 1654)
        )
        self.assertEqual(packs.png_size(data), (1203, 1654))
        with self.assertRaises(SchemaViolation) as ctx:
            packs.png_size(b"not a png")
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_packs_module_pure(self):
        packs_path = os.path.join(_REPO_ROOT, "pipeline", "dataset_compiler", "packs.py")
        with open(packs_path, encoding="utf-8") as handle:
            source = handle.read()
        for token in ("open(", "Path(", "sqlite3", "service", "time.", "random", "uuid"):
            self.assertNotIn(token, source, msg="packs.py 不应含 %r" % token)


if __name__ == "__main__":
    unittest.main()

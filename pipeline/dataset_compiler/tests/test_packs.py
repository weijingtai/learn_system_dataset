"""ACT impl-04/01：纯函数子包编译器的测试。

测试可读 fixture 文件作为纯函数输入（manifest.yaml、pages/*.json、spans.yaml、
anomalies.yaml）；asset_records / ocr_page_revision_ids 由测试按契约从清单派生。
"""

import copy
import hashlib
import json
import os
import struct
import unittest

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

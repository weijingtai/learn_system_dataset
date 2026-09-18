"""ACT impl-04/02：独立发布 Gate evaluate_publication 的测试。

金标输入由测试调用 act/01 的 packs 纯函数在 fixture 上构造；每个篡改用例
深拷贝金标、篡改一处，断言指定检查 ``ok is False`` 且 ``passed is False``。
Gate 自身不得 import packs/canonical/levels/step（防同错同过）。
"""

import ast
import copy
import json
import os
import unittest

import yaml

from pipeline.dataset_compiler import gate, packs

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_TESTS_DIR, os.pardir, os.pardir, os.pardir))
_FIXTURE_DIR = os.path.join(_REPO_ROOT, "pipeline", "corpus", "_fixture", "mini_ed01")

EXCLUDED_PAGES = {"page_002": "known_unrecognizable"}
_DRAFT_VERSIONS = {
    "evidence_map_pack": "0.1.0-draft",
    "release_manifest": "0.1.0-draft",
    "source_asset_pack": "0.1.0-draft",
}


def _load_yaml(name):
    with open(os.path.join(_FIXTURE_DIR, name), encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_json(name):
    with open(os.path.join(_FIXTURE_DIR, name), encoding="utf-8") as handle:
        return json.load(handle)


def _admission():
    return {
        "consumption_level": "INTERNAL_DEMO",
        "source_release": "dev",
        "admitted": True,
        "unmet": [],
        "watermark_required": True,
        "isolation": "internal_only",
    }


def _golden():
    """在 fixture 上构造 Gate 的全部金标参数。"""
    manifest = _load_yaml("manifest.yaml")
    spans_doc = _load_yaml("spans.yaml")
    page_docs = {
        page: _load_json("pages/%s.json" % page)
        for page in ("page_001", "page_002", "page_003")
    }
    ocr_page_revision_ids = {
        "page_001": "rev_%032x" % 101,
        "page_002": "rev_%032x" % 102,
        "page_003": "rev_%032x" % 103,
    }
    asset_records = {
        item["page"]: {
            "artifact_revision_id": "rev_%032x" % (index + 1),
            "sha256": item["sha256"],
            "size": 0,
            "width": item["width"],
            "height": item["height"],
        }
        for index, item in enumerate(manifest["source_assets"])
    }
    frozen_inputs = [
        {
            "artifact_revision_id": "rev_%032x" % 201,
            "artifact_type": "stage_package",
            "sha256": "1" * 64,
        },
        {
            "artifact_revision_id": "rev_%032x" % 202,
            "artifact_type": "corpus_spans",
            "sha256": "2" * 64,
        },
        {
            "artifact_revision_id": "rev_%032x" % 203,
            "artifact_type": "source_manifest",
            "sha256": "3" * 64,
        },
        {
            "artifact_revision_id": "rev_%032x" % 204,
            "artifact_type": "ocr_page_set",
            "sha256": "4" * 64,
        },
    ]
    source_asset_pack = packs.build_source_asset_pack(
        manifest=manifest, asset_records=asset_records
    )
    evidence_map_pack = packs.build_evidence_map_pack(
        spans_doc=spans_doc,
        page_docs=page_docs,
        ocr_page_revision_ids=ocr_page_revision_ids,
        source_asset_pack=source_asset_pack["pack"],
        excluded_pages=EXCLUDED_PAGES,
    )
    release_manifest = packs.build_release_manifest(
        release_id="rel_%032x" % 9,
        admission=_admission(),
        release_scope={"edition_part_ids": [manifest["edition_part"]["artifact_id"]]},
        technique_id="qizheng",
        packs=[
            {
                "pack_type": "source_asset_pack",
                "artifact_revision_id": "rev_%032x" % 211,
                "sha256": source_asset_pack["sha256"],
                "size": len(source_asset_pack["bytes"]),
            },
            {
                "pack_type": "evidence_map_pack",
                "artifact_revision_id": "rev_%032x" % 212,
                "sha256": evidence_map_pack["sha256"],
                "size": len(evidence_map_pack["bytes"]),
            },
        ],
        input_reconciliation=[
            {
                "artifact_revision_id": item["artifact_revision_id"],
                "artifact_type": item["artifact_type"],
                "sha256": item["sha256"],
            }
            for item in frozen_inputs
        ],
        schema_versions=_DRAFT_VERSIONS,
        min_app_version=None,
        known_defects=packs.compute_known_defects(
            evidence_map_pack=evidence_map_pack["pack"],
            m3_gate_profile="structural_only",
            rights_status=manifest["rights_status"],
        ),
        watermark_text=packs.INTERNAL_DEMO_WATERMARK,
    )
    return {
        "manifest": manifest,
        "spans_doc": spans_doc,
        "page_docs": page_docs,
        "ocr_page_revision_ids": ocr_page_revision_ids,
        "asset_records": asset_records,
        "excluded_pages": copy.deepcopy(EXCLUDED_PAGES),
        "m3_gate_profile": "structural_only",
        "frozen_inputs": frozen_inputs,
        "source_asset_pack": source_asset_pack["pack"],
        "evidence_map_pack": evidence_map_pack["pack"],
        "release_manifest": release_manifest["manifest"],
        "pack_bytes": {
            "source_asset_pack": source_asset_pack["bytes"],
            "evidence_map_pack": evidence_map_pack["bytes"],
        },
        "consumption_level": "INTERNAL_DEMO",
    }


def _evaluate(base, **overrides):
    kwargs = dict(base)
    kwargs.update(overrides)
    return gate.evaluate_publication(**kwargs)


from pipeline.dataset_compiler.canonical import quote_sha256 as _quote_sha256  # noqa: E402


class GateGoldenTests(unittest.TestCase):
    """金标：14 项实评 ok True + 9 项 not_applicable（ACT 12 闭集扩为 23）；passed True。"""

    def test_fixture_all_checks_pass_knowledge_not_evaluated(self):
        out = _evaluate(_golden())
        checks = out["checks"]
        self.assertEqual(len(checks), 23)
        not_applicable = {
            "chain_closure",
            "no_assertion_bypass",
            "quote_hash_integrity",
            "content_status_admission",
            "graph_projection_closure",
            "offset_anchor_continuity",
            "patch_reversible",
            "raw_text_binding",
            "sanitization_disclosure",
        }
        for name, check in checks.items():
            if name == "knowledge_chain":
                continue
            if name in not_applicable:
                self.assertIsNone(check["ok"])
                self.assertEqual(check["status"], "not_applicable")
            else:
                self.assertTrue(check["ok"], msg="%s 未通过: %s" % (name, check["detail"]))
        self.assertIsNone(checks["knowledge_chain"]["ok"])
        self.assertEqual(checks["knowledge_chain"]["status"], "not_evaluated")
        self.assertTrue(out["passed"])
        self.assertEqual(out["failed_checks"], [])
        self.assertEqual(out["knowledge_chain"], "not_evaluated")


class GateIndependenceTests(unittest.TestCase):
    """Gate 不得 import packs/canonical/levels/step。"""

    def test_gate_does_not_import_packs_canonical_levels_step(self):
        gate_path = os.path.join(_REPO_ROOT, "pipeline", "dataset_compiler", "gate.py")
        with open(gate_path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), filename=gate_path)
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.append(node.module)
                for alias in node.names:
                    modules.append(
                        "%s.%s" % (node.module, alias.name) if node.module else alias.name
                    )
        for module in modules:
            for token in ("packs", "canonical", "levels", "step"):
                self.assertNotIn(token, module, msg="gate.py 不应 import %r" % module)


class GateTamperTests(unittest.TestCase):
    """逐项篡改：指定检查失败且整体 passed 为 False。"""

    def _assert_check_fails(self, out, name):
        self.assertFalse(out["checks"][name]["ok"], msg="%s 应失败" % name)
        self.assertFalse(out["passed"])

    def test_drop_entry_fails_span_identity(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"].pop("ss_sanche_ed01_p0003_s01")
        evidence["span_count"] = len(evidence["entries"])
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "span_identity"
        )

    def test_rekey_to_other_page_id_fails_span_identity(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0003_s01"] = evidence["entries"].pop(
            "ss_sanche_ed01_p0001_s01"
        )
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "span_identity"
        )

    def test_legacy_seq_key_collapse_fails_span_identity(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        collapsed = {}
        for span in base["spans_doc"]["spans"]:
            seq = int(span["span_id"].rsplit("_s", 1)[1])
            collapsed[(base["spans_doc"]["source_id"], seq)] = evidence["entries"][
                span["span_id"]
            ]
        evidence["entries"] = collapsed
        evidence["span_count"] = len(collapsed)
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "span_identity"
        )

    def test_entry_page_changed_fails_span_page_binding(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"]["page"] = "page_003"
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "span_page_binding"
        )

    def test_text_changed_fails_text_offsets(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"]["text"] = "改动文本"
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "text_offsets"
        )

    def test_quote_hash_changed_fails_text_offsets(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"]["quote_sha256"] = "0" * 64
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "text_offsets"
        )

    def test_glyph_box_changed_fails_glyph_anchor_closure(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"]["glyphs"][0]["box"]["x"] += 1.0
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "glyph_anchor_closure"
        )

    def test_glyph_char_changed_fails_glyph_anchor_closure(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"]["glyphs"][0]["char"] = "錯"
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "glyph_anchor_closure"
        )

    def test_bbox_changed_fails_glyph_anchor_closure(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"]["bbox"]["x"] += 1.0
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "glyph_anchor_closure"
        )

    def test_highlight_level_forged_glyph_fails_highlight_level(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        entry = evidence["entries"]["ss_sanche_ed01_p0001_s03"]
        entry["highlight_level"] = "glyph"
        entry["glyph_text_equal"] = True
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "highlight_level"
        )

    def test_ocr_page_rev_swapped_fails_ocr_page_binding(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"][
            "ocr_page_artifact_revision_id"
        ] = "rev_%032x" % 999
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "ocr_page_binding"
        )

    def test_image_sha_changed_fails_source_asset_binding(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"]["image_sha256"] = "0" * 64
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "source_asset_binding"
        )

    def test_asset_pack_sha_changed_fails_source_asset_binding(self):
        base = _golden()
        asset_pack = copy.deepcopy(base["source_asset_pack"])
        asset_pack["pages"][0]["sha256"] = "0" * 64
        self._assert_check_fails(
            _evaluate(base, source_asset_pack=asset_pack), "source_asset_binding"
        )

    def test_frame_changed_fails_coordinate_frame(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"]["frame"]["width"] += 1
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "coordinate_frame"
        )

    def test_page_index_missing_span_fails_reverse_index(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["page_index"]["page_001"].pop()
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "reverse_index"
        )

    def test_excluded_page_given_span_fails_reverse_index(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["page_index"]["page_002"] = ["ss_sanche_ed01_p0001_s01"]
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "reverse_index"
        )

    def test_pack_bytes_tampered_fails_release_manifest_hashes(self):
        base = _golden()
        pack_bytes = dict(base["pack_bytes"])
        pack_bytes["evidence_map_pack"] = b"tampered"
        self._assert_check_fails(
            _evaluate(base, pack_bytes=pack_bytes), "release_manifest_hashes"
        )

    def test_canonical_hash_tampered_fails_release_manifest_hashes(self):
        base = _golden()
        release = copy.deepcopy(base["release_manifest"])
        release["canonical_hash"] = "0" * 64
        self._assert_check_fails(
            _evaluate(base, release_manifest=release), "release_manifest_hashes"
        )

    def test_input_reconciliation_missing_one_fails(self):
        base = _golden()
        frozen = list(base["frozen_inputs"])[:-1]
        self._assert_check_fails(
            _evaluate(base, frozen_inputs=frozen), "input_reconciliation"
        )

    def test_manifest_level_dev_search_fails_consumption_level(self):
        base = _golden()
        release = copy.deepcopy(base["release_manifest"])
        release["consumption_level"] = "DEV_SEARCH"
        self._assert_check_fails(
            _evaluate(base, release_manifest=release), "consumption_level"
        )

    def test_source_verified_not_release_fails_consumption_level(self):
        base = _golden()
        spans_doc = copy.deepcopy(base["spans_doc"])
        spans_doc["content_status"] = "source_verified"
        release = copy.deepcopy(base["release_manifest"])
        release["source_release"] = "release"
        self._assert_check_fails(
            _evaluate(base, spans_doc=spans_doc, release_manifest=release),
            "consumption_level",
        )

    def test_authoritative_true_fails_consumption_level(self):
        base = _golden()
        release = copy.deepcopy(base["release_manifest"])
        release["authoritative"] = True
        self._assert_check_fails(
            _evaluate(base, release_manifest=release), "consumption_level"
        )

    def test_entry_watermark_false_fails_watermark_disclosure(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["entries"]["ss_sanche_ed01_p0001_s01"]["watermark"] = False
        self._assert_check_fails(
            _evaluate(base, evidence_map_pack=evidence), "watermark_disclosure"
        )

    def test_known_defect_dropped_fails_watermark_disclosure(self):
        base = _golden()
        release = copy.deepcopy(base["release_manifest"])
        release["known_defects"] = [
            item
            for item in release["known_defects"]
            if item["code"] != "glyph_text_mismatch"
        ]
        self._assert_check_fails(
            _evaluate(base, release_manifest=release), "watermark_disclosure"
        )

    def test_knowledge_chain_compiled_claim_fails(self):
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["knowledge_chain"] = "compiled"
        out = _evaluate(base, evidence_map_pack=evidence)
        self.assertFalse(out["checks"]["knowledge_chain"]["ok"])
        self.assertFalse(out["passed"])

    def test_check_exception_becomes_fail_not_raise(self):
        base = _golden()
        page_docs = {
            page: doc
            for page, doc in base["page_docs"].items()
            if page != "page_003"
        }
        out = _evaluate(base, page_docs=page_docs)
        self.assertFalse(out["checks"]["glyph_anchor_closure"]["ok"])
        self.assertFalse(out["passed"])


class GateClosedSetTests(unittest.TestCase):
    """ACT 12：_CHECK_NAMES 23 项单一闭集 + not_applicable（第 107 条 Q-M8-08）。"""

    M8_CHECK_NAMES = (
        "span_identity",
        "span_page_binding",
        "text_offsets",
        "glyph_anchor_closure",
        "highlight_level",
        "ocr_page_binding",
        "source_asset_binding",
        "coordinate_frame",
        "reverse_index",
        "release_manifest_hashes",
        "input_reconciliation",
        "consumption_level",
        "watermark_disclosure",
        "knowledge_chain",
        "chain_closure",
        "no_assertion_bypass",
        "quote_hash_integrity",
        "content_status_admission",
        "offset_anchor_continuity",
        "patch_reversible",
        "raw_text_binding",
        "sanitization_disclosure",
        "graph_projection_closure",
    )

    def test_gate_check_names_match_registered_closed_set(self):
        self.assertEqual(gate._CHECK_NAMES, self.M8_CHECK_NAMES)

    def test_gate_glyphbox_results_unchanged(self):
        """OCR 既有 Gate 结果逐字不变护栏（14 项实评全过、knowledge_chain 过渡项不变）。"""
        out = _evaluate(_golden())
        checks = out["checks"]
        self.assertEqual(len(checks), 23)
        expected_statuses = {
            "chain_closure": "not_applicable",
            "no_assertion_bypass": "not_applicable",
            "quote_hash_integrity": "not_applicable",
            "content_status_admission": "not_applicable",
            "graph_projection_closure": "not_applicable",
            "offset_anchor_continuity": "not_applicable",
            "patch_reversible": "not_applicable",
            "raw_text_binding": "not_applicable",
            "sanitization_disclosure": "not_applicable",
        }
        for name in self.M8_CHECK_NAMES:
            check = checks[name]
            if name in expected_statuses:
                self.assertEqual(
                    check["status"],
                    expected_statuses[name],
                    msg="%s 应为 not_applicable" % name,
                )
                self.assertNotEqual(check["status"], "ok")
            elif name == "knowledge_chain":
                self.assertIsNone(check["ok"])
            else:
                self.assertTrue(
                    check["ok"], msg="%s 未通过: %s" % (name, check["detail"])
                )
        self.assertIsNone(checks["knowledge_chain"]["ok"])
        self.assertEqual(checks["knowledge_chain"]["status"], "not_evaluated")
        self.assertTrue(out["passed"])
        self.assertEqual(out["failed_checks"], [])

    def test_gate_not_applicable_is_not_ok(self):
        """not_applicable 不得冒充 ok：ok 非 True 不计入 passed；污染 ok:True 被检测。"""
        out = _evaluate(_golden())
        na = out["checks"]["chain_closure"]
        self.assertEqual(na["status"], "not_applicable")
        self.assertIsNot(na["ok"], True)
        # 篡改：把 not_applicable 改成 ok True → 自检必须报失败（passed 翻转）
        base = _golden()
        out2 = _evaluate(base, checks_override={"chain_closure": {"ok": True}})
        self.assertFalse(out2["passed"])

    def test_gate_knowledge_chain_compiled_evaluates_chain_closure(self):
        """knowledge_chain 已编译时：知识链五项转实评；此处缺 assertion → chain_closure 失败。"""
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["knowledge_chain"] = "compiled"
        knowledge = {
            "patterns": [
                {
                    "pattern_id": "pat_qizheng_000001",
                    "name": "示例格局",
                    "assertion_ids": ["as_qizheng_999999"],
                    "school_view_ids": [],
                }
            ],
            "concepts": [],
            "assertions": [
                {
                    "assertion_id": "as_qizheng_000001",
                    "proposition": "示例断言",
                    "subject_entity_id": "pat_qizheng_000001",
                    "evidence": [],
                    "school_view_ids": [],
                    "content_status": "machine_extracted",
                }
            ],
            "school_views": [],
            "conflict_groups": [],
        }
        release = copy.deepcopy(base["release_manifest"])
        out = _evaluate(
            base,
            evidence_map_pack=evidence,
            snapshot_knowledge=knowledge,
            release_manifest=release,
        )
        self.assertFalse(out["checks"]["chain_closure"]["ok"])
        self.assertEqual(out["checks"]["chain_closure"]["status"], "evaluated")
        self.assertFalse(out["passed"])
    def test_gate_knowledge_chain_compiled_passes_on_consistent_snapshot(self):
        """知识链已编译且一致时：五项实评全过、过渡项 knowledge_chain 转为 evaluated ok。"""
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["knowledge_chain"] = "compiled"
        knowledge = {
            "patterns": [
                {
                    "pattern_id": "pat_qizheng_000001",
                    "name": "示例格局",
                    "assertion_ids": ["as_qizheng_000001"],
                    "school_view_ids": [],
                }
            ],
            "concepts": [],
            "assertions": [
                {
                    "assertion_id": "as_qizheng_000001",
                    "proposition": "示例断言",
                    "subject_entity_id": "pat_qizheng_000001",
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0001_s04",
                            "start_offset": 0,
                            "end_offset": 6,
                            "quote_sha256": packs.quote_sha256(
                                base["spans_doc"]["spans"][3]["text"][0:6]
                            ),
                        }
                    ],
                    "school_view_ids": [],
                    "content_status": "machine_extracted",
                }
            ],
            "school_views": [],
            "conflict_groups": [],
        }
        graph = {
            "schema_version": "0.1.0-draft",
            "release_id": base["release_manifest"]["release_id"],
            "canonical_hash": base["release_manifest"]["canonical_hash"],
            "consumption_level": "INTERNAL_DEMO",
            "nodes": [],
            "edges": [],
            "node_count": 0,
            "edge_count": 0,
        }
        out = _evaluate(
            base,
            evidence_map_pack=evidence,
            snapshot_knowledge=knowledge,
            graph_projection_pack=graph,
        )
        for name in (
            "chain_closure",
            "no_assertion_bypass",
            "quote_hash_integrity",
            "content_status_admission",
            "graph_projection_closure",
            "knowledge_chain",
        ):
            check = out["checks"][name]
            self.assertTrue(
                check["ok"], msg="%s 应通过: %s" % (name, check["detail"])
            )
            self.assertEqual(check["status"], "evaluated")
        # 整包还有 release_manifest_hashes 等无关失败（pack 未重封），不断言 passed

    def test_gate_rejects_evidence_link_bypassing_assertion(self):
        """assertion 无任何显式引用（绕过 Assertion）→ no_assertion_bypass 失败。"""
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["knowledge_chain"] = "compiled"
        knowledge = {
            "patterns": [],
            "concepts": [],
            "assertions": [
                {
                    "assertion_id": "as_qizheng_000001",
                    "proposition": "示例断言",
                    "subject_entity_id": None,
                    "evidence": [
                        {"source_span_id": "ss_sanche_ed01_p0001_s01"}
                    ],
                    "school_view_ids": [],
                    "content_status": "machine_extracted",
                }
            ],
            "school_views": [],
            "conflict_groups": [],
        }
        out = _evaluate(
            base,
            evidence_map_pack=evidence,
            snapshot_knowledge=knowledge,
        )
        self.assertFalse(out["checks"]["no_assertion_bypass"]["ok"])
        self.assertFalse(out["passed"])

    def test_gate_quote_hash_integrity_detects_tamper(self):
        """quote_sha256 与正文重算不符 → quote_hash_integrity 失败。"""
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["knowledge_chain"] = "compiled"
        knowledge = {
            "patterns": [
                {
                    "pattern_id": "pat_qizheng_000001",
                    "name": "示例格局",
                    "assertion_ids": ["as_qizheng_000001"],
                    "school_view_ids": [],
                }
            ],
            "concepts": [],
            "assertions": [
                {
                    "assertion_id": "as_qizheng_000001",
                    "proposition": "示例断言",
                    "subject_entity_id": "pat_qizheng_000001",
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0001_s01",
                            "start_offset": 10,
                            "end_offset": 20,
                            "quote_sha256": "0" * 64,
                        }
                    ],
                    "school_view_ids": [],
                    "content_status": "machine_extracted",
                }
            ],
            "school_views": [],
            "conflict_groups": [],
        }
        out = _evaluate(
            base,
            evidence_map_pack=evidence,
            snapshot_knowledge=knowledge,
        )
        self.assertFalse(out["checks"]["quote_hash_integrity"]["ok"])
        self.assertFalse(out["passed"])

    def test_gate_graph_projection_closure_detects_hash_mismatch(self):
        """graph_projection.canonical_hash 与清单不符 → graph_projection_closure 失败。"""
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["knowledge_chain"] = "compiled"
        gp = {
            "schema_version": "0.1.0-draft",
            "release_id": base["release_manifest"]["release_id"],
            "canonical_hash": "0" * 64,
            "consumption_level": "INTERNAL_DEMO",
            "nodes": [],
            "edges": [],
            "node_count": 0,
            "edge_count": 0,
        }
        out = _evaluate(
            base,
            evidence_map_pack=evidence,
            graph_projection_pack=gp,
        )
        self.assertFalse(out["checks"]["graph_projection_closure"]["ok"])
        self.assertFalse(out["passed"])

    def test_gate_offset_raw_text_binding_detects_sha_mismatch(self):
        """offset 档：raw_text 清单 sha 与 SourceAsset sha 不符 → raw_text_binding 失败。"""
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["evidence_level"] = "offset_level"
        out = _evaluate(
            base,
            evidence_map_pack=evidence,
            raw_text_binding={"sha256": "0" * 64},
        )
        self.assertFalse(out["checks"]["raw_text_binding"]["ok"])
        self.assertFalse(out["passed"])

    def test_gate_sanitization_disclosure_requires_known_unresolvable_finding(self):
        """清洗文本含禁用字符但 M2 发现无 known_unresolvable → sanitization_disclosure 失败。"""
        base = _golden()
        evidence = copy.deepcopy(base["evidence_map_pack"])
        evidence["evidence_level"] = "offset_level"
        out = _evaluate(
            base,
            evidence_map_pack=evidence,
            raw_text_binding={"sha256": base["asset_records"]["page_001"]["sha256"]},
            raw_text={"text": "示例文本含替换字符?末尾"},
            sanitization_report={
                "findings": [
                    {
                        "finding_id": "replacement_char@10-11",
                        "kind": "replacement_char",
                        "raw_start": 10,
                        "raw_end": 11,
                        "raw_excerpt": "?",
                        "terminal_state": "processed",
                    }
                ]
            },
        )
        self.assertFalse(out["checks"]["sanitization_disclosure"]["ok"])
        self.assertFalse(out["passed"])


if __name__ == "__main__":
    unittest.main()

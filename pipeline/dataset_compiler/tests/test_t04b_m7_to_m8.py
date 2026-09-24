"""T04B / T05f: M7 Snapshot -> M8 compile KnowledgeDataPack, GraphProjectionPack, and evidence chains.

测试先写（Red 阶段）：断言 run_m8 以 M7 Snapshot 为输入时，
实际产出 KnowledgeDataPack、GraphProjectionPack 与证据链并封存进 Ledger；
发布包包含三样东西，knowledge_chain=compiled，且 R15 全栈用例通过。
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
import yaml

from pipeline.assembly.fixture_seed import seed_release_package
from pipeline.assembly.step import run_m7
from pipeline.dataset_compiler import packs
from pipeline.dataset_compiler.step import run_m8
from pipeline.dataset_compiler.acceptance import _evaluate_publication, _build_context
from pipeline.dataset_compiler.tests._ledger_helpers import (
    REPO_ROOT,
    assets_available,
    prepare_m8_ready,
)
from pipeline.ledger.service import LedgerService

FIXTURE_M7 = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"
FIXTURE_M8 = REPO_ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01"


class TestM7ToM8Compilation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="t04b-r15-")
        self.ledger_dir = Path(self._tmp) / "ledger"
        self.service = LedgerService(self.ledger_dir)

    def tearDown(self):
        self.service.close()
        shutil.rmtree(self._tmp, True)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_run_m8_compiles_knowledge_graph_and_evidence_chains(self):
        """测试 run_m8 以 M7 Snapshot 为输入，产出三样子包，knowledge_chain=compiled。"""
        # 1. 准备 M1-M3 上游
        prepared = prepare_m8_ready(self.service)
        edition_part_id = prepared["edition_part_id"]

        # 2. 灌入 M6 视图并跑真 M7 汇编产出 Snapshot
        manifest = yaml.safe_load((FIXTURE_M7 / "manifest.yaml").read_bytes())
        seeded = seed_release_package(self.service, FIXTURE_M7)
        ed01 = manifest["editions"][0]
        first_m6 = seeded["editions"][ed01["edition_key"]]
        res_m7 = run_m7(
            self.service,
            edition_part_id,
            technique_id="qizheng",
            reviewed_package_revision_ids=[first_m6["m6_package_revision_id"]],
            id_range=manifest["id_range"],
        )
        self.assertEqual(res_m7["status"], "succeeded")
        self.assertIsNotNone(res_m7["snapshot_revision_id"])

        # 3. 执行 M8 编译
        res_m8 = run_m8(
            self.service,
            edition_part_id,
            consumption_level="INTERNAL_DEMO",
        )
        self.assertEqual(res_m8.get("status"), "succeeded", "run_m8 应该成功: %r" % res_m8.get("reason"))

        # 4. 验证发布包与封存产物
        m8_step_run_id = res_m8["step_run_id"]
        rows = self.service.list_step_run_revisions(m8_step_run_id, artifact_type="stage_package", status="sealed")
        self.assertEqual(len(rows), 1)
        m8_pkg = json.loads(self.service.read_object(self.service.get_revision(rows[0]["artifact_revision_id"])["sha256"]))
        payload = m8_pkg["payload"]
        self.assertEqual(payload["knowledge_chain"], "compiled")

        pub_rev = self.service.get_revision(payload["publication_package_revision_id"])
        pub = json.loads(self.service.read_object(pub_rev["sha256"]))
        packs_dict = pub["packs"]

        # 必须包含三样东西
        self.assertIn("knowledge_data_pack", packs_dict)
        self.assertIn("graph_projection_pack", packs_dict)
        self.assertIn("evidence_chain", packs_dict)

        # 检查封存的各修订
        kd_doc = json.loads(self.service.read_object(self.service.get_revision(packs_dict["knowledge_data_pack"])["sha256"]))
        self.assertEqual(kd_doc["pack_type"], "knowledge_data_pack")
        self.assertTrue(len(kd_doc["entries"]) > 0)

        gp_doc = json.loads(self.service.read_object(self.service.get_revision(packs_dict["graph_projection_pack"])["sha256"]))
        self.assertTrue(len(gp_doc["nodes"]) > 0)
        self.assertTrue(len(gp_doc["edges"]) > 0)

        ev_doc = json.loads(self.service.read_object(self.service.get_revision(packs_dict["evidence_chain"])["sha256"]))
        self.assertTrue(len(ev_doc["chains"]) > 0)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_r15_full_stack_m7_to_m8_acceptance(self):
        """R15：全栈真实形状输入走通，并通过验收的内容校验。"""
        # 1. 准备 M1-M3 上游
        prepared = prepare_m8_ready(self.service)
        edition_part_id = prepared["edition_part_id"]

        # 2. 灌入 M6 视图并跑 M7
        manifest = yaml.safe_load((FIXTURE_M7 / "manifest.yaml").read_bytes())
        seeded = seed_release_package(self.service, FIXTURE_M7)
        ed01 = manifest["editions"][0]
        first_m6 = seeded["editions"][ed01["edition_key"]]
        res_m7 = run_m7(
            self.service,
            edition_part_id,
            technique_id="qizheng",
            reviewed_package_revision_ids=[first_m6["m6_package_revision_id"]],
            id_range=manifest["id_range"],
        )
        self.assertEqual(res_m7["status"], "succeeded")

        # 3. 跑 M8
        res_m8 = run_m8(
            self.service,
            edition_part_id,
            consumption_level="INTERNAL_DEMO",
        )
        self.assertEqual(res_m8.get("status"), "succeeded")

        # 4. 跑 M8 验收判定
        ctx = _build_context(self.service, edition_part_id, FIXTURE_M8, FIXTURE_M8, "glyphbox_level")
        results = _evaluate_publication(ctx)
        result_map = {name: (status, detail) for name, status, detail in results}

        self.assertEqual(result_map["run_succeeded"][0], "PASS")
        self.assertEqual(result_map["knowledge_chain"][0], "PASS", result_map["knowledge_chain"][1])
        self.assertEqual(result_map["graph_projection"][0], "PASS", result_map["graph_projection"][1])
        self.assertEqual(result_map["identity_migration"][0], "BLOCKED")


# ---------------------------------------------------------------------------
# T04B 第 2 项：run_m8 以 M7 Snapshot 为输入，实际调用三个构建函数并逐一封存。
# 这些用例只看 Ledger 事实（封存了什么、彼此是否同源），不依赖发布 Gate 是否放行。
# ---------------------------------------------------------------------------
import hashlib  # noqa: E402
import re  # noqa: E402

from pipeline.dataset_compiler.tests.test_inputs import seed_m7_snapshot  # noqa: E402
from pipeline.dataset_compiler.tests.test_step import ElectronicTextStepBase  # noqa: E402

_ENT_UUID4 = re.compile(r"^ent_[0-9a-f]{12}4[0-9a-f]{19}$")


def _read_json(service, revision_id):
    return json.loads(service.read_object(service.get_revision(revision_id)["sha256"]).decode("utf-8"))


def _read_any(service, revision_id):
    raw = service.read_object(service.get_revision(revision_id)["sha256"]).decode("utf-8")
    try:
        return json.loads(raw)
    except ValueError:
        return yaml.safe_load(raw)


def _sealed(service, step_run_id, artifact_type):
    return [
        row["artifact_revision_id"]
        for row in service.list_step_run_revisions(
            step_run_id, artifact_type=artifact_type, status="sealed"
        )
    ]


def _knowledge_outputs(test, service, step_run_id):
    """取 m8 StepRun 封存的发号表、KnowledgeDataPack、证据链文档、GraphProjectionPack（各恰 1 个）。"""
    allocation = _sealed(service, step_run_id, "entry_id_allocation")
    knowledge = _sealed(service, step_run_id, "knowledge_data_pack")
    graph = _sealed(service, step_run_id, "graph_projection_pack")
    chain_docs = [
        revision_id
        for revision_id in _sealed(service, step_run_id, "evidence_map_pack")
        if "chains" in _read_json(service, revision_id)
    ]
    test.assertEqual(len(allocation), 1, "entry_id_allocation 须恰封存 1 个")
    test.assertEqual(len(knowledge), 1, "knowledge_data_pack 须恰封存 1 个")
    test.assertEqual(len(graph), 1, "graph_projection_pack 须恰封存 1 个")
    test.assertEqual(len(chain_docs), 1, "七段证据链文档（evidence_map_pack，INTERFACES §3.10）须恰封存 1 个")
    return {
        "allocation": _read_json(service, allocation[0]),
        "knowledge": _read_json(service, knowledge[0]),
        "graph": _read_json(service, graph[0]),
        "chains": _read_json(service, chain_docs[0]),
    }


def _expected_chain_keys(snapshot, entries):
    """由 Snapshot 独立推出应有的 (entry_id, assertion_id, span, start, end) 集合。"""
    assertions = {a["assertion_id"]: a for a in snapshot["assertions"]}
    expected = set()
    for entry in entries:
        for assertion_id in entry["assertion_ids"]:
            for ev in assertions[assertion_id].get("evidence") or []:
                expected.add(
                    (entry["entry_id"], assertion_id, ev["source_span_id"], ev["start_offset"], ev["end_offset"])
                )
    return expected


class TestRunM8CompilesKnowledgeFromSnapshot(unittest.TestCase):
    """glyphbox 档：mini_ed01 上游 + mini_release01 真 M7 创世 Snapshot。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="t04b-kd-")
        self.service = LedgerService(Path(self._tmp) / "ledger")

    def tearDown(self):
        self.service.close()
        shutil.rmtree(self._tmp, True)

    @unittest.skipUnless(assets_available(), "本机缺三页真实页图")
    def test_run_m8_seals_entry_ids_knowledge_pack_evidence_chains_and_graph(self):
        prepared = prepare_m8_ready(self.service)
        edition_part_id = prepared["edition_part_id"]
        manifest = yaml.safe_load((FIXTURE_M7 / "manifest.yaml").read_bytes())
        seeded = seed_release_package(self.service, FIXTURE_M7)
        first_m6 = seeded["editions"][manifest["editions"][0]["edition_key"]]
        res_m7 = run_m7(
            self.service,
            edition_part_id,
            technique_id="qizheng",
            reviewed_package_revision_ids=[first_m6["m6_package_revision_id"]],
            id_range=manifest["id_range"],
        )
        self.assertEqual(res_m7["status"], "succeeded")
        snapshot = _read_json(self.service, res_m7["snapshot_revision_id"])

        res_m8 = run_m8(self.service, edition_part_id, consumption_level="INTERNAL_DEMO")
        step_run_id = res_m8["step_run_id"]
        # M7 Snapshot 是 M8 的冻结输入
        self.assertIn(res_m7["snapshot_revision_id"], self.service.list_frozen_inputs(step_run_id))

        out = _knowledge_outputs(self, self.service, step_run_id)
        allocation, knowledge, graph, chains = (
            out["allocation"], out["knowledge"], out["graph"], out["chains"],
        )
        # 发号表（INTERFACES §3.16）→ KnowledgeDataPack 词条身份一一对应
        self.assertEqual(allocation["allocation_count"], len(allocation["allocations"]))
        self.assertEqual(
            {a["subject_entity_id"]: a["entry_id"] for a in allocation["allocations"]},
            {e["subject_entity_id"]: e["entry_id"] for e in knowledge["entries"]},
        )
        for item in allocation["allocations"]:
            self.assertRegex(item["entry_id"], _ENT_UUID4)
        # 词条主体只来自 Snapshot 显式引用（Pattern.assertion_ids 非空）
        self.assertTrue(knowledge["entries"])
        self.assertEqual(
            sorted(e["subject_entity_id"] for e in knowledge["entries"]),
            sorted(p["pattern_id"] for p in snapshot["patterns"] if p["assertion_ids"]),
        )
        # 同一 Release
        self.assertEqual(knowledge["release_id"], allocation["release_id"])
        self.assertEqual(chains["release_id"], knowledge["release_id"])
        self.assertEqual(graph["release_id"], knowledge["release_id"])

        # 证据链：条数与 Snapshot 独立推导一致；每条恰 7 键；偏移按 I-11 绝对偏移回指 span
        self.assertTrue(chains["chains"])
        got = {
            (
                c["entry_id"],
                c["assertion_id"],
                c["evidence_link"]["source_span_id"],
                c["evidence_link"]["start_offset"],
                c["evidence_link"]["end_offset"],
            )
            for c in chains["chains"]
        }
        self.assertEqual(got, _expected_chain_keys(snapshot, knowledge["entries"]))
        spans = {
            s["span_id"]: s
            for s in _read_any(self.service, prepared["m3"]["spans_revision_id"])["spans"]
        }
        for chain in chains["chains"]:
            self.assertEqual(
                list(chain),
                ["entry_id", "assertion_id", "evidence_link", "source_span", "source_anchor", "ocr_page", "source_asset"],
            )
            link = chain["evidence_link"]
            span = spans[link["source_span_id"]]
            local = (link["start_offset"] - span["start_offset"], link["end_offset"] - span["start_offset"])
            self.assertEqual(link["quote"], span["text"][local[0]:local[1]])
            self.assertEqual(hashlib.sha256(link["quote"].encode("utf-8")).hexdigest(), link["quote_sha256"])
            self.assertEqual(chain["source_span"]["text"], span["text"])
            self.assertEqual(chain["source_anchor"], span["source_anchor"])
            self.assertEqual(
                chain["ocr_page"]["glyph_ids"],
                [char["glyph_id"] for char in span["source_anchor"]["chars"]],
            )
            self.assertEqual(chain["source_asset"]["image_sha256"], span["source_anchor"]["image_sha256"])

        # GraphProjectionPack 与 ReleaseManifest 共享 canonical_hash（§16:725）
        release_manifest = _read_json(self.service, _sealed(self.service, step_run_id, "release_manifest")[0])
        self.assertEqual(graph["canonical_hash"], release_manifest["canonical_hash"])
        self.assertTrue(graph["nodes"])
        self.assertTrue(graph["edges"])
        # 无主体断言如实披露（INTERFACES §3.8：assertion_without_subject: N + 逐条 ID）
        referenced = {a for p in snapshot["patterns"] for a in p["assertion_ids"]}
        orphans = sorted(
            a["assertion_id"]
            for a in snapshot["assertions"]
            if a["assertion_id"] not in referenced and not a.get("concept_refs")
        )
        self.assertTrue(orphans, "夹具前提：r1 Snapshot 含无主体断言")
        disclosed = [d for d in release_manifest["known_defects"] if d["code"] == "assertion_without_subject"]
        self.assertEqual(
            disclosed,
            [{"code": "assertion_without_subject", "detail": "%d: %s" % (len(orphans), ",".join(orphans))}],
        )


class TestRunM8KnowledgeOffsetRoute(ElectronicTextStepBase):
    """offset 档（电子文本路线，真书路线）：证据链第 6/7 段为 text_mapping / source_asset{page, sha256}。"""

    def _offset_knowledge(self, inputs):
        """一条 Pattern、一条带真实 span 绝对偏移证据的断言（形状同 M7 Snapshot）。"""
        spans_doc = _read_any(self.service, inputs["spans_revision_id"])
        span = spans_doc["spans"][0]
        length = min(2, len(span["text"]))
        quote = span["text"][:length]
        return span, {
            "technique_id": inputs["technique_id"],
            "patterns": [
                {"pattern_id": "pat_qizheng_000001", "name": "示例格局", "assertion_ids": ["as_qizheng_000001"]}
            ],
            "concepts": [],
            "assertions": [
                {
                    "assertion_id": "as_qizheng_000001",
                    "proposition": "示例断言",
                    "subject_entity_id": "pat_qizheng_000001",
                    "evidence": [
                        {
                            "source_span_id": span["span_id"],
                            "start_offset": span["start_offset"],
                            "end_offset": span["start_offset"] + length,
                            "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                        }
                    ],
                    "school_view_ids": [],
                    "content_status": "machine_extracted",
                }
            ],
            "school_views": [],
            "conflict_groups": [],
        }

    def test_previous_release_allocation_refuses_instead_of_renumbering(self):
        """账本已有同技法、已 succeeded 的前序发号表：不得静默重新发号（跨 Release 保号，TODO T05e）。"""
        from pipeline.ledger import ids

        inputs = self._ready()
        technique_id = inputs["technique_id"]
        processing_run_id = self.service.create_processing_run(
            "release_run", ids.new_id("artifact_id"), technique_id
        )
        _, config_revision_id = self.service.put_run_artifact(
            processing_run_id, "configuration", json.dumps({"stage": "m8"}).encode("utf-8"),
            producer_module="test.seed", producer_version="0",
        )
        step_run_id = self.service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "processing_run_id": processing_run_id,
                "step_run_id": ids.new_id("step_run_id"),
                "input_artifact_ids": [],
                "technique_profile_id": technique_id,
                "configuration_artifact_id": config_revision_id,
            }
        )
        _, previous_revision_id = self.service.put_artifact(
            step_run_id, "entry_id_allocation",
            json.dumps({"technique_id": technique_id, "allocations": []}).encode("utf-8"),
            producer_module="test.seed", producer_version="0",
        )
        self.service.seal_revision(previous_revision_id)
        self.service.finish_step_run(
            step_run_id,
            {
                "schema_version": "1.0.0",
                "processing_run_id": processing_run_id,
                "step_run_id": step_run_id,
                "status_version": self.service.get_step_run(step_run_id)["status_version"] + 1,
                "status": "succeeded",
                "output_artifact_ids": [previous_revision_id],
                "validation_report_ids": [],
                "log_artifact_ids": [],
                "failure_artifact_ids": [],
            },
        )
        _span, knowledge = self._offset_knowledge(inputs)
        seed_m7_snapshot(self.service, self.edition_part_id, knowledge=knowledge)
        result = self._run_etext()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_check"], "compile")
        self.assertIn(previous_revision_id, result["reason"])
        self.assertIn("T05e", result["reason"])
        self.assertEqual(_sealed(self.service, result["step_run_id"], "entry_id_allocation"), [])

    def test_offset_evidence_chain_carries_text_mapping_and_raw_text_sha(self):
        inputs = self._ready()
        span, knowledge = self._offset_knowledge(inputs)
        seed_m7_snapshot(self.service, self.edition_part_id, knowledge=knowledge)
        result = self._run_etext()
        out = _knowledge_outputs(self, self.service, result["step_run_id"])
        chains = out["chains"]["chains"]
        self.assertEqual(len(chains), 1)
        chain = chains[0]
        self.assertEqual(
            list(chain),
            ["entry_id", "assertion_id", "evidence_link", "source_span", "source_anchor", "text_mapping", "source_asset"],
        )
        anchor = span["source_anchor"]
        self.assertEqual(
            chain["text_mapping"],
            {
                "raw_text_revision_id": anchor["raw_text_revision_id"],
                "cleaned_text_revision_id": anchor["cleaned_text_revision_id"],
                "patch_set_revision_id": inputs["deterministic_patch_set_revision_id"],
                "raw_start": anchor["raw_start"],
                "raw_end": anchor["raw_end"],
            },
        )
        raw_text_sha256 = self.service.get_revision(inputs["raw_text_revision_id"])["sha256"]
        self.assertEqual(chain["source_asset"]["sha256"], raw_text_sha256)
        # reference_and_hash_only：quote 与 source_span.text 置 null，保留偏移与 quote_sha256（Q-M8-03）
        self.assertIsNone(chain["evidence_link"]["quote"])
        self.assertIsNone(chain["source_span"]["text"])
        self.assertEqual(
            chain["evidence_link"]["quote_sha256"],
            knowledge["assertions"][0]["evidence"][0]["quote_sha256"],
        )

    def test_offset_route_publication_content_checks_pass(self):
        """真书路线（offset 档）：M8 成功后，验收的知识链与图投影内容校验实评通过。"""
        from pipeline.dataset_compiler import acceptance

        inputs = self._ready()
        _span, knowledge = self._offset_knowledge(inputs)
        seed_m7_snapshot(self.service, self.edition_part_id, knowledge=knowledge)
        result = self._run_etext()
        self.assertEqual(result["status"], "succeeded", result.get("reason"))
        step_run_id, _package_revision_id, package = acceptance._find_m8_package(
            self.service, self.edition_part_id
        )
        facts = acceptance._m8_output_facts(
            {"service": self.service, "package": package, "m8_step_run_id": step_run_id}
        )
        name, status, detail = acceptance._check_knowledge_chain(facts)
        self.assertEqual((name, status), ("knowledge_chain", "PASS"), detail)
        name, status, detail = acceptance._check_graph_projection(facts)
        self.assertEqual((name, status), ("graph_projection", "PASS"), detail)


# ---------------------------------------------------------------------------
# T04B 第 4 项：M8 验收 knowledge_chain / graph_projection 的真内容校验。
# 先在真实 Ledger 上跑通 M7→M8，再逐项篡改 Ledger 里读出的文档（经假 Ledger 端口替换
# 修订内容，不改真账本），每一种篡改都必须让对应判据 FAIL。
# ---------------------------------------------------------------------------
class _TamperedLedger:
    """读端口包装：指定修订返回替换后的字节，其余原样委派真 Ledger。"""

    def __init__(self, service, replacements):
        self._service = service
        self._replacements = replacements

    def get_revision(self, revision_id):
        if revision_id in self._replacements:
            return dict(self._service.get_revision(revision_id), sha256="tampered:" + revision_id)
        return self._service.get_revision(revision_id)

    def read_object(self, sha256):
        if sha256.startswith("tampered:"):
            return self._replacements[sha256[len("tampered:"):]]
        return self._service.read_object(sha256)

    def __getattr__(self, name):
        return getattr(self._service, name)


@unittest.skipUnless(assets_available(), "本机缺三页真实页图")
class TestPublicationContentChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pipeline.dataset_compiler import acceptance

        cls.acceptance = acceptance
        cls._tmp = tempfile.mkdtemp(prefix="t04b-acc-")
        cls.service = LedgerService(Path(cls._tmp) / "ledger")
        prepared = prepare_m8_ready(cls.service)
        cls.edition_part_id = prepared["edition_part_id"]
        manifest = yaml.safe_load((FIXTURE_M7 / "manifest.yaml").read_bytes())
        seeded = seed_release_package(cls.service, FIXTURE_M7)
        first_m6 = seeded["editions"][manifest["editions"][0]["edition_key"]]
        res_m7 = run_m7(
            cls.service,
            cls.edition_part_id,
            technique_id="qizheng",
            reviewed_package_revision_ids=[first_m6["m6_package_revision_id"]],
            id_range=manifest["id_range"],
        )
        assert res_m7["status"] == "succeeded", res_m7
        res_m8 = run_m8(cls.service, cls.edition_part_id, consumption_level="INTERNAL_DEMO")
        assert res_m8["status"] == "succeeded", res_m8.get("reason")
        context = _build_context(
            cls.service, cls.edition_part_id, FIXTURE_M8, FIXTURE_M8, "glyphbox_level"
        )
        cls.facts = acceptance._m8_output_facts(context)

    @classmethod
    def tearDownClass(cls):
        cls.service.close()
        shutil.rmtree(cls._tmp, True)

    def _doc(self, revision_id):
        return json.loads(self.service.read_object(self.service.get_revision(revision_id)["sha256"]).decode("utf-8"))

    def _tampered_facts(self, revision_id, mutate):
        document = self._doc(revision_id)
        mutate(document)
        data = json.dumps(document, ensure_ascii=False).encode("utf-8")
        return dict(self.facts, service=_TamperedLedger(self.service, {revision_id: data}))

    def _knowledge_status(self, facts):
        return self.acceptance._check_knowledge_chain(facts)[1:]

    def _graph_status(self, facts):
        return self.acceptance._check_graph_projection(facts)[1:]

    @property
    def _packs(self):
        return self.facts["packs"]

    def _orphan_id(self):
        knowledge = self._doc(self._packs["knowledge_data_pack"])
        referenced = {a for entry in knowledge["entries"] for a in entry["assertion_ids"]}
        return sorted(a["assertion_id"] for a in knowledge["assertions"] if a["assertion_id"] not in referenced)[0]

    def test_untampered_publication_passes_both_content_checks(self):
        status, detail = self._knowledge_status(self.facts)
        self.assertEqual(status, "PASS", detail)
        status, detail = self._graph_status(self.facts)
        self.assertEqual(status, "PASS", detail)

    def test_evidence_link_moved_off_its_entry_assertion_fails(self):
        orphan = self._orphan_id()

        def mutate(doc):
            doc["chains"][0]["assertion_id"] = orphan
            doc["chains"][0]["evidence_link"]["assertion_id"] = orphan

        status, detail = self._knowledge_status(self._tampered_facts(self._packs["evidence_chain"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_quote_hash_tamper_fails(self):
        def mutate(doc):
            doc["chains"][0]["evidence_link"]["quote_sha256"] = "0" * 64

        status, detail = self._knowledge_status(self._tampered_facts(self._packs["evidence_chain"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_evidence_offset_moved_outside_span_fails(self):
        def mutate(doc):
            link = doc["chains"][0]["evidence_link"]
            link["start_offset"] -= link["start_offset"] + 1  # 负偏移：越出 span

        status, detail = self._knowledge_status(self._tampered_facts(self._packs["evidence_chain"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_dropped_chain_fails(self):
        def mutate(doc):
            doc["chains"].pop()

        status, detail = self._knowledge_status(self._tampered_facts(self._packs["evidence_chain"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_chain_segment_order_swapped_fails(self):
        def mutate(doc):
            chain = doc["chains"][0]
            reordered = {key: chain[key] for key in ("entry_id", "assertion_id", "source_span", "evidence_link")}
            reordered.update({key: chain[key] for key in list(chain)[4:]})
            doc["chains"][0] = reordered

        status, detail = self._knowledge_status(self._tampered_facts(self._packs["evidence_chain"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_ocr_page_glyph_ids_tamper_fails(self):
        def mutate(doc):
            doc["chains"][0]["ocr_page"]["glyph_ids"] = doc["chains"][0]["ocr_page"]["glyph_ids"][:-1]

        status, detail = self._knowledge_status(self._tampered_facts(self._packs["evidence_chain"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_entry_assertion_set_tamper_fails(self):
        orphan = self._orphan_id()

        def mutate(doc):
            doc["entries"][0]["assertion_ids"] = sorted(doc["entries"][0]["assertion_ids"] + [orphan])

        status, detail = self._knowledge_status(self._tampered_facts(self._packs["knowledge_data_pack"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_undisclosed_subjectless_assertion_fails(self):
        def mutate(doc):
            doc["known_defects"] = [d for d in doc["known_defects"] if d["code"] != "assertion_without_subject"]

        facts = self._tampered_facts(self.facts["publication"]["release_manifest_revision_id"], mutate)
        status, detail = self._knowledge_status(facts)
        self.assertEqual(status, "FAIL", detail)

    def test_graph_edge_dropped_fails(self):
        def mutate(doc):
            doc["edges"].pop()
            doc["edge_count"] -= 1

        status, detail = self._graph_status(self._tampered_facts(self._packs["graph_projection_pack"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_graph_node_label_changed_fails(self):
        def mutate(doc):
            doc["nodes"][0]["label"] += "（改）"

        status, detail = self._graph_status(self._tampered_facts(self._packs["graph_projection_pack"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_graph_extra_node_fails(self):
        def mutate(doc):
            doc["nodes"].append(
                {
                    "node_id": "co_qizheng_999999",
                    "kind": "concept",
                    "label": "多出来的概念",
                    "content_status": "machine_extracted",
                    "watermark": True,
                }
            )
            doc["nodes"].sort(key=lambda node: node["node_id"])
            doc["node_count"] += 1

        status, detail = self._graph_status(self._tampered_facts(self._packs["graph_projection_pack"], mutate))
        self.assertEqual(status, "FAIL", detail)

    def test_graph_canonical_hash_mismatch_fails(self):
        def mutate(doc):
            doc["canonical_hash"] = "0" * 64

        status, detail = self._graph_status(self._tampered_facts(self._packs["graph_projection_pack"], mutate))
        self.assertEqual(status, "FAIL", detail)

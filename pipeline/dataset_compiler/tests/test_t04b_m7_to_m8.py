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

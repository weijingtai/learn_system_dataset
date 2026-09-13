"""M7 创世 Ledger 事务测试（spec §17, §6.2, act/g0-04）。"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.fixture_seed import seed_genesis_package
from pipeline.assembly.genesis import assemble_genesis, propose_genesis
from pipeline.assembly.model import validate_candidate_set
from pipeline.assembly.step import begin_or_supersede, run_m7
from pipeline.ledger.service import LedgerService


def load_fixture_data():
    data_path = os.path.join(os.path.dirname(__file__), "data", "genesis_package.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestGenesisLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.service = LedgerService(Path(self.tmp) / "ledger")
        self.fixture_doc = load_fixture_data()
        self.seed_res = seed_genesis_package(self.service, self.fixture_doc)
        self.edition_part_id = self.fixture_doc["ledger_constants"]["edition_part_artifact_id"]
        self.technique_id = self.fixture_doc["ledger_constants"]["technique_id"]
        self.m6_pkg_rev_id = self.seed_res["m6_package_revision_id"]

    def tearDown(self):
        if hasattr(self.service, "close"):
            self.service.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run_m7_genesis_succeeds_and_seals_snapshot(self):
        res = run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
        )
        self.assertEqual(res["status"], "succeeded")
        self.assertIsNotNone(res["snapshot_revision_id"])
        self.assertIsNotNone(res["assembly_package_revision_id"])
        self.assertIsNotNone(res["validation_report_revision_id"])
        self.assertTrue(res["gate"]["passed"])

        # 校验 Snapshot 字节与纯函数结果逐字相同
        snap_rev = self.service.get_revision(res["snapshot_revision_id"])
        self.assertEqual(snap_rev["status"], "sealed")
        snap_bytes = self.service.objects.get(snap_rev["sha256"])
        snap_doc = json.loads(snap_bytes.decode("utf-8"))

        cset = self.fixture_doc["candidate_set"]
        ed = self.fixture_doc["reviewed_edition"]
        prop = propose_genesis(cset, ed)
        expected = assemble_genesis(cset, ed, prop["proposals"], id_range={"pattern": [1, 10000]})
        self.assertEqual(snap_bytes, expected["knowledge_bytes"])

    def test_configuration_and_processing_run_shape(self):
        res = run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
        )
        step = self.service.get_step_run(res["step_run_id"])
        req = json.loads(step["request_json"])
        cfg_rev_id = req["configuration_artifact_id"]
        cfg_rev = self.service.get_revision(cfg_rev_id)
        cfg_doc = json.loads(self.service.objects.get(cfg_rev["sha256"]).decode("utf-8"))
        self.assertEqual(cfg_doc["stage"], "m7")
        self.assertEqual(cfg_doc["task"], "assemble")
        self.assertEqual(cfg_doc["technique_id"], self.technique_id)

        proc_id = step["processing_run_id"]
        proc_row = self.service.store.conn.execute(
            "SELECT kind, edition_part_id, technique_id FROM processing_runs WHERE processing_run_id=?",
            (proc_id,),
        ).fetchone()
        self.assertIsNotNone(proc_row)
        self.assertEqual(proc_row[0], "release_run")
        self.assertEqual(proc_row[1], self.edition_part_id)
        self.assertEqual(proc_row[2], self.technique_id)

    def test_stage_package_schema_and_lineage(self):
        res = run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
        )
        step = self.service.get_step_run(res["step_run_id"])
        result = json.loads(step["result_json"])
        output_revs = result["output_artifact_ids"]
        self.assertIn(res["assembly_package_revision_id"], output_revs)
        self.assertIn(res["snapshot_revision_id"], output_revs)

        # stage_package 恰 1 个 assembly_package 输出
        stg_pkg_rev = [r for r in output_revs if r.startswith("rev_") and self.service.store.conn.execute("SELECT artifact_type FROM artifacts a JOIN artifact_revisions r ON r.artifact_id=a.artifact_id WHERE r.artifact_revision_id=?", (r,)).fetchone()[0] == "stage_package"][0]
        stg_doc = json.loads(self.service.objects.get(self.service.get_revision(stg_pkg_rev)["sha256"]).decode("utf-8"))
        outputs = stg_doc["manifest"]["output_artifacts"]
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]["artifact_type"], "assembly_package")
        self.assertEqual(outputs[0]["artifact_revision_id"], res["assembly_package_revision_id"])

        # lineage 输入集合 == frozen_inputs
        frozen_inputs = self.service._frozen_input_ids(res["step_run_id"])
        upstream_revs = [u["artifact_revision_id"] for u in stg_doc["lineage"]["upstream_artifacts"]]
        self.assertEqual(set(upstream_revs), set(frozen_inputs))

    def test_checkpoints_propose_then_seal(self):
        res = run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
        )
        cps = self.service.list_checkpoints(self.edition_part_id, "m7")
        self.assertGreaterEqual(len(cps), 2)
        tasks = []
        for cp in cps:
            for t in cp["content"].get("completed_tasks", []):
                tasks.append(t["task_id"])
        self.assertIn("propose_r1", tasks)
        self.assertIn("seal_snapshot", tasks)
        # 链条成链
        for i in range(1, len(cps)):
            self.assertEqual(cps[i]["prev_checkpoint_revision_id"], cps[i - 1]["artifact_revision_id"])

    def test_refuse_before_begin_no_writes(self):
        # 记录基线行数
        c_revs_0 = self.service.store.conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0]
        c_steps_0 = self.service.store.conn.execute("SELECT count(*) FROM step_runs").fetchone()[0]
        c_audit_0 = self.service.store.conn.execute("SELECT count(*) FROM audit_log").fetchone()[0]

        # 1. base_snapshot_revision_id 非 None
        with self.assertRaises(AssemblyRefused) as ctx:
            run_m7(
                self.service,
                self.edition_part_id,
                technique_id=self.technique_id,
                reviewed_package_revision_ids=[self.m6_pkg_rev_id],
                base_snapshot_revision_id="rev_00000000000000000000000000000099",
            )
        self.assertIn("纵切后", str(ctx.exception))

        # 行数不变
        self.assertEqual(self.service.store.conn.execute("SELECT count(*) FROM artifact_revisions").fetchone()[0], c_revs_0)
        self.assertEqual(self.service.store.conn.execute("SELECT count(*) FROM step_runs").fetchone()[0], c_steps_0)
        self.assertEqual(self.service.store.conn.execute("SELECT count(*) FROM audit_log").fetchone()[0], c_audit_0)

    def test_begin_or_supersede_uses_existing_succeeded_run(self):
        # 先执行一次成功运行
        res1 = run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
        )
        self.assertEqual(res1["status"], "succeeded")

        # 使用 helper 开启新运行（应接替旧运行而非直接 begin）
        step_run_id2 = begin_or_supersede(
            self.service,
            self.edition_part_id,
            "m7",
            configuration_revision_id=self.seed_res["config_revision_id"],
            input_artifact_ids=[self.m6_pkg_rev_id],
            processing_run_id=self.fixture_doc["ledger_constants"]["processing_run_id"],
            technique_id=self.technique_id,
        )
        step2 = self.service.get_step_run(step_run_id2)
        self.assertEqual(step2["supersedes_step_run_id"], res1["step_run_id"])

    def test_gate_failure_seals_failure_report_and_no_package(self):
        # 破坏 candidate_set 使得 gate 校验失败（改动 proposition）
        res = run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
            _tamper_fn=lambda k: k["assertions"].__setitem__(0, dict(k["assertions"][0], proposition="篡改命题")),
        )
        self.assertEqual(res["status"], "failed")
        self.assertFalse(res["gate"]["passed"])
        self.assertIsNone(res.get("assembly_package_revision_id"))
        step = self.service.get_step_run(res["step_run_id"])
        self.assertEqual(step["status"], "failed")
        events = self.service.list_step_run_events(res["step_run_id"])
        fail_events = [e for e in events if e["event_type"] == "failure"]
        self.assertEqual(len(fail_events), 1)
        payload = json.loads(fail_events[0]["payload_json"])
        self.assertGreater(len(payload["failure_revision_ids"]), 0)

    def test_cli_success_and_refusal_codes(self):
        import subprocess
        import sys

        # CLI 会以新进程打开 LedgerService，需先释放当前测试进程的写锁
        self.service.close()

        cmd_ok = [
            sys.executable,
            "-m",
            "pipeline.assembly",
            "run",
            "--ledger-dir",
            str(Path(self.tmp) / "ledger"),
            "--edition-part-id",
            self.edition_part_id,
            "--technique-id",
            self.technique_id,
            "--reviewed-package-revision-id",
            self.m6_pkg_rev_id,
        ]
        proc = subprocess.run(cmd_ok, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"stdout: {proc.stdout}, stderr: {proc.stderr}")
        self.assertTrue(proc.stdout.strip().splitlines()[-1].startswith("M7 OK"))

        cmd_refuse = [
            sys.executable,
            "-m",
            "pipeline.assembly",
            "run",
            "--ledger-dir",
            str(Path(self.tmp) / "ledger"),
            "--edition-part-id",
            self.edition_part_id,
            "--technique-id",
            self.technique_id,
            "--reviewed-package-revision-id",
            self.m6_pkg_rev_id,
            "--base-snapshot-revision-id",
            "rev_00000000000000000000000000000099",
        ]
        proc2 = subprocess.run(cmd_refuse, capture_output=True, text=True)
        self.assertEqual(proc2.returncode, 2, f"stdout: {proc2.stdout}, stderr: {proc2.stderr}")

        # 恢复 service 供 tearDown 正常清理
        self.service = LedgerService(Path(self.tmp) / "ledger")

    def test_no_upstream_mutation(self):
        # 运行前状态
        m6_rev_0 = self.service.get_revision(self.m6_pkg_rev_id)
        re_rev_0 = self.service.get_revision(self.seed_res["reviewed_edition_revision_id"])
        m6_events_0 = self.service.store.conn.execute(
            "SELECT count(*) FROM revision_status_events WHERE artifact_revision_id=?",
            (self.m6_pkg_rev_id,),
        ).fetchone()[0]

        run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
        )

        # 运行后比对
        m6_rev_1 = self.service.get_revision(self.m6_pkg_rev_id)
        re_rev_1 = self.service.get_revision(self.seed_res["reviewed_edition_revision_id"])
        m6_events_1 = self.service.store.conn.execute(
            "SELECT count(*) FROM revision_status_events WHERE artifact_revision_id=?",
            (self.m6_pkg_rev_id,),
        ).fetchone()[0]

        self.assertEqual(m6_rev_0["sha256"], m6_rev_1["sha256"])
        self.assertEqual(m6_rev_0["status"], m6_rev_1["status"])
        self.assertEqual(re_rev_0["sha256"], re_rev_1["sha256"])
        self.assertEqual(re_rev_0["status"], re_rev_1["status"])
        self.assertEqual(m6_events_0, m6_events_1)

    def test_configuration_registers_id_range(self):
        res = run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
            id_range={"pattern": [100, 200]},
        )
        step = self.service.get_step_run(res["step_run_id"])
        req = json.loads(step["request_json"])
        cfg_doc = json.loads(self.service.objects.get(self.service.get_revision(req["configuration_artifact_id"])["sha256"]).decode("utf-8"))
        self.assertEqual(cfg_doc["id_range"], {"pattern": [100, 200]})

    def test_snapshot_knowledge_records_id_range_and_allocation_list(self):
        res = run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
            id_range={"pattern": [10, 50]},
        )
        snap_rev = self.service.get_revision(res["snapshot_revision_id"])
        snap_doc = json.loads(self.service.objects.get(snap_rev["sha256"]).decode("utf-8"))
        # 存储层改键为 pat_<technique>
        self.assertEqual(snap_doc["id_range"], {"pat_qizheng": [10, 50]})
        self.assertEqual(snap_doc["allocated_pattern_ids"], [])

    def test_synthetic_human_decisions_marked_and_not_expert_verified(self):
        for dec in self.fixture_doc["reviewed_edition"].get("decisions", []):
            self.assertTrue(dec.get("synthetic_fixture"), "Decision must contain synthetic_fixture: true")

        res = run_m7(
            self.service,
            self.edition_part_id,
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[self.m6_pkg_rev_id],
        )
        snap_rev = self.service.get_revision(res["snapshot_revision_id"])
        snap_doc = json.loads(self.service.objects.get(snap_rev["sha256"]).decode("utf-8"))
        for p in snap_doc.get("patterns", []):
            self.assertNotIn("content_status", p)

    def test_synthetic_candidate_set_matches_impl05_shape(self):
        cset = self.fixture_doc["candidate_set"]
        v_cset = validate_candidate_set(cset)
        self.assertIsNotNone(v_cset)
        for a in cset["assertions"]:
            self.assertNotIn("subject", a)
            self.assertNotIn("school_view_ids", a)
            self.assertIn("school_ids", a)
        for p in cset["patterns"]:
            self.assertNotIn("candidate_key", p)
            self.assertIn("pattern_id", p)
            self.assertTrue(p["pattern_id"].startswith("pat_"))


if __name__ == "__main__":
    unittest.main()

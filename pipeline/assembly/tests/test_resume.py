"""M7 增量汇编人工暂停与续跑测试（TODO T04B 第三轮方案 A）。

验证：
1. 增量 Release 停在 awaiting_human 后，可带 resume_token 经 orchestrator.human.resume
   走描述符 resume_entry 续跑；同一 StepRun 收口 succeeded、写出新 Snapshot；
2. resume_token 只在内存流转，绝不落盘（按字节搜 ledger.sqlite 与 objects/ 均为 0 命中）；
3. 校验规则：未决提案不可续跑、错误 token 拒绝。
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.assembly import fixture_seed
from pipeline.assembly.errors import AssemblyRefused
from pipeline.assembly.step import run_m7
from pipeline.assembly.tests.fixture_decisions import decisions_for_round, load_manifest
from pipeline.contract_registry.catalog import load_registry
from pipeline.contract_registry.ports import DirectLedgerAdapter
from pipeline.ledger.errors import InvalidResumeToken
from pipeline.ledger.service import LedgerService
from pipeline.orchestrator.human import resume

try:
    from pipeline.assembly.step import record_m7_decision, resume_m7
except ImportError:
    record_m7_decision = None
    resume_m7 = None

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_release01"


class TestM7Resume(unittest.TestCase):
    """M7 增量汇编暂停与恢复测试。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m7_resume_test_")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.ledger_dir = Path(self._tmp) / "ledger"
        self.adapter = DirectLedgerAdapter(self.ledger_dir)
        self.addCleanup(self.adapter.close)
        self.service = self.adapter.unwrap()
        self.registry = load_registry()
        self.manifest = load_manifest()
        self.technique_id = self.manifest["technique_id"]
        self.seeded = fixture_seed.seed_release_package(self.service, FIXTURE)["editions"]
        self.ed01 = self.manifest["editions"][0]
        self.ed99 = self.manifest["editions"][1]

    def _run_genesis(self):
        """执行首版次创世汇编，产出 r1 Snapshot。"""
        m6_rev = self.seeded[self.ed01["edition_key"]]["m6_package_revision_id"]
        res = run_m7(
            self.service,
            self.ed01["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[m6_rev],
            base_snapshot_revision_id=None,
            id_range=self.manifest["id_range"],
        )
        self.assertEqual(res["status"], "succeeded")
        return res

    def test_incremental_release_resumes_after_awaiting_human(self):
        """用例先红：增量 Release 停在 awaiting_human 后经 orchestrator.human.resume 续跑。"""
        # 1. 创世
        r1 = self._run_genesis()
        s1_rev = r1["snapshot_revision_id"]

        # 2. 增量轮（ed99，有待决提案）→ 停在 awaiting_human
        m6_rev_99 = self.seeded[self.ed99["edition_key"]]["m6_package_revision_id"]
        r2 = run_m7(
            self.service,
            self.ed99["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[m6_rev_99],
            base_snapshot_revision_id=s1_rev,
            id_range=self.manifest["id_range"],
        )
        self.assertEqual(r2["status"], "awaiting_human")
        step_run_id = r2["step_run_id"]
        token = r2.get("resume_token")
        self.assertIsNotNone(token, "run_m7 暂停时必须返回 resume_token")
        self.assertTrue(isinstance(token, str) and len(token) > 0)

        # 3. 登记人工决定（走 M7 公开入口）
        self.assertIsNotNone(record_m7_decision, "record_m7_decision 必须已实现")
        decisions = decisions_for_round(2)
        self.assertEqual(len(decisions), 1)
        rec_res = record_m7_decision(self.service, step_run_id, token, decisions[0])
        self.assertEqual(rec_res.get("remaining_pending"), [])

        # 4. 经 orchestrator.human.resume 走描述符 resume_entry 续跑
        handle = {"edition_part_id": self.ed99["edition_part_artifact_id"]}
        resumed = resume(self.adapter, self.registry, handle, step_run_id, token)

        # 5. 断言：同一 StepRun 收口 succeeded、写出新 Snapshot
        self.assertEqual(resumed["status"], "succeeded")
        self.assertEqual(resumed["step_run_id"], step_run_id)

        step_row = self.service.get_step_run(step_run_id)
        self.assertEqual(step_row["status"], "succeeded")

        # 验证新 Snapshot
        snap_rows = self.service.list_revisions(
            artifact_type="canonical_snapshot",
            status="sealed",
            step_run_ids=[step_run_id],
        )
        self.assertEqual(len(snap_rows), 1, "同一 StepRun 应写出恰 1 个新 Snapshot 修订")
        s2_rev = snap_rows[0]
        self.assertEqual(s2_rev["prev_revision_id"], s1_rev)
        s2_doc = json.loads(self.service.read_object(s2_rev["sha256"]).decode("utf-8"))
        self.assertEqual(s2_doc["meta"]["base_snapshot_revision_id"], s1_rev)
        self.assertEqual(s2_doc["meta"]["assembly_seq"], 2)

    def test_m7_resume_token_never_persisted(self):
        """用例：暂停后按字节搜 ledger.sqlite 与 objects/，token 明文 0 命中。"""
        r1 = self._run_genesis()
        m6_rev_99 = self.seeded[self.ed99["edition_key"]]["m6_package_revision_id"]
        r2 = run_m7(
            self.service,
            self.ed99["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[m6_rev_99],
            base_snapshot_revision_id=r1["snapshot_revision_id"],
            id_range=self.manifest["id_range"],
        )
        self.assertEqual(r2["status"], "awaiting_human")
        token = r2.get("resume_token")
        self.assertIsNotNone(token, "run_m7 暂停时必须返回 resume_token")
        token_bytes = token.encode("utf-8")

        # 搜 ledger.sqlite
        sqlite_file = self.ledger_dir / "ledger.sqlite"
        self.assertTrue(sqlite_file.is_file())
        self.assertNotIn(
            token_bytes,
            sqlite_file.read_bytes(),
            "resume_token 不得持久化到 ledger.sqlite",
        )

        # 搜 objects/ 下所有文件
        objects_dir = self.ledger_dir / "objects"
        object_files = list(objects_dir.glob("**/*"))
        self.assertTrue(len(object_files) > 0, "必须存在 objects 存储文件")
        for obj_path in object_files:
            if obj_path.is_file():
                self.assertNotIn(
                    token_bytes,
                    obj_path.read_bytes(),
                    "resume_token 不得持久化到 objects 文件: %s" % obj_path.name,
                )

    def test_resume_m7_refuses_when_proposals_undecided_and_keeps_token(self):
        """BDD 8.2：还有未决提案时调用 resume_m7 拒绝，StepRun 保持 awaiting_human，token 未被消费。"""
        r1 = self._run_genesis()
        m6_rev_99 = self.seeded[self.ed99["edition_key"]]["m6_package_revision_id"]
        r2 = run_m7(
            self.service,
            self.ed99["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[m6_rev_99],
            base_snapshot_revision_id=r1["snapshot_revision_id"],
            id_range=self.manifest["id_range"],
        )
        step_run_id = r2["step_run_id"]
        token = r2["resume_token"]

        # 未登记决定即调 resume_m7 → 拒绝
        with self.assertRaises(AssemblyRefused) as caught:
            resume_m7(self.service, step_run_id, token)
        self.assertEqual(caught.exception.code, "REF_001")

        # StepRun 仍保持 awaiting_human
        step_row = self.service.get_step_run(step_run_id)
        self.assertEqual(step_row["status"], "awaiting_human")

        # token 未被消费：登记决定后仍可使用该 token 成功续跑
        dec = decisions_for_round(2)[0]
        record_m7_decision(self.service, step_run_id, token, dec)
        resumed = resume_m7(self.service, step_run_id, token)
        self.assertEqual(resumed["status"], "succeeded")
        self.assertEqual(self.service.get_step_run(step_run_id)["status"], "succeeded")

    def test_record_m7_decision_rejects_duplicate_decision(self):
        """BDD 8.3：同一提案重复决定，在写入任何修订之前拒绝。"""
        r1 = self._run_genesis()
        m6_rev_99 = self.seeded[self.ed99["edition_key"]]["m6_package_revision_id"]
        r2 = run_m7(
            self.service,
            self.ed99["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[m6_rev_99],
            base_snapshot_revision_id=r1["snapshot_revision_id"],
            id_range=self.manifest["id_range"],
        )
        step_run_id = r2["step_run_id"]
        token = r2["resume_token"]
        dec = decisions_for_round(2)[0]

        record_m7_decision(self.service, step_run_id, token, dec)
        with self.assertRaises(AssemblyRefused) as caught:
            record_m7_decision(self.service, step_run_id, token, dec)
        self.assertEqual(caught.exception.code, "ID_002")

    def test_record_m7_decision_rejects_choice_not_in_options(self):
        """BDD 8.3：choice 不在 options 内拒绝。"""
        from pipeline.ledger.errors import SchemaViolation

        r1 = self._run_genesis()
        m6_rev_99 = self.seeded[self.ed99["edition_key"]]["m6_package_revision_id"]
        r2 = run_m7(
            self.service,
            self.ed99["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[m6_rev_99],
            base_snapshot_revision_id=r1["snapshot_revision_id"],
            id_range=self.manifest["id_range"],
        )
        step_run_id = r2["step_run_id"]
        token = r2["resume_token"]
        bad_dec = dict(decisions_for_round(2)[0], choice="impossible_choice")

        with self.assertRaises(SchemaViolation) as caught:
            record_m7_decision(self.service, step_run_id, token, bad_dec)
        self.assertEqual(caught.exception.code, "SCH_002")

    def test_resume_m7_rejects_wrong_token(self):
        """错误 token 拒绝，状态机不跃迁。"""
        r1 = self._run_genesis()
        m6_rev_99 = self.seeded[self.ed99["edition_key"]]["m6_package_revision_id"]
        r2 = run_m7(
            self.service,
            self.ed99["edition_part_artifact_id"],
            technique_id=self.technique_id,
            reviewed_package_revision_ids=[m6_rev_99],
            base_snapshot_revision_id=r1["snapshot_revision_id"],
            id_range=self.manifest["id_range"],
        )
        step_run_id = r2["step_run_id"]
        token = r2["resume_token"]
        dec = decisions_for_round(2)[0]
        record_m7_decision(self.service, step_run_id, token, dec)

        with self.assertRaises(InvalidResumeToken):
            resume_m7(self.service, step_run_id, token + "x")
        self.assertEqual(self.service.get_step_run(step_run_id)["status"], "awaiting_human")


if __name__ == "__main__":
    unittest.main()

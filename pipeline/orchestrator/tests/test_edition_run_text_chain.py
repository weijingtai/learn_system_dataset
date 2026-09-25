"""调度器 M1→M6 电子文本全线（TODO T04A，裁决 2/3/4）。

宿主：``pipeline/corpus/_fixture/qianyuan_ed01_text``（电子文本路线，OCR 夹具
``mini_ed01`` 只作为测试宿主存在，不进生产登记表）。

纪律（裁决 4）：

- M1–M6 只由调度器推进，人工节点只在 M4、M6 以 ``awaiting_human`` 暂停；
- 人工环节只走公开入口：M4 的提交走 ``run_m4_submit``、分歧裁决走
  ``record_category_ruling``；M6 的签发走审核台公开 API（``record_decision``）；
- 恢复统一经 ``human.resume``（legacy 绑定走描述符 ``resume_entry``）；
- 本模块不写任何金标文件，不直接改 Ledger 造人工结果。
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.contract_registry.catalog import load_registry
from pipeline.contract_registry.ports import DirectLedgerAdapter
from pipeline.knowledge_extraction import CANDIDATE_SCHEMA_VERSION
from pipeline.knowledge_extraction.step import record_category_ruling
from pipeline.knowledge_extraction.submit import run_m4_submit
from pipeline.orchestrator import EDITION_STAGES
from pipeline.orchestrator.edition_run import advance, run_until, start_edition_run
from pipeline.orchestrator.human import resume
from pipeline.orchestrator.module import bind_module
from pipeline.orchestrator.runner import run_legacy
from pipeline.review.step import record_decision

ROOT = Path(__file__).resolve().parents[3]
HOST = ROOT / "pipeline" / "corpus" / "_fixture" / "qianyuan_ed01_text"
M4_DIR = HOST / "m4"
CANON_DIR = ROOT / "pipeline" / "schemas" / "shared" / "canon"

SUBMISSION_FILES = (
    "submission_assertion_a.yaml",
    "submission_assertion_b.yaml",
    "submission_pattern_a.yaml",
    "submission_pattern_b.yaml",
    "submission_concept_mention_a.yaml",
    "submission_concept_mention_b.yaml",
)

# 允许停成 awaiting_human 的 stage（规格规定的人工节点）
HUMAN_STAGES = ("m4", "m6")


def _missing_host_reason():
    if not (HOST / "source_info.yaml").is_file():
        return "电子文本宿主缺失: %s" % HOST
    missing = [name for name in SUBMISSION_FILES if not (M4_DIR / name).is_file()]
    if missing:
        return "电子文本 M4 提交件缺失: %s" % ", ".join(missing)
    return None


@unittest.skipIf(_missing_host_reason() is not None, _missing_host_reason())
class EditionRunTextChainTests(unittest.TestCase):
    """临时 Ledger 上的 M1→M6 全线（不碰 ``var/``）。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="orch-text-chain-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.root = Path(self._tmp) / "ledger"
        self.adapter = DirectLedgerAdapter(self.root)
        self.addCleanup(self.adapter.close)
        self.service = self.adapter.unwrap()
        self.registry = load_registry()
        self.source_info = yaml.safe_load(
            (HOST / "source_info.yaml").read_text(encoding="utf-8")
        )
        self.edition_part_id = self.source_info["edition_part"]["artifact_id"]
        self.handle = start_edition_run(
            self.adapter,
            edition_part_id=self.edition_part_id,
            technique_id="qizheng",
            run_inputs={
                "route": "text",
                "source_dir": str(HOST),
                "source_info": self.source_info,
                "technique_profile": {
                    "technique_id": "qizheng",
                    "canon_dir": str(CANON_DIR),
                },
            },
        )
        self.awaiting_stages = []

    # ------------------------------------------------------------- 只读小工具
    def _doc_of(self, revision_id):
        row = self.service.get_revision(revision_id)
        return json.loads(self.service.objects.get(row["sha256"]).decode("utf-8"))

    def _dispute_ids(self, step_run_id):
        rows = self.service.list_step_run_revisions(
            step_run_id, artifact_type="dispute_queue"
        )
        self.assertEqual(len(rows), 1)
        doc = self._doc_of(rows[0]["artifact_revision_id"])
        return [row["dispute_id"] for row in doc["disputes"]]

    def _review_queue_item_ids(self, step_run_id):
        rows = self.service.list_step_run_revisions(
            step_run_id, artifact_type="review_queue"
        )
        self.assertEqual(len(rows), 1)
        doc = self._doc_of(rows[0]["artifact_revision_id"])
        return [row["queue_item_id"] for row in doc]

    def _note_human_stop(self, item):
        if (item.get("step_result") or {}).get("status") == "awaiting_human":
            self.awaiting_stages.append(item["stage"])

    # ------------------------------------------------------------------ 用例
    def test_run_until_m3_never_enters_m4(self):
        """生产登记表上 ``run_until(..., "m3")`` 执行完 m3 就停：本运行不得出现 m4 StepRun。"""
        results = run_until(self.adapter, self.registry, self.handle, "m3")
        self.assertEqual(
            [item["stage"] for item in results if item["action"] == "executed"],
            ["m1", "m2", "m3"],
        )
        for item in results:
            if item["action"] == "executed":
                self.assertEqual(item["step_result"]["status"], "succeeded", item["stage"])
        step_runs = self.adapter.run_status(self.handle["processing_run_id"])["step_runs"]
        self.assertEqual(
            sorted({row["stage"] for row in step_runs}), ["m1", "m2", "m3"]
        )

    def _submit_m4_and_pause(self):
        """跑 m1–m3 → 经公开入口交六份提交件 → ``advance`` 停在 m4 awaiting_human，返回该结果。"""
        run_until(self.adapter, self.registry, self.handle, "m3")
        for name in SUBMISSION_FILES:
            summary = run_m4_submit(
                self.service,
                self.edition_part_id,
                (M4_DIR / name).read_bytes(),
                producer_module="t04a_host:%s" % name,
                producer_version="0.1.0",
            )
            self.assertEqual(summary["status"], "succeeded", name)
        item = advance(self.adapter, self.registry, self.handle)
        self.assertEqual(
            (item["action"], item["stage"], item["step_result"]["status"]),
            ("executed", "m4", "awaiting_human"),
        )
        return item

    def test_resume_token_never_persisted(self):
        """裁决 3 硬约束：m4 暂停返回的 resume_token 明文不得落进 ledger 的 sqlite 或 objects/。"""
        item = self._submit_m4_and_pause()
        token = item["step_result"]["resume_token"]
        self.assertIsInstance(token, str)
        self.assertGreaterEqual(len(token), 32)
        needle = token.encode("utf-8")
        # 按字节搜之前先释放账本写锁（Windows 下 sqlite 打开时不可读）
        self.adapter.close()
        hits = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            if needle in path.read_bytes():
                hits.append(str(path.relative_to(self.root)))
        self.assertEqual(hits, [], "resume_token 明文出现在: %s" % hits)

    def test_m4_registry_entry_takes_technique_profile_from_run_inputs(self):
        """m4 登记条目是 M4 薄适配：技法画像只经运行输入进入，由入口登记在本运行下。"""
        descriptor = self.registry.module_for("m4")
        self.assertEqual(descriptor["entry"], "pipeline.knowledge_extraction.entry:run_m4")
        self.assertIs(descriptor.get("receives_run_inputs"), True)

        run_until(self.adapter, self.registry, self.handle, "m3")
        for name in SUBMISSION_FILES:
            summary = run_m4_submit(
                self.service,
                self.edition_part_id,
                (M4_DIR / name).read_bytes(),
                producer_module="t04a_host:%s" % name,
                producer_version="0.1.0",
            )
            self.assertEqual(summary["status"], "succeeded", name)
        profiles_before = self.service.list_revisions(
            artifact_type="technique_profile",
            processing_run_id=self.handle["processing_run_id"],
        )
        self.assertEqual(profiles_before, [])

        # 只验登记条目 → run_legacy → 薄适配的接线（advance 的 m4 判定见全线用例）
        out = run_legacy(self.adapter, bind_module(descriptor), self.handle)
        self.assertEqual(out["step_result"]["status"], "awaiting_human")
        self.assertEqual(out["processing_run_id"], self.handle["processing_run_id"])
        profiles = self.service.list_revisions(
            artifact_type="technique_profile",
            processing_run_id=self.handle["processing_run_id"],
        )
        self.assertEqual(len(profiles), 1)
        request = json.loads(self.service.get_step_run(out["step_run_id"])["request_json"])
        self.assertIn(profiles[0]["artifact_revision_id"], request["input_artifact_ids"])

    def test_scheduler_drives_m1_to_m6_with_public_human_entries(self):
        """M1→M6 全线：仅 M4/M6 停 awaiting_human，恢复经 human.resume 后自动收口。"""
        results = run_until(self.adapter, self.registry, self.handle, "m3")
        self.assertEqual(
            [item["stage"] for item in results if item["action"] == "executed"],
            ["m1", "m2", "m3"],
        )

        # M4 的六份提交件在 M3 之后经公开入口登记；技法画像由运行输入给出（M4 薄适配登记）。
        for name in SUBMISSION_FILES:
            summary = run_m4_submit(
                self.service,
                self.edition_part_id,
                (M4_DIR / name).read_bytes(),
                producer_module="t04a_host:%s" % name,
                producer_version="0.1.0",
            )
            self.assertEqual(summary["status"], "succeeded", name)

        # M4 停 awaiting_human
        item = advance(self.adapter, self.registry, self.handle)
        self._note_human_stop(item)
        self.assertEqual(
            (item["action"], item["stage"], item["step_result"]["status"]),
            ("executed", "m4", "awaiting_human"),
        )
        m4_step_run_id = item["step_run_id"]
        m4_token = item["step_result"]["resume_token"]
        disputes = self._dispute_ids(m4_step_run_id)
        self.assertTrue(disputes, "M4 停 awaiting_human 时必须有待裁决分歧")
        for dispute_id in disputes:
            record_category_ruling(
                self.service,
                m4_step_run_id,
                m4_token,
                {
                    "schema_version": CANDIDATE_SCHEMA_VERSION,
                    "dispute_id": dispute_id,
                    "choice": "a",
                    "rationale": "验收宿主：按 A 路归属裁决",
                    "actor_ref": "t04a_host",
                },
            )
        resumed = resume(self.adapter, self.registry, self.handle, m4_step_run_id, m4_token)
        self.assertEqual(resumed["status"], "succeeded")

        # M5 自动
        item = advance(self.adapter, self.registry, self.handle)
        self.assertEqual((item["action"], item["stage"]), ("executed", "m5"))
        self.assertEqual(item["step_result"]["status"], "succeeded")

        # M6 停 awaiting_human
        item = advance(self.adapter, self.registry, self.handle)
        self._note_human_stop(item)
        self.assertEqual(
            (item["action"], item["stage"], item["step_result"]["status"]),
            ("executed", "m6", "awaiting_human"),
        )
        m6_step_run_id = item["step_run_id"]
        m6_token = item["step_result"]["resume_token"]
        queue_item_ids = self._review_queue_item_ids(m6_step_run_id)
        self.assertTrue(queue_item_ids, "M6 停 awaiting_human 时审核队列不得为空")
        for queue_item_id in queue_item_ids:
            record_decision(
                self.service,
                m6_step_run_id,
                m6_token,
                queue_item_id=queue_item_id,
                verdict="accept",
                rationale="验收宿主：签发",
            )
        resumed = resume(self.adapter, self.registry, self.handle, m6_step_run_id, m6_token)
        self.assertEqual(resumed["status"], "succeeded")

        # 收口
        item = advance(self.adapter, self.registry, self.handle)
        self.assertEqual(item["action"], "complete")

        # 只有规格规定的人工节点停过 awaiting_human
        self.assertEqual(self.awaiting_stages, list(HUMAN_STAGES))

        # m1..m6 各恰 1 个阶段包，且来自生产模块、归属本运行
        for stage in EDITION_STAGES:
            descriptor = self.registry.module_for(stage)
            self.assertIsNotNone(descriptor, stage)
            self.assertNotEqual(descriptor["binding"], "imported", stage)
            rows = self.service.list_stage_packages(stage)
            self.assertEqual(len(rows), 1, "阶段 %s 的阶段包不是恰 1 个" % stage)
            step = self.service.get_step_run(rows[0]["step_run_id"])
            self.assertEqual(
                step["processing_run_id"], self.handle["processing_run_id"], stage
            )
            self.assertEqual(step["status"], "succeeded", stage)


if __name__ == "__main__":
    unittest.main()

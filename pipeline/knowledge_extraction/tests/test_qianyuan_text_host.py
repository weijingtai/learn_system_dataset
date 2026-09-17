"""R82b（第 104 条 D1–D4）：《乾元秘旨》电子文本宿主 → M4 停在 ``awaiting_human``。

抽取协议 v2（第 104 条 D2）：证据**只写** ``source_span_id`` 与 ``support_type``，
不带 ``quote``/``span_char_*``——M4 ``locate_evidence`` 即取整个片段，故两路证据键
可以对齐。某路某类别为空时如实提交 ``items: []``（第 104 条 D3）。

第 104 条 D1：M4 分歧**必须由用户人工裁决**后方能 ``resume_m4`` 封存（规格 §12:572
「未解决语义分歧进入人工队列，不能通过 M4 Gate」）。本模块**不写** ``ruling_*.yaml``、
**不调用** ``resume_m4``，只如实断言 M4 停在 ``awaiting_human``。

第 97 条口径：只认显式的电子文本宿主 ``pipeline/corpus/_fixture/qianyuan_ed01_text``，
宿主或其 ``m4/`` 提交件缺失即 ``skipTest``（写明缺什么），**绝不**回落 OCR 路线宿主
``mini_ed01``；mini_ed01 的既有用例不受本模块影响。

本模块只断言「真书宿主 + 六份提交件 → M4 ``awaiting_human``、分歧数 = 实测值、
不写 ``candidate_set``、不登记 m4 阶段包」，不比对任何金标（无人工金标，第 95 条）。
"""

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.corpus_compiler.step_offset import run_m3_text
from pipeline.digitization.step import run_m2
from pipeline.intake.source import read_source_files
from pipeline.intake.step import run_m1
from pipeline.knowledge_extraction.adapters.registry import register_technique_profile
from pipeline.knowledge_extraction.inputs import collect_submissions
from pipeline.knowledge_extraction.step import run_m4
from pipeline.knowledge_extraction.submit import run_m4_submit
from pipeline.ledger.service import LedgerService

ROOT = Path(__file__).resolve().parents[3]
HOST = ROOT / "pipeline" / "corpus" / "_fixture" / "qianyuan_ed01_text"
M4_DIR = HOST / "m4"
CANON_DIR = ROOT / "pipeline" / "schemas" / "shared" / "canon"

# 六份提交件（协议 v2；每类两路，空类别以 items: [] 如实提交）
SUBMISSION_FILES = (
    "submission_assertion_a.yaml",
    "submission_assertion_b.yaml",
    "submission_pattern_a.yaml",
    "submission_pattern_b.yaml",
    "submission_concept_mention_a.yaml",
    "submission_concept_mention_b.yaml",
)
EXPECTED_SPAN_COUNT = 696
# 实测值（持久 Ledger var/ledgers/qianyuan_w8 上同一流程跑出的 dispute_queue 条数）
EXPECTED_DISPUTE_COUNT = 24


def _missing_host_reason():
    """宿主缺失的明确原因（第 97 条：绝不回落 mini_ed01）。"""
    if not (HOST / "source_info.yaml").is_file():
        return "电子文本验收宿主缺失: %s（不得回落 mini_ed01）" % HOST
    if not M4_DIR.is_dir():
        return "电子文本 M4 提交件宿主缺失: %s（不得回落 mini_ed01）" % M4_DIR
    missing = [name for name in SUBMISSION_FILES if not (M4_DIR / name).is_file()]
    if missing:
        return "电子文本 M4 提交件缺失: %s" % ", ".join(missing)
    return None


@unittest.skipIf(_missing_host_reason() is not None, _missing_host_reason())
class QianyuanTextHostM4Tests(unittest.TestCase):
    """真书 M1→M2→M3→M4（临时 Ledger，用完即删；**不用** var/）。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="qianyuan-m4-e2e-")
        cls.service = LedgerService(Path(cls.tmp) / "ledger")
        source_info = yaml.safe_load((HOST / "source_info.yaml").read_text(encoding="utf-8"))
        cls.edition_part_id = source_info["edition_part"]["artifact_id"]
        files = read_source_files(str(HOST), source_info["pages"])
        m1 = run_m1(cls.service, source_info, files, cls.edition_part_id)
        raw_revision_id = m1["raw_text_revision_ids"][0]
        cls.m2 = run_m2(cls.service, raw_revision_id, source_info, cls.edition_part_id)
        cls.m3 = run_m3_text(cls.service, cls.edition_part_id)
        processing_run_id = cls.service.get_step_run(cls.m3["step_run_id"])["processing_run_id"]
        register_technique_profile(
            cls.service, processing_run_id, technique_id="qizheng", canon_dir=CANON_DIR
        )
        cls.submits = [
            run_m4_submit(
                cls.service,
                cls.edition_part_id,
                (M4_DIR / name).read_bytes(),
                producer_module="w8:%s" % name,
                producer_version="0.1.0",
            )
            for name in SUBMISSION_FILES
        ]
        cls.awaiting = run_m4(cls.service, cls.edition_part_id)
        cls.spans_doc = yaml.safe_load(
            cls.service.objects.get(
                cls.service.get_revision(cls.m3["spans_revision_id"])["sha256"]
            ).decode("utf-8")
        )
        # 前置守卫：真书 M1/M2/M3 未走通时后续断言无意义，直接给出明确失败原因
        if cls.m3.get("status") != "succeeded":
            raise RuntimeError(
                "真书 M3 未成功（%s）: %r" % (cls.m3.get("failed_check"), cls.m3.get("reason"))
            )
        if cls.spans_doc.get("span_count") != EXPECTED_SPAN_COUNT:
            raise RuntimeError(
                "真书 M3 片段数 %r != 期望 %d"
                % (cls.spans_doc.get("span_count"), EXPECTED_SPAN_COUNT)
            )

    @classmethod
    def tearDownClass(cls):
        cls.service.close()
        shutil.rmtree(cls.tmp, True)

    def _sealed_type(self, step_run_id, artifact_type):
        rows = self.service.store.conn.execute(
            "SELECT r.artifact_revision_id FROM artifacts a "
            "JOIN artifact_revisions r ON r.artifact_id = a.artifact_id "
            "WHERE r.step_run_id=? AND a.artifact_type=?",
            (step_run_id, artifact_type),
        ).fetchall()
        return [row[0] for row in rows]

    def test_six_submissions_registered_including_empty_lane(self):
        """六份提交件全部登记（含 pattern/a 的 ``items: []``——空类别如实提交，D3）。"""
        registered = collect_submissions(self.service, self.edition_part_id)
        self.assertEqual(
            sorted(registered),
            [
                "assertion/a",
                "assertion/b",
                "concept_mention/a",
                "concept_mention/b",
                "pattern/a",
                "pattern/b",
            ],
        )
        for summary in self.submits:
            self.assertEqual(summary["status"], "succeeded")
        empty_lane = next(row for row in self.submits if row["category"] == "pattern")
        doc = yaml.safe_load(
            self.service.objects.get(
                self.service.get_revision(empty_lane["submission_revision_id"])["sha256"]
            ).decode("utf-8")
        )
        self.assertEqual(doc["lane"], "a")
        self.assertEqual(doc["items"], [])

    def test_m4_stops_at_awaiting_human_with_measured_dispute_count(self):
        """M4 终态 ``awaiting_human``，分歧条数等于实测值（等待用户裁决，第 104 条 D1）。"""
        self.assertEqual(self.awaiting["status"], "awaiting_human")
        self.assertEqual(len(self.awaiting["dispute_ids"]), EXPECTED_DISPUTE_COUNT)
        queue = yaml.safe_load(
            self.service.objects.get(
                self.service.get_revision(self.awaiting["dispute_queue_revision_id"])["sha256"]
            ).decode("utf-8")
        )
        self.assertEqual(len(queue["disputes"]), EXPECTED_DISPUTE_COUNT)
        self.assertEqual(
            [row["dispute_id"] for row in queue["disputes"]],
            list(self.awaiting["dispute_ids"]),
        )

    def test_m4_writes_no_candidate_set(self):
        """未封存：``candidate_set`` 一条也不写。"""
        self.assertEqual(
            self._sealed_type(self.awaiting["step_run_id"], "candidate_set"), []
        )

    def test_m4_registers_no_stage_package(self):
        """未封存：``stage_packages`` 中没有任何 m4 行。"""
        rows = self.service.store.conn.execute(
            "SELECT sp.stage_package_id FROM stage_packages sp WHERE sp.stage='m4'"
        ).fetchall()
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()

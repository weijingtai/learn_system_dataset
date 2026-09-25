"""M4 薄适配入口 ``entry.run_m4``（TODO T04A 第 2 项：technique_profile 走运行输入）。

宿主：电子文本 ``pipeline/corpus/_fixture/qianyuan_ed01_text``（M1→M2→M3 经各自生产入口
在临时 Ledger 上跑出，六份提交件经公开入口 ``run_m4_submit`` 登记）。每个用例在模板
Ledger 的副本上执行，互不影响；不碰 ``var/``。

断言：技法画像只从运行输入 ``technique_profile: {technique_id, canon_dir}`` 取；本运行下
没有该技法的 ``technique_profile`` 修订时经公开函数登记一次、已有则不重复登记；拒收一律
发生在任何写入之前。
"""

import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.corpus_compiler.step_offset import run_m3_text
from pipeline.digitization.step import run_m2
from pipeline.intake.source import read_source_files
from pipeline.intake.step import run_m1
from pipeline.knowledge_extraction.adapters.registry import (
    build_technique_profile,
    register_technique_profile,
)
from pipeline.knowledge_extraction.errors import ExtractionRefused
from pipeline.knowledge_extraction.submit import run_m4_submit
from pipeline.ledger.service import LedgerService

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


def _missing_host_reason():
    if not (HOST / "source_info.yaml").is_file():
        return "电子文本宿主缺失: %s" % HOST
    missing = [name for name in SUBMISSION_FILES if not (M4_DIR / name).is_file()]
    if missing:
        return "电子文本 M4 提交件缺失: %s" % ", ".join(missing)
    return None


def _row_counts(root):
    """只读统计 ``(artifact_revisions, step_runs, audit_log)`` 行数（零写入的判据）。"""
    connection = sqlite3.connect("file:%s?mode=ro" % (root / "ledger.sqlite"), uri=True)
    try:
        return tuple(
            connection.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
            for table in ("artifact_revisions", "step_runs", "audit_log")
        )
    finally:
        connection.close()


def _run_inputs(**profile):
    technique_profile = {"technique_id": "qizheng", "canon_dir": str(CANON_DIR)}
    technique_profile.update(profile)
    return {
        "route": "text",
        "source_dir": str(HOST),
        "source_info": {"pages": []},
        "technique_profile": technique_profile,
    }


@unittest.skipIf(_missing_host_reason() is not None, _missing_host_reason())
class M4EntryTests(unittest.TestCase):
    """模板 Ledger：M1→M3 + 六份提交件（尚无 technique_profile、尚无 assemble 运行）。"""

    @classmethod
    def setUpClass(cls):
        cls._template_tmp = tempfile.mkdtemp(prefix="m4-entry-template-")
        cls.template_root = Path(cls._template_tmp) / "ledger"
        service = LedgerService(cls.template_root)
        try:
            source_info = yaml.safe_load(
                (HOST / "source_info.yaml").read_text(encoding="utf-8")
            )
            cls.edition_part_id = source_info["edition_part"]["artifact_id"]
            files = read_source_files(str(HOST), source_info["pages"])
            m1 = run_m1(service, source_info, files, cls.edition_part_id)
            run_m2(service, m1["raw_text_revision_ids"][0], source_info, cls.edition_part_id)
            m3 = run_m3_text(service, cls.edition_part_id)
            if m3.get("status") != "succeeded":
                raise RuntimeError("宿主 M3 未成功: %r" % (m3,))
            cls.processing_run_id = service.get_step_run(m3["step_run_id"])[
                "processing_run_id"
            ]
            for name in SUBMISSION_FILES:
                summary = run_m4_submit(
                    service,
                    cls.edition_part_id,
                    (M4_DIR / name).read_bytes(),
                    producer_module="m4_entry_test:%s" % name,
                    producer_version="0.1.0",
                )
                if summary["status"] != "succeeded":
                    raise RuntimeError("提交件登记失败: %s" % name)
        finally:
            service.close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._template_tmp, True)

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m4-entry-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.root = Path(self._tmp) / "ledger"
        shutil.copytree(self.template_root, self.root)
        self.service = LedgerService(self.root)
        self.addCleanup(self.service.close)

    # ------------------------------------------------------------- 只读小工具
    def _profiles(self):
        return [
            row["artifact_revision_id"]
            for row in self.service.list_revisions(
                artifact_type="technique_profile",
                processing_run_id=self.processing_run_id,
            )
        ]

    def _counts(self):
        connection = sqlite3.connect(
            "file:%s?mode=ro" % (self.root / "ledger.sqlite"), uri=True
        )
        try:
            return tuple(
                connection.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
                for table in ("artifact_revisions", "step_runs", "audit_log")
            )
        finally:
            connection.close()

    def _frozen_inputs(self, step_run_id):
        step = self.service.get_step_run(step_run_id)
        return json.loads(step["request_json"])["input_artifact_ids"]

    # ------------------------------------------------------------------ 用例
    def test_registers_profile_from_run_inputs_then_runs_m4(self):
        from pipeline.knowledge_extraction.entry import run_m4

        self.assertEqual(self._profiles(), [])
        summary = run_m4(self.service, self.edition_part_id, run_inputs=_run_inputs())
        self.assertEqual(summary["status"], "awaiting_human")
        self.assertTrue(summary["resume_token"])

        profiles = self._profiles()
        self.assertEqual(len(profiles), 1)
        row = self.service.get_revision(profiles[0])
        self.assertEqual(row["status"], "sealed")
        self.assertEqual(
            self.service.read_object(row["sha256"]),
            build_technique_profile(technique_id="qizheng", canon_dir=CANON_DIR),
        )
        self.assertIn(profiles[0], self._frozen_inputs(summary["step_run_id"]))

    def test_existing_profile_of_this_run_not_registered_again(self):
        from pipeline.knowledge_extraction.entry import run_m4

        existing = register_technique_profile(
            self.service,
            self.processing_run_id,
            technique_id="qizheng",
            canon_dir=CANON_DIR,
        )
        summary = run_m4(self.service, self.edition_part_id, run_inputs=_run_inputs())
        self.assertEqual(summary["status"], "awaiting_human")
        self.assertEqual(self._profiles(), [existing])
        self.assertIn(existing, self._frozen_inputs(summary["step_run_id"]))

    def test_refusals_happen_before_any_write(self):
        from pipeline.knowledge_extraction.entry import run_m4

        missing_canon = str(Path(self._tmp) / "no_such_canon")
        empty_canon = Path(self._tmp) / "empty_canon"
        empty_canon.mkdir()
        cases = {
            "no_run_inputs": None,
            "no_technique_profile": {"route": "text"},
            "technique_mismatch": _run_inputs(technique_id="other"),
            "canon_dir_missing": _run_inputs(canon_dir=missing_canon),
            "canon_dir_empty_string": _run_inputs(canon_dir=""),
            "canon_dir_without_yaml": _run_inputs(canon_dir=str(empty_canon)),
        }
        for label, run_inputs in cases.items():
            with self.subTest(case=label):
                before = self._counts()
                with self.assertRaises(ExtractionRefused):
                    run_m4(self.service, self.edition_part_id, run_inputs=run_inputs)
                self.assertEqual(before, self._counts())
                self.assertEqual(self._profiles(), [])


@unittest.skipIf(_missing_host_reason() is not None, _missing_host_reason())
class M4EntrySubmissionGapTests(unittest.TestCase):
    """模板 Ledger：M1→M3，**尚无任何提交件**（裁决 Q1：缺提交件 → 零写入拒收）。

    与上一个模板的区别只在“有没有提交件”：那些先拒收再交件的用例不能靠删修订实现，
    故另建一个只跑到 M3 的模板。
    """

    @classmethod
    def setUpClass(cls):
        cls._template_tmp = tempfile.mkdtemp(prefix="m4-entry-gap-template-")
        cls.template_root = Path(cls._template_tmp) / "ledger"
        service = LedgerService(cls.template_root)
        try:
            source_info = yaml.safe_load(
                (HOST / "source_info.yaml").read_text(encoding="utf-8")
            )
            cls.edition_part_id = source_info["edition_part"]["artifact_id"]
            files = read_source_files(str(HOST), source_info["pages"])
            m1 = run_m1(service, source_info, files, cls.edition_part_id)
            run_m2(
                service,
                m1["raw_text_revision_ids"][0],
                source_info,
                cls.edition_part_id,
            )
            m3 = run_m3_text(service, cls.edition_part_id)
            if m3.get("status") != "succeeded":
                raise RuntimeError("宿主 M3 未成功: %r" % (m3,))
        finally:
            service.close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._template_tmp, True)

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="m4-entry-gap-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.root = Path(self._tmp) / "ledger"
        shutil.copytree(self.template_root, self.root)
        self.service = LedgerService(self.root)
        self.addCleanup(self.service.close)

    def _counts(self):
        return _row_counts(self.root)

    def _profiles(self):
        return [
            row["artifact_revision_id"]
            for row in self.service.list_revisions(artifact_type="technique_profile")
        ]

    def _submit(self, name):
        summary = run_m4_submit(
            self.service,
            self.edition_part_id,
            (M4_DIR / name).read_bytes(),
            producer_module="m4_entry_gap:%s" % name,
            producer_version="0.1.0",
        )
        self.assertEqual(summary["status"], "succeeded")

    def test_no_submissions_is_a_zero_write_refusal_pointing_at_run_m4_submit(self):
        """一份提交件都没有：入口返回零写入拒收，理由写明出路 ``run_m4_submit``。"""
        from pipeline.knowledge_extraction.entry import run_m4

        before = self._counts()
        result = run_m4(self.service, self.edition_part_id, run_inputs=_run_inputs())

        self.assertEqual(result["refused"], True)
        self.assertIn("run_m4_submit", result["reason"], "拒收必须写明怎么解")
        self.assertIn("REF_001", result["reason"])
        self.assertEqual(result.get("step_run_id"), None, "拒收不建 StepRun")
        self.assertEqual(before, self._counts(), "拒收发生在任何写入之前")
        self.assertEqual(self._profiles(), [], "拒收时也不得登记技法画像")

    def test_partial_submissions_are_refused_not_taken_as_complete(self):
        """只交 3/6（每类只有 a 路）：M4 自己拒收（REF_*），零写入且不反复调起。"""
        from pipeline.knowledge_extraction.entry import run_m4

        for name in (
            "submission_assertion_a.yaml",
            "submission_pattern_a.yaml",
            "submission_concept_mention_a.yaml",
        ):
            self._submit(name)

        before = self._counts()
        first = run_m4(self.service, self.edition_part_id, run_inputs=_run_inputs())
        self.assertEqual(first["refused"], True)
        self.assertIn("缺必需路", first["reason"])
        self.assertIn("REF_001", first["reason"])
        self.assertIn("run_m4_submit", first["reason"])
        self.assertEqual(before, self._counts(), "不齐不得当齐，拒收零写入")
        self.assertEqual(self._profiles(), [])

        second = run_m4(self.service, self.edition_part_id, run_inputs=_run_inputs())
        self.assertEqual(second, first, "再调一次仍是同样的拒收（不建 StepRun、不重试）")
        self.assertEqual(before, self._counts(), "反复调起不得新增修订")

    def test_refusal_disappears_once_all_six_submissions_are_registered(self):
        """补齐 6/6 后拒收消失：入口正常跑 M4（停在人工队列）。"""
        from pipeline.knowledge_extraction.entry import run_m4

        for name in SUBMISSION_FILES:
            self._submit(name)
        summary = run_m4(self.service, self.edition_part_id, run_inputs=_run_inputs())
        self.assertEqual(summary["status"], "awaiting_human")
        self.assertNotIn("refused", summary)
        self.assertEqual(len(self._profiles()), 1)


if __name__ == "__main__":
    unittest.main()

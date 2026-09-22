"""ACT 19 Q3：M5 Gate 扫描 M4 提交件 adapter_notes 的截断自述。

先红后绿。本文件在 `pipeline.validation.adapter_notes` 落地前必须整份 ImportError。

背景：`adapter_notes` 是抽取员写「我略去了什么」的字段，此前**无任何下游消费者**
（死数据）。本检查给 M5 Gate 接上第一条消费者：命中截断自述即产出一条 error 发现，
经 `gate_summary` / `assemble_gate_results` 变成返工任务，`gate.passed` 转假——
**不得静默通过**。
"""

import json
import os
import types
import unittest

import yaml

from pipeline.validation.adapter_notes import (
    CHECK_NAME,
    GATE,
    TRUNCATION_MARKERS,
    findings_from_hits,
    markers_from_env,
    scan_documents,
    submission_documents,
)
from pipeline.validation.findings import gate_summary
from pipeline.validation.package import assemble_gate_results
from pipeline.validation.registry import CHECK_CODES

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
M4_DIR = os.path.join(REPO_ROOT, "corpus/_fixture/qianyuan_ed01_text/m4")

# 真书 b 路提交件里那条自述（逐字，见 m4/submission_concept_mention_b.yaml）
REAL_TRUNCATION_NOTE = (
    "抽取员 notes：十神名（伤官、食神、正财、偏财、偏印、正印、劫财）亦属专门术语，"
    "但受 20 条上限所限未逐一登记，仅登记天官、七煞、化禄。"
)
REAL_TRANSFORM_NOTE = (
    "主 Agent 按第 100 条 D4、第 104 条 D2/D3 机械转换：抽取件顶层 lane/model/notes "
    "转入 producer 与本字段，items 原样未改；空类别如实提交 items: []"
)
# 真书 a 路提交件里那条「跳过某片段」的说明：不是截断自述，不得误报
CLEAN_NOTE = (
    "抽取员 notes：跳过 ss_qianyuan_ed01_o0008670（「等天官者何？」为设问句，"
    "无独立论断内容，其答案已由下一片段承载）。"
)

LEVELS = ("INTERNAL_DEMO", "DEV_SEARCH", "PUBLIC_RELEASE")


def _submission(revision_id, notes):
    doc = {
        "schema_version": "0.1.0-draft",
        "category": "concept_mention",
        "lane": "b",
        "items": [{"surface": "天官", "evidence": [{"source_span_id": "ss_x_o0000001"}]}],
        "adapter_notes": list(notes),
    }
    return revision_id, doc


class TruncationScanTest(unittest.TestCase):
    def test_m5_gate_flags_adapter_notes_truncation(self):
        """命中截断自述 → error 发现 + 返工任务，M5 Gate **不得静默通过**。"""
        hits = scan_documents(
            [_submission("rev_a", [REAL_TRANSFORM_NOTE, REAL_TRUNCATION_NOTE])]
        )
        self.assertEqual(len(hits), 1)
        self.assertIn("上限", hits[0]["markers"])
        self.assertIn("未逐一登记", hits[0]["markers"])

        findings = findings_from_hits(hits)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["check"], CHECK_NAME)
        self.assertEqual(finding["gate"], GATE)
        self.assertIsNone(finding["code"], "如实披露项不得伪挂 §8.2 错误码")
        self.assertIsNotNone(finding["rework_stage"], "命中即置待处理（返工任务）")
        self.assertEqual(finding["subject"]["artifact_revision_id"], "rev_a")
        for level in LEVELS:
            self.assertEqual(
                finding["severity"][level], "error", "%s 级不得冒充 ok" % level
            )

        target = "INTERNAL_DEMO"
        gate = gate_summary(target, findings, [])
        self.assertFalse(gate["passed"], "命中后 gate.passed 必须为假")
        self.assertEqual(gate["severe_error_count"], 1)
        self.assertEqual(gate["pending_rework_count"], 1)

        results = assemble_gate_results(
            {level: "failed" for level in LEVELS},
            findings,
            [],
            target_consumption_level=target,
        )
        self.assertEqual([f["check"] for f in results["failures"]], [CHECK_NAME])
        self.assertEqual([t["check"] for t in results["rework_tasks"]], [CHECK_NAME])
        self.assertEqual(results["gates"][GATE], "failed")

    def test_m5_gate_adapter_notes_clean_passes(self):
        """无截断自述（仅机械转换注记 / 跳过说明）→ 无发现，Gate 不受影响。"""
        hits = scan_documents([_submission("rev_a", [REAL_TRANSFORM_NOTE, CLEAN_NOTE])])
        self.assertEqual(hits, [])
        findings = findings_from_hits(hits)
        self.assertEqual(findings, [])
        gate = gate_summary("INTERNAL_DEMO", findings, [])
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["pending_rework_count"], 0)

    def test_no_submissions_at_all_changes_nothing(self):
        """账本里没有 M4 提交件时（夹具/OCR 档），本检查不产生任何发现。"""
        self.assertEqual(scan_documents([]), [])
        self.assertEqual(findings_from_hits([]), [])
        self.assertTrue(gate_summary("INTERNAL_DEMO", [], [])["passed"])

    def test_check_name_registered_without_error_code(self):
        """检查名必须登记进 registry 闭集；如实披露项取 None（§5.5 缺口同类）。"""
        self.assertIn(CHECK_NAME, CHECK_CODES)
        self.assertIsNone(CHECK_CODES[CHECK_NAME])

    def test_markers_are_centralized_and_configurable(self):
        """词表集中定义、可整体覆盖（不许散落在多处硬编码）。"""
        self.assertEqual(
            tuple(TRUNCATION_MARKERS), ("控总数", "上限", "略去", "未逐一登记")
        )
        hits = scan_documents([_submission("rev_a", [CLEAN_NOTE])], markers=("跳过",))
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["markers"], ["跳过"])
        self.assertEqual(scan_documents([_submission("rev_a", [CLEAN_NOTE])]), [])
        self.assertEqual(
            markers_from_env({"M5_ADAPTER_NOTES_MARKERS": "跳过, 略去"}), ("跳过", "略去")
        )
        self.assertEqual(markers_from_env({}), tuple(TRUNCATION_MARKERS))
        self.assertEqual(markers_from_env({"M5_ADAPTER_NOTES_MARKERS": " , "}),
                         tuple(TRUNCATION_MARKERS))

    def test_real_book_submission_notes_are_flagged(self):
        """直接用入库提交件（真书 b 路 / a 路）跑：逐条自述命中，a 路的「跳过」不误报。"""
        with open(os.path.join(M4_DIR, "submission_assertion_b.yaml"), encoding="utf-8") as fh:
            lane_b = yaml.safe_load(fh)
        hits = scan_documents([("rev_b", lane_b)])
        # b 路 11 条 notes 里 4 条是截断自述（3 条「为控总数略去」+ 1 条「受 20 条上限所限」）
        self.assertEqual(len(hits), 4)
        capped = [hit for hit in hits if "未逐一登记" in hit["markers"]]
        self.assertEqual(len(capped), 1)
        self.assertIn("十神名", capped[0]["note"])
        self.assertEqual(capped[0]["markers"], ["上限", "未逐一登记"])
        self.assertEqual(
            {marker for hit in hits for marker in hit["markers"]},
            {"控总数", "上限", "略去", "未逐一登记"},
        )
        self.assertEqual(hits[0]["lane"], "b")

        with open(os.path.join(M4_DIR, "submission_assertion_a.yaml"), encoding="utf-8") as fh:
            lane_a = yaml.safe_load(fh)
        self.assertEqual(scan_documents([("rev_a", lane_a)]), [], "a 路无截断自述")


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)


class _Conn:
    """只读 SELECT 桩：按 ``artifact_type`` 返回 ``(revision_id, artifact_type)``。"""

    def __init__(self, types_by_revision):
        self._types = types_by_revision

    def execute(self, _sql, params):
        wanted = set(params)
        return _Cursor(
            [(rev, kind) for rev, kind in self._types.items() if rev in wanted]
        )


class _Reader:
    """`submission_documents` 所需的最小只读接口桩（不建真账本）。"""

    def __init__(self, checkpoints, step_runs, types_by_revision, objects):
        self.store = types.SimpleNamespace(conn=_Conn(types_by_revision))
        self.objects = types.SimpleNamespace(get=lambda sha: objects[sha])
        self._checkpoints = checkpoints
        self._step_runs = step_runs
        self._revision_rows = {"rev_sub_b": {"sha256": "sha_b"}}

    def list_checkpoints(self, edition_part_id, stage):
        return self._checkpoints.get((edition_part_id, stage), [])

    def get_step_run(self, step_run_id):
        return self._step_runs.get(step_run_id)

    def get_revision(self, revision_id):
        return self._revision_rows.get(revision_id)


def _reader(status="succeeded"):
    request = json.dumps({"input_artifact_ids": ["rev_sub_b", "rev_other"]})
    return _Reader(
        checkpoints={("art_1", "m4"): [{"content": {"step_run_id": "srun_m4"}}]},
        step_runs={"srun_m4": {"status": status, "request_json": request}},
        types_by_revision={
            "rev_sub_b": "candidate_submission",
            "rev_other": "corpus_spans",
        },
        objects={
            "sha_b": yaml.safe_dump(
                {"adapter_notes": [REAL_TRUNCATION_NOTE]}, allow_unicode=True
            ).encode("utf-8")
        },
    )


class SubmissionLookupTest(unittest.TestCase):
    """提交件定位只读、只认 succeeded 的 m4 Checkpoint。"""

    def test_reads_submissions_from_succeeded_m4_step_run(self):
        docs = submission_documents(_reader(), "art_1")
        self.assertEqual([rev for rev, _doc in docs], ["rev_sub_b"])
        self.assertEqual(docs[0][1]["adapter_notes"], [REAL_TRUNCATION_NOTE])

    def test_ignores_non_succeeded_m4_step_run(self):
        self.assertEqual(submission_documents(_reader(status="failed"), "art_1"), [])

    def test_no_m4_checkpoint_yields_nothing(self):
        self.assertEqual(submission_documents(_reader(), "art_other"), [])

    def test_end_to_end_flags_from_ledger_documents(self):
        findings = findings_from_hits(
            scan_documents(submission_documents(_reader(), "art_1"))
        )
        self.assertEqual([f["check"] for f in findings], [CHECK_NAME])


if __name__ == "__main__":
    unittest.main()

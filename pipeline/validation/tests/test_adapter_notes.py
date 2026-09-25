"""ACT 19 Q3：M5 Gate 扫描 M4 提交件 adapter_notes 的截断自述。

先红后绿。本文件在 `pipeline.validation.adapter_notes` 落地前必须整份 ImportError。

背景：`adapter_notes` 是抽取员写「我略去了什么」的字段，此前**无任何下游消费者**
（死数据）。本检查给 M5 Gate 接上第一条消费者，且按第 109 条分两级：

- 命中截断词且**逐条点名**（注记含真实片段 ID 或「（…）」括号术语表）→ 披露项，
  `warning`，进 `gate_results.warnings` 如实列出，**不进返工任务**，`gate.passed`
  不受影响（`G3 = passed_with_warnings`）；
- 命中截断词但**未逐条点名** → `error` + 返工任务，`gate.passed` 转假——
  **不得静默通过**。
"""

import json
import os
import re
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
from pipeline.validation.findings import gate_summary, level_verdicts
from pipeline.validation.package import assemble_gate_results
from pipeline.validation.registry import CHECK_CODES

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
M4_DIR = os.path.join(REPO_ROOT, "corpus/_fixture/qianyuan_ed01_text/m4")

# 真书 b 路提交件里那条自述（逐字，见 m4/submission_concept_mention_b.yaml）：
# 无片段 ID，但**括号内逐个点名**了被 20 条上限截掉的是哪些术语
REAL_TRUNCATION_NOTE = (
    "抽取员 notes：十神名（伤官、食神、正财、偏财、偏印、正印、劫财）亦属专门术语，"
    "但受 20 条上限所限未逐一登记，仅登记天官、七煞、化禄。"
)
# 真书 b 路提交件里那条「为控总数略去」的自述（逐字）：**逐个点名**了被略去的片段 ID
REAL_ITEMIZED_SPAN_NOTE = (
    "抽取员 notes：ss_qianyuan_ed01_o0008946、ss_qianyuan_ed01_o0008984、"
    "ss_qianyuan_ed01_o0009004、ss_qianyuan_ed01_o0009014、ss_qianyuan_ed01_o0009028 "
    "为《天官经》天官贵格类韵语，与已抽条目义近，为控总数略去。"
)
# 合成：命中截断词却**未逐条点名**（无片段 ID、无括号术语表）——仍须阻断
UNITEMIZED_NOTE = "抽取员 notes：另有数条韵语与已抽条目义近，为控总数略去，未逐条点名。"

# 篡改探针用：抹掉片段 ID 与「（…）」术语表，其余逐字不动
_SPAN_TOKEN_RE = re.compile(r"ss_[a-z0-9_]+[、,，]*")
_TERM_LIST_RE = re.compile(r"（[^（）]*）")


def _without_itemization(note):
    return _TERM_LIST_RE.sub("", _SPAN_TOKEN_RE.sub("", note))


def _load_submission(name):
    with open(os.path.join(M4_DIR, name), encoding="utf-8") as handle:
        return yaml.safe_load(handle)
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
    def test_unitemized_truncation_is_an_error_and_blocks(self):
        """命中但未逐条点名 → error 发现 + 返工任务，M5 Gate **不得静默通过**。"""
        hits = scan_documents([_submission("rev_a", [REAL_TRANSFORM_NOTE, UNITEMIZED_NOTE])])
        self.assertEqual(len(hits), 1)
        self.assertFalse(hits[0]["itemized"], "无片段 ID、无括号术语表即未点名")
        self.assertIn("控总数", hits[0]["markers"])
        self.assertIn("略去", hits[0]["markers"])

        findings = findings_from_hits(hits)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["check"], CHECK_NAME)
        self.assertEqual(finding["gate"], GATE)
        self.assertIsNone(finding["code"], "如实披露项不得伪挂 §8.2 错误码")
        self.assertIsNotNone(finding["rework_stage"], "未点名即置待处理（返工任务）")
        self.assertEqual(finding["subject"]["artifact_revision_id"], "rev_a")
        self.assertTrue(finding["detail"].startswith("未逐条点名"), finding["detail"])
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
        self.assertEqual(results["warnings"], [])
        self.assertEqual(results["gates"][GATE], "failed")

    def test_itemized_truncation_is_a_disclosure_warning(self):
        """逐条点名（片段 ID 或括号术语表）→ warning：如实列出但**不阻断** M5。"""
        hits = scan_documents(
            [
                _submission(
                    "rev_a",
                    [REAL_TRANSFORM_NOTE, REAL_ITEMIZED_SPAN_NOTE, REAL_TRUNCATION_NOTE],
                )
            ]
        )
        self.assertEqual(len(hits), 2, "机械转换注记不作数")
        self.assertTrue(all(hit["itemized"] for hit in hits))
        self.assertTrue(any("ss_" in hit["note"] for hit in hits), "一条靠片段 ID 点名")
        self.assertTrue(any("（" in hit["note"] for hit in hits), "一条靠括号术语表点名")

        findings = findings_from_hits(hits)
        self.assertEqual(len(findings), 2)
        for finding in findings:
            self.assertEqual(finding["check"], CHECK_NAME)
            self.assertEqual(finding["gate"], GATE)
            self.assertIsNone(finding["code"])
            self.assertIsNone(finding["rework_stage"], "披露项不置返工任务")
            self.assertTrue(finding["detail"].startswith("已逐条点名"), finding["detail"])
            for level in LEVELS:
                self.assertEqual(finding["severity"][level], "warning")

        target = "INTERNAL_DEMO"
        gate = gate_summary(target, findings, [])
        self.assertTrue(gate["passed"], "warning 不得阻断 gate")
        self.assertEqual(gate["severe_error_count"], 0)
        self.assertEqual(gate["pending_rework_count"], 0)
        self.assertEqual(
            level_verdicts(findings, []), {level: "passed" for level in LEVELS}
        )

        results = assemble_gate_results(
            level_verdicts(findings, []),
            findings,
            [],
            target_consumption_level=target,
        )
        self.assertEqual(results["failures"], [])
        self.assertEqual([f["check"] for f in results["warnings"]], [CHECK_NAME, CHECK_NAME])
        self.assertEqual(results["rework_tasks"], [])
        self.assertEqual(results["gates"][GATE], "passed_with_warnings")
        self.assertEqual(results["counts"]["failures"], 0)
        self.assertEqual(results["counts"]["warnings"], 2)

    def test_removing_itemization_turns_disclosure_back_into_error(self):
        """篡改探针：同一注记去掉片段 ID / 括号术语表后，warning 必须转回 error。"""
        target = "INTERNAL_DEMO"
        for note in (REAL_ITEMIZED_SPAN_NOTE, REAL_TRUNCATION_NOTE):
            itemized_hits = scan_documents([_submission("rev_a", [note])])
            self.assertEqual(len(itemized_hits), 1, note)
            self.assertTrue(itemized_hits[0]["itemized"], note)
            self.assertEqual(
                findings_from_hits(itemized_hits)[0]["severity"][target], "warning"
            )

            stripped = _without_itemization(note)
            self.assertNotIn("ss_", stripped)
            self.assertNotIn("（", stripped)
            stripped_hits = scan_documents([_submission("rev_a", [stripped])])
            self.assertEqual(len(stripped_hits), 1, "抹掉点名后仍是截断自述")
            self.assertFalse(stripped_hits[0]["itemized"], stripped)
            finding = findings_from_hits(stripped_hits)[0]
            self.assertEqual(finding["severity"][target], "error", stripped)
            self.assertIsNotNone(finding["rework_stage"], stripped)
            self.assertFalse(gate_summary(target, [finding], [])["passed"])

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
        """直接用入库提交件（真书 b 路 / a 路）跑：4 条自述全检出、全逐条点名、a 路「跳过」不误报。"""
        lane_b = _load_submission("submission_assertion_b.yaml")
        hits = scan_documents([("rev_b", lane_b)])
        # b 路 11 条 notes 里 4 条是截断自述（3 条「为控总数略去」+ 1 条「受 20 条上限所限」）
        self.assertEqual(len(hits), 4)
        self.assertTrue(all(hit["itemized"] for hit in hits), "宿主自述逐条点名，属披露项")
        capped = [hit for hit in hits if "未逐一登记" in hit["markers"]]
        self.assertEqual(len(capped), 1)
        self.assertIn("十神名", capped[0]["note"])
        self.assertEqual(capped[0]["markers"], ["上限", "未逐一登记"])
        self.assertEqual(
            {marker for hit in hits for marker in hit["markers"]},
            {"控总数", "上限", "略去", "未逐一登记"},
        )
        self.assertEqual(hits[0]["lane"], "b")

        findings = findings_from_hits(hits)
        self.assertEqual(len(findings), 4)
        for level in LEVELS:
            self.assertTrue(
                all(f["severity"][level] == "warning" for f in findings),
                "%s 级：宿主逐条点名，如实披露而不阻断" % level,
            )
        gate = gate_summary("INTERNAL_DEMO", findings, [])
        self.assertTrue(gate["passed"], "宿主 4 条披露项不得阻断 M5")
        self.assertEqual(gate["severe_error_count"], 0)
        self.assertEqual(gate["pending_rework_count"], 0)

        lane_a = _load_submission("submission_assertion_a.yaml")
        self.assertEqual(scan_documents([("rev_a", lane_a)]), [], "a 路无截断自述")


class _Reader:
    """`submission_documents` 所需的最小只读接口桩（不建真账本）。

    TODO.md T03：只提供 LedgerPort 方法，**故意不提供** ``store`` / ``objects``——
    模块若还绕过端口直读，这里会立即 AttributeError。
    """

    def __init__(self, checkpoints, step_runs, types_by_revision, objects, revision_rows=None):
        self._types_by_revision = types_by_revision
        self._objects = objects
        self._checkpoints = checkpoints
        self._step_runs = step_runs
        self._revision_rows = (
            {"rev_sub_b": {"sha256": "sha_b"}}
            if revision_rows is None
            else revision_rows
        )

    def list_checkpoints(self, edition_part_id, stage):
        return self._checkpoints.get((edition_part_id, stage), [])

    def get_step_run(self, step_run_id):
        return self._step_runs.get(step_run_id)

    def get_revision(self, revision_id):
        return self._revision_rows.get(revision_id)

    def describe_revision(self, revision_id):
        artifact_type = self._types_by_revision.get(revision_id)
        return None if artifact_type is None else {"artifact_revision_id": revision_id, "artifact_type": artifact_type}

    def read_object(self, sha256):
        return self._objects[sha256]


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
        # 该桩里的注记是宿主「十神名（…）」条：逐条点名 → 披露项（warning）
        self.assertEqual(findings[0]["severity"]["INTERNAL_DEMO"], "warning")
        self.assertTrue(findings[0]["detail"].startswith("已逐条点名"))


def _repeated_checkpoint_reader(step_run_count=1, checkpoints=32):
    """真书账本口径的桩：同一 M4 StepRun 被多个 Checkpoint 重复登记。

    六份宿主提交件（3 份带 4 条截断自述的 b 路、3 份干净的 a 路）挂在 succeeded 的 m4
    StepRun 上；每个 StepRun 被 ``checkpoints`` 个 Checkpoint 登记（真书实测：M4 assemble
    的 38 个 Checkpoint 全指同一 StepRun，未去重时 6×32=192、命中 12×32=384）。
    """
    noisy = _load_submission("submission_assertion_b.yaml")
    clean = _load_submission("submission_assertion_a.yaml")
    objects, revision_rows, types_by_revision = {}, {}, {}
    for index in range(6):
        revision_id, sha256 = "rev_%d" % index, "sha_%d" % index
        objects[sha256] = yaml.safe_dump(
            noisy if index < 3 else clean, allow_unicode=True
        ).encode("utf-8")
        revision_rows[revision_id] = {"sha256": sha256}
        types_by_revision[revision_id] = "candidate_submission"
    request = json.dumps({"input_artifact_ids": list(revision_rows)})
    step_runs = {
        "srun_m4_%d" % index: {"status": "succeeded", "request_json": request}
        for index in range(step_run_count)
    }
    checkpoint_rows = [
        {"content": {"step_run_id": "srun_m4_%d" % (index % step_run_count)}}
        for index in range(checkpoints * step_run_count)
    ]
    return _Reader(
        checkpoints={("art_1", "m4"): checkpoint_rows},
        step_runs=step_runs,
        types_by_revision=types_by_revision,
        objects=objects,
        revision_rows=revision_rows,
    )


class RepeatedRegistrationTest(unittest.TestCase):
    """同一 M4 StepRun 被重复登记时只计一次（192→6 / 384→12，依第 109 条）。"""

    def test_each_m4_step_run_is_counted_once(self):
        documents = submission_documents(_repeated_checkpoint_reader(), "art_1")
        self.assertEqual(len(documents), 6, "同一 StepRun 重复登记 32 次只计一次")
        self.assertEqual(
            sorted(revision_id for revision_id, _doc in documents),
            ["rev_%d" % index for index in range(6)],
        )

        hits = scan_documents(documents)
        self.assertEqual(len(hits), 12, "3 份 × 4 条（未去重时 12×32=384）")
        self.assertEqual(
            sorted({hit["artifact_revision_id"] for hit in hits}),
            ["rev_0", "rev_1", "rev_2"],
        )

    def test_distinct_step_runs_are_still_counted_separately(self):
        """去重只按 StepRun：两个不同 StepRun 各自登记的提交件仍各自计数（不误并）。"""
        documents = submission_documents(
            _repeated_checkpoint_reader(step_run_count=2), "art_1"
        )
        self.assertEqual(len(documents), 12)
        self.assertEqual(len(scan_documents(documents)), 24)

    def test_repeated_checkpoint_does_not_change_findings(self):
        """去重后产出与「每份提交件恰好登记一次」逐条一致。"""
        once = findings_from_hits(
            scan_documents(submission_documents(_repeated_checkpoint_reader(), "art_1"))
        )
        self.assertEqual(len(once), 12)
        self.assertTrue(all(f["check"] == CHECK_NAME for f in once))
        self.assertTrue(all(f["severity"]["INTERNAL_DEMO"] == "warning" for f in once))


if __name__ == "__main__":
    unittest.main()

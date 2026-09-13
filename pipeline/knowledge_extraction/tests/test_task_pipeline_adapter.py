"""ACT 00 任务管线 Adapter（normalize_task_output / export_task_inputs）单测（先红后绿）。"""

import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from pipeline.knowledge_extraction import serialize
from pipeline.knowledge_extraction.adapters.task_pipeline import (
    export_task_inputs,
    normalize_task_output,
)
from pipeline.knowledge_extraction.errors import ExtractionRefused
from pipeline.ledger.errors import SchemaViolation

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_SPANS = ROOT / "pipeline" / "corpus" / "_fixture" / "mini_ed01" / "spans.yaml"

PRODUCER = {"kind": "human", "name": "local_owner"}


def _assertion(**overrides):
    item = {
        "proposition": "宋錢如璧撰",
        "relation": "supports",
        "evidence": [
            {"source_span_id": "ss_sanche_ed01_p0001_s02", "support_type": "direct"}
        ],
    }
    item.update(overrides)
    return item


class TaskPipelineAdapterTests(unittest.TestCase):
    def _normalize(self, doc, **kwargs):
        params = dict(
            category="assertion",
            lane="a",
            channel="task_pipeline_manual",
            technique_id="qizheng",
            producer=PRODUCER,
        )
        params.update(kwargs)
        return normalize_task_output(doc, **params)

    def test_normalize_handbook_assertions_doc(self):
        doc = {
            "assertions": [
                {
                    "assertion_id": "as_qizheng_000001",
                    "proposition_id": "pr_qizheng_000001",
                    "proposition": "宋錢如璧撰",
                    "relation": "supports",
                    "concept_ids": ["co_shared_branch_05"],
                    "canon_refs": ["co_shared_branch_05"],
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0001_s02",
                            "support_type": "direct",
                        }
                    ],
                },
                {
                    "assertion_id": "as_qizheng_000002",
                    "proposition_id": "pr_qizheng_000002",
                    "proposition": "三辰通載三十卷",
                    "relation": "supports",
                    "concept_ids": [],
                    "canon_refs": [],
                    "evidence": [
                        {
                            "source_span_id": "ss_sanche_ed01_p0001_s04",
                            "support_type": "direct",
                        }
                    ],
                },
            ]
        }
        result = self._normalize(doc)
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0]["concept_refs"], ["co_shared_branch_05"])
        self.assertEqual(
            result["adapter_notes"],
            [
                "丢弃 assertion_id（M4 重新分配或首切片不收）",
                "丢弃 canon_refs（M4 重新分配或首切片不收）",
                "丢弃 proposition_id（M4 重新分配或首切片不收）",
            ],
        )

    def test_skipped_segments_preserved(self):
        doc = {"assertions": [_assertion()], "skipped_segments": ["s005"]}
        result = self._normalize(doc)
        self.assertEqual(result["skipped"], ["s005"])

    def test_new_concept_candidates_become_concept_mention_items(self):
        doc = {
            "new_concept_candidates": [
                {"surface": "身宮", "source_span_id": "ss_sanche_ed01_p0003_s12"}
            ]
        }
        result = self._normalize(doc, category="concept_mention")
        item = result["items"][0]
        self.assertEqual(item["surface"], "身宮")
        self.assertIsNone(item["concept_ref"])
        self.assertEqual(item["evidence"][0]["quote"], "身宮")

    def test_seg_id_without_map_SCH_001(self):
        doc = {"new_concept_candidates": [{"surface": "身宮", "seg_id": "s012"}]}
        with self.assertRaises(SchemaViolation) as ctx:
            self._normalize(doc, category="concept_mention")
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_normalize_rejects_expert_verified_status(self):
        doc = {"assertions": [_assertion(status="expert_verified")]}
        with self.assertRaises(SchemaViolation) as ctx:
            self._normalize(doc)
        self.assertEqual(ctx.exception.code, "SCH_002")

    def test_export_task_inputs_writes_four_files_deterministic(self):
        spans_doc = yaml.safe_load(FIXTURE_SPANS.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "INSTRUCTIONS.src"
            template.write_bytes("# 工位 5 指令模板（测试替身）\n".encode("utf-8"))
            outs = []
            for name in ("a", "b"):
                out = Path(tmp) / name
                out.mkdir()
                paths = export_task_inputs(
                    spans_doc,
                    out_dir=out,
                    task_id="task_assertion_a",
                    category="assertion",
                    lane="a",
                    technique_id="qizheng",
                    template_path=template,
                    id_range={"assertion": [1, 99]},
                    instruction_version="stage5_assertions@1",
                )
                outs.append(out)
                self.assertEqual(
                    list(paths),
                    [
                        "INSTRUCTIONS.md",
                        "input/segments.yaml",
                        "input/spans.yaml",
                        "task.yaml",
                    ],
                )
            self.assertEqual(
                (outs[0] / "INSTRUCTIONS.md").read_bytes(), template.read_bytes()
            )
            segments = yaml.safe_load(
                (outs[0] / "input" / "segments.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(len(segments["segments"]), 43)
            self.assertEqual(
                [row["span_id"] for row in segments["segments"]],
                [span["span_id"] for span in spans_doc["spans"]],
            )
            for rel in (
                "INSTRUCTIONS.md",
                "input/segments.yaml",
                "input/spans.yaml",
                "task.yaml",
            ):
                self.assertEqual(
                    (outs[0] / rel).read_bytes(), (outs[1] / rel).read_bytes()
                )
            with self.assertRaises(ExtractionRefused) as ctx:
                export_task_inputs(
                    spans_doc,
                    out_dir=outs[0],
                    task_id="task_assertion_a",
                    category="assertion",
                    lane="a",
                    technique_id="qizheng",
                    template_path=template,
                    id_range={"assertion": [1, 99]},
                    instruction_version="stage5_assertions@1",
                )
            self.assertEqual(ctx.exception.code, "SCH_002")

    def test_canonical_json_sort_keys_and_unicode(self):
        self.assertEqual(
            serialize.canonical_json({"b": 1, "a": "中"}),
            '{"a":"中","b":1}'.encode("utf-8"),
        )
        self.assertEqual(
            serialize.sha256_hex(b"abc"), hashlib.sha256(b"abc").hexdigest()
        )


if __name__ == "__main__":
    unittest.main()

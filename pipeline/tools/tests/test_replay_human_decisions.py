"""Tests for pipeline/tools/replay_human_decisions.py.

用小夹具证明：
1. M4 分歧数量不等时停手（ReplayMismatchError）
2. M4 分歧 ID 集合不等时停手（ReplayMismatchError）
3. M4 候选内容不等时停手（ReplayMismatchError）
4. M6 审核目标集合不等时停手（ReplayMismatchError）
5. 对得上就逐字照抄（M4 类别裁决 + M6 审核决定逐字登记入账本）
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.contract_registry.ports import DirectLedgerAdapter
from pipeline.knowledge_extraction import CANDIDATE_SCHEMA_VERSION
from pipeline.ledger import ids
from pipeline.tools.replay_human_decisions import (
    ReplayMismatchError,
    replay_m4_rulings,
    replay_m6_decisions,
    verify_m4_disputes,
    verify_m6_targets,
)


class TestReplayHumanDecisionsUnit(unittest.TestCase):
    """小夹具纯逻辑/对位规则四种不等停手测试。"""

    def test_m4_dispute_count_mismatch_stops(self):
        """1. M4 分歧数量不等：停手并抛出 ReplayMismatchError。"""
        new_disputes = [
            {"dispute_id": "m4_d001", "a": [{"prop": "A1"}], "b": [{"prop": "B1"}]},
        ]
        old_disputes = [
            {"dispute_id": "m4_d001", "a": [{"prop": "A1"}], "b": [{"prop": "B1"}]},
            {"dispute_id": "m4_d002", "a": [{"prop": "A2"}], "b": [{"prop": "B2"}]},
        ]
        with self.assertRaises(ReplayMismatchError) as ctx:
            verify_m4_disputes(new_disputes, old_disputes)
        self.assertIn("数量不等", str(ctx.exception))

    def test_m4_dispute_id_set_mismatch_stops(self):
        """2. M4 分歧 ID 集合不等：停手并抛出 ReplayMismatchError。"""
        new_disputes = [
            {"dispute_id": "m4_d001", "a": [{"prop": "A1"}], "b": [{"prop": "B1"}]},
        ]
        old_disputes = [
            {"dispute_id": "m4_d002", "a": [{"prop": "A1"}], "b": [{"prop": "B1"}]},
        ]
        with self.assertRaises(ReplayMismatchError) as ctx:
            verify_m4_disputes(new_disputes, old_disputes)
        self.assertIn("ID 集合不等", str(ctx.exception))

    def test_m4_candidate_content_mismatch_stops(self):
        """3. M4 候选内容不等：停手并抛出 ReplayMismatchError。"""
        new_disputes = [
            {"dispute_id": "m4_d001", "a": [{"prop": "A1_NEW"}], "b": [{"prop": "B1"}]},
        ]
        old_disputes = [
            {"dispute_id": "m4_d001", "a": [{"prop": "A1_OLD"}], "b": [{"prop": "B1"}]},
        ]
        with self.assertRaises(ReplayMismatchError) as ctx:
            verify_m4_disputes(new_disputes, old_disputes)
        self.assertIn("候选内容不等", str(ctx.exception))

    def test_m6_target_set_mismatch_stops(self):
        """4. M6 目标集合不等：停手并抛出 ReplayMismatchError。"""
        new_queue_items = [
            {
                "queue_item_id": "as_qizheng_000001#review_source_fidelity",
                "target_entity_id": "as_qizheng_000001",
                "kind": "assertion",
                "decision_type": "review_source_fidelity",
            }
        ]
        old_decisions = [
            {
                "target_entity_id": "as_qizheng_000002",
                "entity_kind": "assertion",
                "decision_type": "review_source_fidelity",
                "verdict": "accept",
                "rationale": "通过",
            }
        ]
        with self.assertRaises(ReplayMismatchError) as ctx:
            verify_m6_targets(new_queue_items, old_decisions)
        self.assertIn("目标集合不等", str(ctx.exception))

    def test_m6_pattern_in_queue_without_supplement_stops(self):
        """M6 队列包含 pattern 但旧决定中无对应项时停手。"""
        new_queue_items = [
            {
                "queue_item_id": "as_qizheng_000001#review_source_fidelity",
                "target_entity_id": "as_qizheng_000001",
                "kind": "assertion",
                "decision_type": "review_source_fidelity",
            },
            {
                "queue_item_id": "pat_qizheng_000001#review_source_fidelity",
                "target_entity_id": "pat_qizheng_000001",
                "kind": "pattern",
                "decision_type": "review_source_fidelity",
            },
        ]
        old_decisions = [
            {
                "target_entity_id": "as_qizheng_000001",
                "entity_kind": "assertion",
                "decision_type": "review_source_fidelity",
                "verdict": "accept",
                "rationale": "通过",
            }
        ]
        with self.assertRaises(ReplayMismatchError) as ctx:
            verify_m6_targets(new_queue_items, old_decisions)
        self.assertIn("pat_qizheng_000001", str(ctx.exception))

    def test_load_m6_supplement_decisions(self):
        """测试从 YAML 读取 U07 补充决定并标准化为决定字典。"""
        from pipeline.tools.replay_human_decisions import load_m6_supplement_decisions
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("""
actor_ref: user:wjt
decisions:
  - entity_id: pat_qizheng_000001
    decision_type: review_source_fidelity
    verdict: accept
    rationale: 审定接受
""")
            temp_path = f.name
        try:
            items = load_m6_supplement_decisions(temp_path)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["target_entity_id"], "pat_qizheng_000001")
            self.assertEqual(items[0]["entity_kind"], "pattern")
            self.assertEqual(items[0]["verdict"], "accept")
            self.assertEqual(items[0]["actor_ref"], "user:wjt")
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestReplayHumanDecisionsIntegration(unittest.TestCase):
    """小夹具集成测试：证明对得上就逐字照抄。"""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="test-replay-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.ledger_dir = Path(self._tmp) / "ledger"
        self.adapter = DirectLedgerAdapter(self.ledger_dir)
        self.addCleanup(self.adapter.close)
        self.service = self.adapter.unwrap()

    def test_replay_verbatim_when_matched(self):
        """5. 对得上就逐字照抄：小夹具在真实临时 Ledger 上验证 M4 与 M6 逐字登记。"""
        edition_part_id = ids.new_id("artifact_id")
        prun_id = self.service.create_processing_run(
            "edition_run",
            edition_part_id,
            "qizheng",
        )

        # 1. 模拟 M4 暂停在 awaiting_human
        m4_config_rev = self.service.put_run_artifact(
            prun_id,
            "configuration",
            json.dumps({"stage": "m4"}).encode("utf-8"),
            producer_module="test",
            producer_version="0.1.0",
        )[1]
        m4_srun_id = self.service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "processing_run_id": prun_id,
                "step_run_id": ids.new_id("step_run_id"),
                "input_artifact_ids": [],
                "technique_profile_id": "qizheng",
                "configuration_artifact_id": m4_config_rev,
            }
        )
        # 写 dispute_queue 并封存
        dispute_item = {
            "dispute_id": "m4_d001",
            "category": "assertion",
            "a": [{"proposition": "论断 A"}],
            "b": [{"proposition": "论断 B"}],
            "key": [["s001", 0, 10]],
        }
        dq_rev = self.service.put_artifact(
            m4_srun_id,
            "dispute_queue",
            json.dumps({"disputes": [dispute_item]}, ensure_ascii=False).encode("utf-8"),
            producer_module="test",
            producer_version="0.1.0",
        )[1]
        self.service.seal_revision(dq_rev)
        m4_token = self.service.await_human(m4_srun_id, pending_queue_revision_ids=[dq_rev])

        # 准备 M4 原始裁决数据
        old_disputes = [dict(dispute_item)]
        old_rulings = {
            "m4_d001": {
                "dispute_id": "m4_d001",
                "choice": "both",
                "rationale": "小夹具测试：两路并存",
                "actor_ref": "user:wjt",
            }
        }

        # 执行 M4 回放
        m4_results = replay_m4_rulings(
            self.service,
            m4_srun_id,
            m4_token,
            old_disputes=old_disputes,
            old_rulings=old_rulings,
        )
        self.assertEqual(len(m4_results), 1)
        self.assertEqual(m4_results[0]["dispute_id"], "m4_d001")

        # 检查账本中登记的 human_event 内容逐字一致
        m4_events = self.service.list_human_events(m4_srun_id)
        self.assertEqual(len(m4_events), 1)
        ev_rev = self.service.get_revision(m4_events[0]["event_revision_id"])
        ev_doc = json.loads(self.adapter.read_object(ev_rev["sha256"]).decode("utf-8"))
        self.assertEqual(ev_doc["choice"], "both")
        self.assertEqual(ev_doc["rationale"], "小夹具测试：两路并存")
        self.assertEqual(ev_doc["actor_ref"], "user:wjt")

        # 2. 模拟 M6 暂停在 awaiting_human
        m6_config_rev = self.service.put_run_artifact(
            prun_id,
            "configuration",
            json.dumps({"stage": "m6"}).encode("utf-8"),
            producer_module="test",
            producer_version="0.1.0",
        )[1]
        m6_srun_id = self.service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "processing_run_id": prun_id,
                "step_run_id": ids.new_id("step_run_id"),
                "input_artifact_ids": [],
                "technique_profile_id": "qizheng",
                "configuration_artifact_id": m6_config_rev,
            }
        )
        # 写 candidate_set 并封存
        cand_set_doc = {
            "assertions": [
                {
                    "assertion_id": "as_qizheng_000001",
                    "proposition": "原论断一",
                },
                {
                    "assertion_id": "as_qizheng_000002",
                    "proposition": "原论断二",
                },
            ]
        }
        cand_set_rev = self.service.put_artifact(
            m6_srun_id,
            "candidate_set",
            json.dumps(cand_set_doc, ensure_ascii=False).encode("utf-8"),
            producer_module="test",
            producer_version="0.1.0",
        )[1]
        self.service.seal_revision(cand_set_rev)

        # 写 review_queue 并封存
        queue_items = [
            {
                "queue_item_id": "as_qizheng_000001#review_source_fidelity",
                "target_entity_id": "as_qizheng_000001",
                "kind": "assertion",
                "decision_type": "review_source_fidelity",
                "seen_artifact_revision_id": cand_set_rev,
            },
            {
                "queue_item_id": "as_qizheng_000002#review_source_fidelity",
                "target_entity_id": "as_qizheng_000002",
                "kind": "assertion",
                "decision_type": "review_source_fidelity",
                "seen_artifact_revision_id": cand_set_rev,
            },
        ]
        rq_rev = self.service.put_artifact(
            m6_srun_id,
            "review_queue",
            json.dumps(queue_items, ensure_ascii=False).encode("utf-8"),
            producer_module="test",
            producer_version="0.1.0",
        )[1]
        self.service.seal_revision(rq_rev)
        self.service.write_checkpoint(
            m6_srun_id,
            edition_part_id=edition_part_id,
            stage="m6",
            completed_tasks=[],
            human_decisions=[],
            pending_queue=[rq_rev],
            next_pointer=None,
        )
        m6_token = self.service.await_human(m6_srun_id, pending_queue_revision_ids=[rq_rev])

        # 准备 M6 原始决定数据（1条 accept，1条 modify）
        old_decisions = [
            {
                "target_entity_id": "as_qizheng_000001",
                "entity_kind": "assertion",
                "decision_type": "review_source_fidelity",
                "verdict": "accept",
                "rationale": "第一条忠实原文",
                "evidence_refs": [],
                "actor_ref": "local_owner",
            },
            {
                "target_entity_id": "as_qizheng_000002",
                "entity_kind": "assertion",
                "decision_type": "review_source_fidelity",
                "verdict": "modify",
                "rationale": "第二条修改论断文字",
                "modified_content": {"proposition": "修改后的论断二"},
                "evidence_refs": [],
                "actor_ref": "local_owner",
            },
        ]

        # 执行 M6 回放
        m6_results = replay_m6_decisions(
            self.service,
            m6_srun_id,
            m6_token,
            old_decisions=old_decisions,
        )
        self.assertEqual(len(m6_results), 2)

        # 验证账本中登记的 M6 human_event 逐字一致
        m6_events = self.service.list_human_events(m6_srun_id)
        self.assertEqual(len(m6_events), 2)

        ev1_rev = self.service.get_revision(m6_events[0]["event_revision_id"])
        ev1_doc = json.loads(self.adapter.read_object(ev1_rev["sha256"]).decode("utf-8"))
        self.assertEqual(ev1_doc["verdict"], "accept")
        self.assertEqual(ev1_doc["rationale"], "第一条忠实原文")
        self.assertEqual(ev1_doc["target"]["entity_id"], "as_qizheng_000001")

        ev2_rev = self.service.get_revision(m6_events[1]["event_revision_id"])
        ev2_doc = json.loads(self.adapter.read_object(ev2_rev["sha256"]).decode("utf-8"))
        self.assertEqual(ev2_doc["verdict"], "modify")
        self.assertEqual(ev2_doc["rationale"], "第二条修改论断文字")
        self.assertEqual(ev2_doc["target"]["entity_id"], "as_qizheng_000002")

        # 验证 modify 产生对应的 reviewed_candidate
        rev_cands = self.service.list_step_run_revisions(m6_srun_id, artifact_type="reviewed_candidate")
        self.assertEqual(len(rev_cands), 1)
        rc_doc = json.loads(self.adapter.read_object(self.service.get_revision(rev_cands[0]["artifact_revision_id"])["sha256"]).decode("utf-8"))
        self.assertEqual(rc_doc["assertion_id"], "as_qizheng_000002")
        self.assertEqual(rc_doc["proposition"], "修改后的论断二")

    def test_m6_replay_with_pattern_and_supplement_integration(self):
        """集成测试：M6 队列含 pattern 时，不加 supplement 停手抛出异常，加 supplement 成功回放。"""
        edition_part_id = ids.new_id("artifact_id")
        prun_id = self.service.create_processing_run(
            "edition_run",
            edition_part_id,
            "qizheng",
        )
        m6_config_rev = self.service.put_run_artifact(
            prun_id,
            "configuration",
            json.dumps({"stage": "m6"}).encode("utf-8"),
            producer_module="test",
            producer_version="0.1.0",
        )[1]
        m6_srun_id = self.service.begin_step_run(
            {
                "schema_version": "1.0.0",
                "processing_run_id": prun_id,
                "step_run_id": ids.new_id("step_run_id"),
                "input_artifact_ids": [],
                "technique_profile_id": "qizheng",
                "configuration_artifact_id": m6_config_rev,
            }
        )
        cand_set_doc = {
            "assertions": [{"assertion_id": "as_qizheng_000001", "proposition": "论断一"}],
            "patterns": [{"pattern_id": "pat_qizheng_000001", "pattern_name": "格局一"}],
        }
        cand_set_rev = self.service.put_artifact(
            m6_srun_id,
            "candidate_set",
            json.dumps(cand_set_doc, ensure_ascii=False).encode("utf-8"),
            producer_module="test",
            producer_version="0.1.0",
        )[1]
        self.service.seal_revision(cand_set_rev)

        queue_items = [
            {
                "queue_item_id": "as_qizheng_000001#review_source_fidelity",
                "target_entity_id": "as_qizheng_000001",
                "kind": "assertion",
                "decision_type": "review_source_fidelity",
                "seen_artifact_revision_id": cand_set_rev,
            },
            {
                "queue_item_id": "pat_qizheng_000001#review_source_fidelity",
                "target_entity_id": "pat_qizheng_000001",
                "kind": "pattern",
                "decision_type": "review_source_fidelity",
                "seen_artifact_revision_id": cand_set_rev,
            },
        ]
        rq_rev = self.service.put_artifact(
            m6_srun_id,
            "review_queue",
            json.dumps(queue_items, ensure_ascii=False).encode("utf-8"),
            producer_module="test",
            producer_version="0.1.0",
        )[1]
        self.service.seal_revision(rq_rev)
        self.service.write_checkpoint(
            m6_srun_id,
            edition_part_id=edition_part_id,
            stage="m6",
            completed_tasks=[],
            human_decisions=[],
            pending_queue=[rq_rev],
            next_pointer=None,
        )
        m6_token = self.service.await_human(m6_srun_id, pending_queue_revision_ids=[rq_rev])

        old_decisions = [
            {
                "target_entity_id": "as_qizheng_000001",
                "entity_kind": "assertion",
                "decision_type": "review_source_fidelity",
                "verdict": "accept",
                "rationale": "通过",
                "evidence_refs": [],
                "actor_ref": "local_owner",
            }
        ]
        # 探针 1：不给 supplement，必须停手抛错，指明缺失 pat_qizheng_000001
        with self.assertRaises(ReplayMismatchError) as ctx:
            replay_m6_decisions(
                self.service,
                m6_srun_id,
                m6_token,
                old_decisions=old_decisions,
            )
        self.assertIn("pat_qizheng_000001", str(ctx.exception))

        # 探针 2：给 supplement 后，成功回放
        supplement = [
            {
                "target_entity_id": "pat_qizheng_000001",
                "entity_kind": "pattern",
                "decision_type": "review_source_fidelity",
                "verdict": "accept",
                "rationale": "格局接受",
                "evidence_refs": [],
                "actor_ref": "user:wjt",
            }
        ]
        results = replay_m6_decisions(
            self.service,
            m6_srun_id,
            m6_token,
            old_decisions=old_decisions,
            supplement_decisions=supplement,
        )
        self.assertEqual(len(results), 2)
        events = self.service.list_human_events(m6_srun_id)
        self.assertEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()

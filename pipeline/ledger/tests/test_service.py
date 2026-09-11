"""ACT impl-01/03：LedgerService / LedgerReader（规格 §7.1、§17）的单元测试。

先写本文件，运行 `.venv/bin/python -m unittest discover -s pipeline/ledger/tests -t .`
因 `pipeline.ledger.service` 尚不存在而全红。所有用例只使用 ``tempfile`` 目录，
绝不写 ``var/`` 或 fixture。

实现约定（ACT 03 未逐字规定、由实现选定并在交付报告中登记）：

- ``step_runs.stage`` 由 ``begin_step_run`` 从配置修订（``configuration_artifact_id``）
  的已封存内容 JSON 的 ``stage`` 键推导；StepRequest Schema 没有 stage 字段，配置修订
  是该 stage 的唯一载体（见 act/05.yaml step 2）。
- ``resume_token`` 只存哈希，并把哈希与该次 ``awaiting_human`` 的 ``status_version``
  绑定（存为 ``v<版本>:<sha256>``）；``recover`` 回到 ``awaiting_human`` 时按新版本重新
  锚定前缀，使 token 在 suspended/recovery 往返后仍有效（§7.1 + BDD 3.3）。
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.ledger import ids
from pipeline.ledger.actor import LocalActorProvider
from pipeline.ledger.errors import (
    DuplicateIdentifier,
    HashMismatch,
    IllegalTransition,
    InvalidIdentifier,
    InvalidResumeToken,
    LedgerError,
    NotConsumable,
    SchemaViolation,
    WriterLocked,
)
from pipeline.ledger.lock import WriterLock
from pipeline.ledger.service import LedgerReader, LedgerService
from pipeline.ledger.store import utcnow

# 登记用固定 stage（fixture 与单测都用 m1–m3）


class ServiceTestBase(unittest.TestCase):
    """公共脚手架：临时 Ledger 根、直连 LedgerService、配置修订播种。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.service = LedgerService(self.root)
        self.addCleanup(self.service.close)

    # ------------------------------------------------------------ 脚手架
    def actor(self):
        return LocalActorProvider().current_actor()

    def seed_configuration(self, processing_run_id, stage, payload=None):
        """低层播种一个已 sealed 的配置修订（ACT 03 阶段尚无 put_run_artifact）。

        内容 JSON 含 ``stage`` 键；``begin_step_run`` 由它推导 ``step_runs.stage``。
        """
        artifact_id = ids.new_id("artifact_id")
        revision_id = ids.new_id("artifact_revision_id")
        data = payload if payload is not None else json.dumps(
            {"stage": stage, "tool": "tests", "tool_version": "1.0"}
        ).encode("utf-8")
        sha256, size = self.service.objects.put(data)
        now = utcnow()
        with self.service.store.transaction():
            self.service.store.insert_artifact(
                artifact_id, "configuration", now, self.actor()
            )
            self.service.store.insert_revision(
                revision_id,
                artifact_id,
                "sealed",
                1,
                sha256,
                size,
                "objects/%s/%s" % (sha256[:2], sha256),
                "tests",
                "1.0",
                "internal",
                now,
                self.actor(),
                processing_run_id=processing_run_id,
                sealed_at=now,
            )
        return revision_id

    def new_processing_run(self, technique_id="qizheng"):
        return self.service.create_processing_run(
            "edition_run", ids.new_id("artifact_id"), technique_id
        )

    def request(self, processing_run_id, step_run_id, configuration_revision_id,
                inputs=(), technique_profile_id="qizheng"):
        return {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "input_artifact_ids": list(inputs),
            "technique_profile_id": technique_profile_id,
            "configuration_artifact_id": configuration_revision_id,
        }

    def begin(self, processing_run_id, stage="m1", inputs=(), step_run_id=None,
              configuration_revision_id=None):
        """建配置修订并 begin_step_run，返回 (step_run_id, 配置修订号)。"""
        config = configuration_revision_id or self.seed_configuration(
            processing_run_id, stage
        )
        step_run_id = step_run_id or ids.new_id("step_run_id")
        returned = self.service.begin_step_run(
            self.request(processing_run_id, step_run_id, config, inputs)
        )
        self.assertEqual(returned, step_run_id)
        return step_run_id, config

    def put_sealed(self, step_run_id, artifact_type="source_manifest", data=b"payload"):
        artifact_id, revision_id = self.service.put_artifact(
            step_run_id,
            artifact_type,
            data,
            producer_module="tests",
            producer_version="1.0",
        )
        self.service.seal_revision(revision_id)
        return artifact_id, revision_id

    def result(self, processing_run_id, step_run_id, outputs=(), validation=(),
               logs=(), failures=(), status="succeeded"):
        # StepResult.status_version 取「完成该次迁移后的版本」（step_result Schema 要求 >= 1）
        current = self.service.store.get_step_run(step_run_id)["status_version"] + 1
        return {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": step_run_id,
            "status_version": current,
            "status": status,
            "output_artifact_ids": list(outputs),
            "validation_report_ids": list(validation),
            "log_artifact_ids": list(logs),
            "failure_artifact_ids": list(failures),
        }

    def artifact_type_of(self, revision_id):
        row = self.service.store.conn.execute(
            "SELECT a.artifact_type FROM artifacts a JOIN artifact_revisions r "
            "ON r.artifact_id = a.artifact_id WHERE r.artifact_revision_id=?",
            (revision_id,),
        ).fetchone()
        return None if row is None else row[0]

    def assert_audit(self, action, target):
        rows = self.service.store.conn.execute(
            "SELECT action, target FROM audit_log WHERE action=? ORDER BY id DESC",
            (action,),
        ).fetchall()
        self.assertTrue(rows, "缺少审计记录: %s" % action)
        self.assertEqual(rows[0]["target"], str(target))

    def events(self, step_run_id, event_type=None):
        rows = self.service.store.list_step_run_events(step_run_id)
        if event_type is not None:
            rows = [row for row in rows if row["event_type"] == event_type]
        return rows


class TestLedgerService(ServiceTestBase):
    """覆盖 §7.1 与 §17：StepRun 事务序列、人工恢复、suspended 对账与只读 API。"""

    # -------------------------------------------------------------- begin
    def test_begin_step_run_validates_request_schema(self):
        processing_run_id = ids.new_id("processing_run_id")
        request = {
            "schema_version": "1.0.0",
            "processing_run_id": processing_run_id,
            "step_run_id": ids.new_id("step_run_id"),
            "input_artifact_ids": [],
            # 故意缺 technique_profile_id
            "configuration_artifact_id": ids.new_id("artifact_revision_id"),
        }
        with self.assertRaises(SchemaViolation) as ctx:
            self.service.begin_step_run(request)
        self.assertEqual(ctx.exception.code, "SCH_001")

    def test_begin_step_run_rejects_unsealed_input(self):
        processing_run_id = self.new_processing_run()
        first, _ = self.begin(processing_run_id, "m1")
        _, draft_revision = self.service.put_artifact(
            first,
            "source_manifest",
            b"still draft",
            producer_module="tests",
            producer_version="1.0",
        )
        self.assertEqual(
            self.service.store.get_revision(draft_revision)["status"], "draft"
        )
        config = self.seed_configuration(processing_run_id, "m2")
        with self.assertRaises(NotConsumable):
            self.service.begin_step_run(
                self.request(
                    processing_run_id,
                    ids.new_id("step_run_id"),
                    config,
                    [draft_revision],
                )
            )

    # ------------------------------------------------------ put / seal
    def test_put_then_seal_records_hash_size_and_events(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        data = b"hello ledger service"
        artifact_id, revision_id = self.service.put_artifact(
            step_run_id,
            "source_manifest",
            data,
            producer_module="tests",
            producer_version="1.0",
        )
        row = self.service.store.get_revision(revision_id)
        self.assertEqual(row["status"], "draft")
        self.assertEqual(row["status_version"], 0)
        self.assertEqual(row["artifact_id"], artifact_id)
        self.assertEqual(row["step_run_id"], step_run_id)
        self.assertEqual(row["processing_run_id"], processing_run_id)
        self.assertEqual(row["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(row["size_bytes"], len(data))
        self.assertIsNone(row["sealed_at"])
        self.assertTrue(self.service.objects.exists(row["sha256"]))

        self.service.seal_revision(revision_id)
        row = self.service.store.get_revision(revision_id)
        self.assertEqual(row["status"], "sealed")
        self.assertEqual(row["status_version"], 1)
        self.assertIsNotNone(row["sealed_at"])
        history = self.service.store.conn.execute(
            "SELECT from_status, to_status FROM revision_status_events "
            "WHERE artifact_revision_id=? ORDER BY id",
            (revision_id,),
        ).fetchall()
        self.assertEqual(
            [(item[0], item[1]) for item in history], [("draft", "sealed")]
        )

    def test_seal_detects_object_tamper(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        _, revision_id = self.service.put_artifact(
            step_run_id,
            "source_manifest",
            b"tamper me",
            producer_module="tests",
            producer_version="1.0",
        )
        row = self.service.store.get_revision(revision_id)
        path = self.service.objects.path_for(row["sha256"])
        raw = bytearray(path.read_bytes())
        raw[0] ^= 0x01
        path.write_bytes(bytes(raw))

        with self.assertRaises(HashMismatch) as ctx:
            self.service.seal_revision(revision_id)
        self.assertEqual(ctx.exception.code, "SRC_003")
        self.assertEqual(
            self.service.store.get_revision(revision_id)["status"], "quarantined"
        )

    def test_illegal_artifact_transition(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        _, revision_id = self.service.put_artifact(
            step_run_id,
            "source_manifest",
            b"draft only",
            producer_module="tests",
            producer_version="1.0",
        )
        # draft → invalidated 不在 §8.2 第 4 表内
        with self.assertRaises(IllegalTransition):
            self.service.invalidate_revision(revision_id, "未封存不可失效")
        # sealed → quarantined 不在表内（quarantine 只允许 draft → quarantined）
        self.service.seal_revision(revision_id)
        with self.assertRaises(IllegalTransition):
            self.service.quarantine_revision(revision_id, "误判")
        # invalidated → sealed 不在表内（不得把旧修订改回 sealed）
        self.service.invalidate_revision(revision_id, "上游变化")
        with self.assertRaises(IllegalTransition):
            self.service.seal_revision(revision_id)
        # invalidated → superseded 合法（新修订必须同 Artifact 且 prev 指向旧修订）
        _, next_revision = self.service.put_artifact(
            step_run_id,
            "source_manifest",
            b"v2",
            prev_revision_id=revision_id,
            producer_module="tests",
            producer_version="1.0",
        )
        self.service.seal_revision(next_revision)
        self.service.supersede_revision(revision_id, next_revision)
        self.assertEqual(
            self.service.store.get_revision(revision_id)["status"], "superseded"
        )

    def test_supersede_revision_requires_same_artifact_and_prev_pointer(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        artifact_x, x1 = self.put_sealed(step_run_id, "source_manifest", b"x1")
        _, y1 = self.put_sealed(step_run_id, "ocr_page", b"y1")
        _, y2 = self.service.put_artifact(
            step_run_id,
            "ocr_page",
            b"y2",
            prev_revision_id=y1,
            producer_module="tests",
            producer_version="1.0",
        )
        self.service.seal_revision(y2)
        self.assertEqual(self.service.store.get_revision(y2)["artifact_id"],
                         self.service.store.get_revision(y1)["artifact_id"])

        # 不同 artifact 之间不得 supersede
        with self.assertRaises(IllegalTransition):
            self.service.supersede_revision(x1, y1)
        # 同一 artifact 且 prev 指针正确 → 合法
        self.service.supersede_revision(y1, y2)
        self.assertEqual(self.service.store.get_revision(y1)["status"], "superseded")

        # prev 指针不指向旧修订 → 非法
        _, y3 = self.service.put_artifact(
            step_run_id,
            "ocr_page",
            b"y3",
            prev_revision_id=y1,
            producer_module="tests",
            producer_version="1.0",
        )
        self.service.seal_revision(y3)
        with self.assertRaises(IllegalTransition):
            self.service.supersede_revision(y2, y3)
        self.assertEqual(
            self.service.store.get_revision(x1)["artifact_id"], artifact_x
        )

    # --------------------------------------------------- transformation
    def test_record_transformation_outputs_must_belong_to_step_run(self):
        processing_run_id = self.new_processing_run()
        first, config_first = self.begin(processing_run_id, "m1")
        _, out_first = self.put_sealed(first, "source_manifest", b"out1")
        second, config_second = self.begin(processing_run_id, "m2", inputs=[out_first])
        _, out_second = self.put_sealed(second, "ocr_page_set", b"out2")

        # 输出不属于本 StepRun → 拒绝
        with self.assertRaises(IllegalTransition):
            self.service.record_transformation(
                second,
                operation="digitize_pages",
                tool="tests",
                tool_version="1.0",
                configuration_revision_id=config_second,
                input_revision_ids=[out_first],
                output_revision_ids=[out_first],
            )
        # 输入不在冻结输入集内 → 拒绝
        _, stray = self.put_sealed(first, "step_log", b"stray")
        with self.assertRaises(IllegalTransition):
            self.service.record_transformation(
                second,
                operation="digitize_pages",
                tool="tests",
                tool_version="1.0",
                configuration_revision_id=config_second,
                input_revision_ids=[out_first, stray],
                output_revision_ids=[out_second],
            )
        # 合法：输入 == 冻结输入，输出为本次产出
        transformation_id = self.service.record_transformation(
            second,
            operation="digitize_pages",
            tool="tests",
            tool_version="1.0",
            configuration_revision_id=config_second,
            input_revision_ids=[out_first],
            output_revision_ids=[out_second],
        )
        self.assertEqual(
            self.service.store.list_transformation_inputs(transformation_id),
            [out_first],
        )
        self.assertEqual(
            self.service.store.list_transformation_outputs(transformation_id),
            [out_second],
        )
        self.assertNotEqual(config_first, config_second)

    # ---------------------------------------------------- human resume
    def test_await_human_resume_token_single_use(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        _, queued = self.put_sealed(step_run_id, "ocr_page", b"pending")
        token = self.service.await_human(step_run_id, [queued])
        self.assertIsInstance(token, str)
        row = self.service.store.get_step_run(step_run_id)
        self.assertEqual(row["status"], "awaiting_human")
        self.assertIsNotNone(row["resume_token_hash"])
        self.assertNotEqual(row["resume_token_hash"], token)
        self.assertNotIn(token, row["resume_token_hash"])
        self.assertIn(hashlib.sha256(token.encode("utf-8")).hexdigest(),
                      row["resume_token_hash"])
        self.assertEqual(
            [event["event_type"] for event in self.events(step_run_id)],
            ["created", "await_human"],
        )

        self.service.resume(step_run_id, token)
        row = self.service.store.get_step_run(step_run_id)
        self.assertEqual(row["status"], "running")
        self.assertIsNone(row["resume_token_hash"])
        with self.assertRaises(InvalidResumeToken):
            self.service.resume(step_run_id, token)

    def test_record_human_event_does_not_consume_token(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        _, queued = self.put_sealed(step_run_id, "ocr_page", b"pending")
        token = self.service.await_human(step_run_id, [queued])
        _, decision = self.put_sealed(
            step_run_id, "human_event", b'{"decision":"ok"}'
        )
        self.service.record_human_event(
            step_run_id, token, decision, decision_type="review_source_fidelity"
        )
        # 事件登记本身不消费 token
        self.assertIsNotNone(
            self.service.store.get_step_run(step_run_id)["resume_token_hash"]
        )
        self.assertEqual(
            self.service.store.conn.execute(
                "SELECT decision_type FROM human_events WHERE event_revision_id=?",
                (decision,),
            ).fetchone()[0],
            "review_source_fidelity",
        )
        # token 仍可用
        self.service.resume(step_run_id, token)
        self.assertEqual(
            self.service.store.get_step_run(step_run_id)["status"], "running"
        )

    def test_record_human_event_rejects_wrong_token(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        _, queued = self.put_sealed(step_run_id, "ocr_page", b"pending")
        token = self.service.await_human(step_run_id, [queued])
        _, decision = self.put_sealed(step_run_id, "human_event", b"{}")

        with self.assertRaises(InvalidResumeToken):
            self.service.record_human_event(step_run_id, token + "x", decision)
        # decision_type 必须属 §8.2 第 2 表
        with self.assertRaises(SchemaViolation) as ctx:
            self.service.record_human_event(
                step_run_id, token, decision, decision_type="review_nope"
            )
        self.assertEqual(ctx.exception.code, "SCH_002")
        # 事件修订必须是 artifact_type=human_event 的 sealed 修订
        _, not_event = self.put_sealed(step_run_id, "ocr_page", b"not an event")
        with self.assertRaises(LedgerError):
            self.service.record_human_event(step_run_id, token, not_event)

    def test_suspend_from_awaiting_human_and_recover_returns_to_awaiting_human(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        _, queued = self.put_sealed(step_run_id, "ocr_page", b"pending")
        token = self.service.await_human(step_run_id, [queued])

        self.service.suspend(step_run_id, "操作者暂停", "operator")
        self.assertEqual(
            self.service.store.get_step_run(step_run_id)["status"], "suspended"
        )
        self.service.recover(step_run_id, "基础设施恢复")
        self.assertEqual(
            self.service.store.get_step_run(step_run_id)["status"], "awaiting_human"
        )
        # token 在 suspended/recovery 往返后仍有效
        _, decision = self.put_sealed(step_run_id, "human_event", b"{}")
        self.service.record_human_event(step_run_id, token, decision)
        self.service.resume(step_run_id, token)
        self.assertEqual(
            self.service.store.get_step_run(step_run_id)["status"], "running"
        )

    def test_recover_on_terminal_step_run_is_illegal(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        _, out = self.put_sealed(step_run_id, "source_manifest", b"out")
        self.service.finish_step_run(
            step_run_id, self.result(processing_run_id, step_run_id, outputs=[out])
        )
        before = dict(self.service.store.get_step_run(step_run_id))
        with self.assertRaises(IllegalTransition):
            self.service.recover(step_run_id, "不得改写终态")
        self.assertEqual(dict(self.service.store.get_step_run(step_run_id)), before)

    def test_suspended_event_persists_reason_source_inputs_queue(self):
        upstream_run = self.new_processing_run()
        upstream_step, _ = self.begin(upstream_run, "m1")
        _, upstream = self.put_sealed(upstream_step, "source_manifest", b"up")

        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m2", inputs=[upstream])
        _, queued = self.put_sealed(step_run_id, "ocr_page", b"pending")
        self.service.await_human(step_run_id, [queued])
        self.service.suspend(step_run_id, "基础设施不可用", "infrastructure")

        suspended = self.events(step_run_id, "suspended")
        self.assertEqual(len(suspended), 1)
        payload = json.loads(suspended[0]["payload_json"])
        self.assertEqual(payload["reason"], "基础设施不可用")
        self.assertEqual(payload["source"], "infrastructure")
        self.assertEqual(payload["frozen_inputs"], [upstream])
        self.assertEqual(payload["pending_queue"], [queued])
        self.assertEqual(suspended[0]["from_status"], "awaiting_human")
        self.assertEqual(suspended[0]["to_status"], "suspended")
        self.assertIsNone(self.service.store.get_step_run(step_run_id)["result_json"])

    # -------------------------------------------- finish / fail / rerun
    def test_finish_step_run_seals_step_manifest_and_validates_result_schema(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m1")
        _, out = self.put_sealed(step_run_id, "source_manifest", b"out")
        _, log = self.put_sealed(step_run_id, "step_log", b"log")
        _, report = self.put_sealed(step_run_id, "validation_report", b"{}")

        missing = self.result(processing_run_id, step_run_id, outputs=[out])
        missing.pop("status")
        with self.assertRaises(SchemaViolation) as ctx:
            self.service.finish_step_run(step_run_id, missing)
        self.assertEqual(ctx.exception.code, "SCH_001")

        invalid_enum = self.result(
            processing_run_id, step_run_id, outputs=[out], status="bogus"
        )
        with self.assertRaises(SchemaViolation) as ctx:
            self.service.finish_step_run(step_run_id, invalid_enum)
        self.assertEqual(ctx.exception.code, "SCH_002")

        not_succeeded = self.result(
            processing_run_id, step_run_id, outputs=[out], status="running"
        )
        with self.assertRaises(LedgerError):
            self.service.finish_step_run(step_run_id, not_succeeded)

        manifest_revision = self.service.finish_step_run(
            step_run_id,
            self.result(
                processing_run_id,
                step_run_id,
                outputs=[out],
                validation=[report],
                logs=[log],
            ),
        )
        self.assertEqual(
            self.service.store.get_step_run(step_run_id)["status"], "succeeded"
        )
        row = self.service.store.get_revision(manifest_revision)
        self.assertEqual(row["status"], "sealed")
        self.assertEqual(self.artifact_type_of(manifest_revision), "step_manifest")
        content = json.loads(self.service.objects.get(row["sha256"]).decode("utf-8"))
        for key in (
            "step_run_id",
            "request",
            "result",
            "frozen_inputs",
            "transformation_ids",
            "last_checkpoint_revision_id",
            "sealed_at",
        ):
            self.assertIn(key, content)
        self.assertEqual(content["step_run_id"], step_run_id)

    def test_fail_step_run_keeps_failure_artifact_sealed(self):
        processing_run_id = self.new_processing_run()
        step_run_id, _ = self.begin(processing_run_id, "m3")
        _, failure = self.put_sealed(step_run_id, "failure_report", b"boom")
        self.service.fail_step_run(step_run_id, [failure], "任务失败")

        self.assertEqual(
            self.service.store.get_step_run(step_run_id)["status"], "failed"
        )
        self.assertEqual(
            self.service.store.get_revision(failure)["status"], "sealed"
        )
        self.assertEqual(
            [event["event_type"] for event in self.events(step_run_id)],
            ["created", "failure"],
        )

    def test_supersede_step_run_keeps_old_terminal_state_and_links(self):
        processing_run_id = self.new_processing_run()
        running_step, _ = self.begin(processing_run_id, "m1")
        config = self.seed_configuration(processing_run_id, "m1")
        new_step_run_id = ids.new_id("step_run_id")
        returned = self.service.supersede_step_run(
            running_step,
            self.request(processing_run_id, new_step_run_id, config),
        )
        self.assertEqual(returned, new_step_run_id)
        self.assertEqual(
            self.service.store.get_step_run(new_step_run_id)["supersedes_step_run_id"],
            running_step,
        )
        self.assertEqual(
            self.service.store.get_step_run(running_step)["status"], "superseded"
        )

        finished_step, _ = self.begin(processing_run_id, "m2")
        _, out = self.put_sealed(finished_step, "ocr_page_set", b"out")
        self.service.finish_step_run(
            finished_step,
            self.result(processing_run_id, finished_step, outputs=[out]),
        )
        config2 = self.seed_configuration(processing_run_id, "m2")
        rerun_id = ids.new_id("step_run_id")
        self.service.supersede_step_run(
            finished_step, self.request(processing_run_id, rerun_id, config2)
        )
        # 旧运行已是终态 → 原终态不变，仅由新运行表达重跑关系
        self.assertEqual(
            self.service.store.get_step_run(finished_step)["status"], "succeeded"
        )
        self.assertEqual(
            self.service.store.get_step_run(rerun_id)["supersedes_step_run_id"],
            finished_step,
        )

    # ------------------------------------------------------------ 导入路径
    def test_explicit_ids_import_path(self):
        processing_run_id = ids.new_id("processing_run_id")
        adopted = self.service.create_processing_run(
            "edition_run",
            ids.new_id("artifact_id"),
            "qizheng",
            processing_run_id=processing_run_id,
        )
        self.assertEqual(adopted, processing_run_id)

        with self.assertRaises(DuplicateIdentifier) as ctx:
            self.service.create_processing_run(
                "edition_run",
                ids.new_id("artifact_id"),
                "qizheng",
                processing_run_id=processing_run_id,
            )
        self.assertEqual(ctx.exception.code, "ID_002")

        with self.assertRaises(InvalidIdentifier) as ctx:
            self.service.create_processing_run(
                "edition_run",
                ids.new_id("artifact_id"),
                "qizheng",
                processing_run_id="pr_" + "a" * 32,
            )
        self.assertEqual(ctx.exception.code, "ID_001")

        config = self.seed_configuration(processing_run_id, "m1")
        step_run_id = ids.new_id("step_run_id")
        self.service.begin_step_run(
            self.request(processing_run_id, step_run_id, config)
        )
        artifact_id = ids.new_id("artifact_id")
        revision_id = ids.new_id("artifact_revision_id")
        got_artifact, got_revision = self.service.put_artifact(
            step_run_id,
            "source_manifest",
            b"imported",
            artifact_id=artifact_id,
            artifact_revision_id=revision_id,
            producer_module="tests",
            producer_version="1.0",
        )
        self.assertEqual((got_artifact, got_revision), (artifact_id, revision_id))
        with self.assertRaises(DuplicateIdentifier) as ctx:
            self.service.put_artifact(
                step_run_id,
                "source_manifest",
                b"again",
                artifact_revision_id=revision_id,
                producer_module="tests",
                producer_version="1.0",
            )
        self.assertEqual(ctx.exception.code, "ID_002")

    # ------------------------------------------------------------- 审计
    def test_every_write_appends_audit_log(self):
        processing_run_id = self.new_processing_run()
        self.assert_audit("create_processing_run", processing_run_id)

        step_run_id, config = self.begin(processing_run_id, "m1")
        self.assert_audit("begin_step_run", step_run_id)

        artifact_id, out = self.service.put_artifact(
            step_run_id,
            "source_manifest",
            b"out",
            producer_module="tests",
            producer_version="1.0",
        )
        self.assert_audit("put_artifact", artifact_id)
        self.service.seal_revision(out)
        self.assert_audit("seal_revision", out)

        transformation_id = self.service.record_transformation(
            step_run_id,
            operation="ingest_source",
            tool="tests",
            tool_version="1.0",
            configuration_revision_id=config,
            input_revision_ids=[],
            output_revision_ids=[out],
        )
        self.assert_audit("record_transformation", transformation_id)

        token = self.service.await_human(step_run_id, [out])
        self.assert_audit("await_human", step_run_id)
        _, decision = self.put_sealed(step_run_id, "human_event", b"{}")
        self.service.record_human_event(step_run_id, token, decision)
        self.assert_audit("record_human_event", step_run_id)
        self.service.resume(step_run_id, token)
        self.assert_audit("resume", step_run_id)

        self.service.suspend(step_run_id, "暂停", "operator")
        self.assert_audit("suspend", step_run_id)
        self.service.recover(step_run_id, "恢复")
        self.assert_audit("recover", step_run_id)

        manifest = self.service.finish_step_run(
            step_run_id, self.result(processing_run_id, step_run_id, outputs=[out])
        )
        self.assert_audit("finish_step_run", step_run_id)
        self.assertTrue(manifest)

    # -------------------------------------------------------------- 只读
    def test_reader_can_read_while_service_holds_lock(self):
        processing_run_id = self.new_processing_run()
        step_run_id, config = self.begin(processing_run_id, "m1")
        artifact_id, revision_id = self.put_sealed(
            step_run_id, "source_manifest", b"payload"
        )
        transformation_id = self.service.record_transformation(
            step_run_id,
            operation="ingest_source",
            tool="tests",
            tool_version="1.0",
            configuration_revision_id=config,
            input_revision_ids=[],
            output_revision_ids=[revision_id],
        )

        reader = LedgerReader(self.root)
        self.addCleanup(reader.close)
        self.assertEqual(reader.get_revision(revision_id)["status"], "sealed")
        self.assertEqual(reader.get_step_run(step_run_id)["status"], "running")
        self.assertEqual(
            [row["id"] for row in reader.list_transformations(step_run_id)],
            [transformation_id],
        )
        self.assertTrue(reader.list_step_run_events(step_run_id))
        row = self.service.store.get_revision(revision_id)
        self.assertEqual(reader.read_object(row["sha256"]), b"payload")
        self.assertIsNone(reader.latest_checkpoint(artifact_id, "m1"))
        self.assertEqual(reader.list_checkpoints(artifact_id, "m1"), [])
        # 写锁仍被 service 持有
        with self.assertRaises(WriterLocked):
            WriterLock(self.root).acquire()

    def test_run_status_and_stage_progress_shapes(self):
        processing_run_id = self.new_processing_run()
        first, _ = self.begin(processing_run_id, "m1")
        _, out_first = self.put_sealed(first, "source_manifest", b"m1-out")
        self.service.finish_step_run(
            first, self.result(processing_run_id, first, outputs=[out_first])
        )
        second, _ = self.begin(processing_run_id, "m2", inputs=[out_first])

        status = self.service.run_status(processing_run_id)
        self.assertEqual(
            set(status.keys()),
            {
                "processing_run_id",
                "status",
                "started_at",
                "finished_at",
                "step_runs",
            },
        )
        self.assertEqual(status["processing_run_id"], processing_run_id)
        self.assertEqual(status["status"], "running")
        self.assertEqual(len(status["step_runs"]), 2)
        self.assertIsNone(status["finished_at"])

        progress = self.service.stage_progress(processing_run_id)
        self.assertEqual(set(progress.keys()), {"m1", "m2"})
        self.assertEqual(
            set(progress["m1"].keys()),
            {
                "step_runs",
                "succeeded",
                "failed",
                "running",
                "awaiting_human",
                "suspended",
                "superseded",
                "last_checkpoint_revision_id",
            },
        )
        self.assertEqual(progress["m1"]["step_runs"], 1)
        self.assertEqual(progress["m1"]["succeeded"], 1)
        self.assertEqual(progress["m2"]["running"], 1)
        self.assertIsNone(progress["m1"]["last_checkpoint_revision_id"])
        self.assertEqual(progress["m2"]["step_runs"], 1)
        self.assertTrue(second)


if __name__ == "__main__":
    unittest.main()

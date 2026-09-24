"""本地 Ledger 客户端（规格 §17）：经 Unix domain socket 调用，语义与直连一致。

协议（act/04.yaml ``contract.protocol``）：

- 每请求一行 JSON ``{"op": "<方法名>", "args": {...}}``，每响应一行 JSON；
- ``bytes`` 参数用 ``"<name>_b64"``（base64）传递，``bytes`` 结果用 ``"data_b64"``；
- 响应 ``{"ok": true, "result": ...}`` 或
  ``{"ok": false, "error": {"type", "code", "message"}}``；
- 错误按 ``type`` 还原为 ``errors.py`` 中的同名异常并 ``raise``（未知类型 → ``LedgerError``）。

客户端与 ``LedgerService`` / ``LedgerReader`` 暴露同名方法、同名参数。
"""

import base64
import json
import socket
from pathlib import Path

from . import errors
from .errors import LedgerError

# 协议里 bytes 结果的编码键
DATA_B64 = "data_b64"

# errors.py 中可还原的异常类（键为类名）
ERROR_TYPES = {
    name: value
    for name, value in vars(errors).items()
    if isinstance(value, type) and issubclass(value, LedgerError)
}


def restore_error(payload):
    """把错误响应还原为同名异常；未知 ``type`` 或缺失字段回落到 ``LedgerError``。"""
    payload = payload or {}
    cls = ERROR_TYPES.get(payload.get("type"), LedgerError)
    exc = cls(payload.get("message", ""))
    code = payload.get("code")
    if code is not None:
        exc.code = code
    return exc


class LedgerClient:
    """本地 Ledger 客户端：``LedgerClient(socket_path)``。

    保持一条长连接（协议允许一个连接多请求）；``close()`` 关闭连接。
    """

    def __init__(self, socket_path):
        self.socket_path = Path(socket_path)
        self._sock = None
        self._reader = None

    # ------------------------------------------------------------ 连接
    def _socket(self):
        if self._sock is None:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(str(self.socket_path))
            self._sock = sock
            self._reader = sock.makefile("rb")
        return self._sock

    def close(self):
        """关闭连接（幂等）。"""
        if self._reader is not None:
            self._reader.close()
            self._reader = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    # ------------------------------------------------------------ 协议
    def _call(self, op, args):
        """发一次请求并还原响应；``bytes`` 参数自动转 ``*_b64``。"""
        payload = {}
        for key, value in (args or {}).items():
            if isinstance(value, (bytes, bytearray)):
                payload["%s_b64" % key] = base64.b64encode(bytes(value)).decode("ascii")
            else:
                payload[key] = value
        sock = self._socket()
        request = json.dumps({"op": op, "args": payload}, ensure_ascii=False)
        sock.sendall(request.encode("utf-8") + b"\n")
        line = self._reader.readline()
        if not line:
            raise LedgerError("Ledger 服务端未返回响应（连接已关闭）")
        response = json.loads(line.decode("utf-8"))
        if response.get("ok"):
            result = response.get("result")
            if isinstance(result, dict) and set(result.keys()) == {DATA_B64}:
                return base64.b64decode(result[DATA_B64])
            return result
        raise restore_error(response.get("error"))

    def actor(self):
        """见 ``LedgerService.actor``：向服务端查询当前操作者引用。"""
        return self._call("actor", {})

    # ------------------------------------------------- 写 API（LedgerService）
    def create_processing_run(
        self, kind, edition_part_id, technique_id, *, processing_run_id=None
    ):
        """见 ``LedgerService.create_processing_run``。"""
        return self._call(
            "create_processing_run",
            {
                "kind": kind,
                "edition_part_id": edition_part_id,
                "technique_id": technique_id,
                "processing_run_id": processing_run_id,
            },
        )

    def begin_step_run(self, request, *, step_run_id=None):
        """见 ``LedgerService.begin_step_run``。"""
        return self._call(
            "begin_step_run", {"request": request, "step_run_id": step_run_id}
        )

    def put_artifact(
        self,
        step_run_id,
        artifact_type,
        data,
        *,
        artifact_id=None,
        artifact_revision_id=None,
        prev_revision_id=None,
        schema_id=None,
        schema_version=None,
        producer_module,
        producer_version,
        configuration_revision_id=None,
        rights_scope="internal",
    ):
        """见 ``LedgerService.put_artifact``（返回 ``(artifact_id, revision_id)``）。"""
        return tuple(
            self._call(
                "put_artifact",
                {
                    "step_run_id": step_run_id,
                    "artifact_type": artifact_type,
                    "data": data,
                    "artifact_id": artifact_id,
                    "artifact_revision_id": artifact_revision_id,
                    "prev_revision_id": prev_revision_id,
                    "schema_id": schema_id,
                    "schema_version": schema_version,
                    "producer_module": producer_module,
                    "producer_version": producer_version,
                    "configuration_revision_id": configuration_revision_id,
                    "rights_scope": rights_scope,
                },
            )
        )

    def put_run_artifact(
        self,
        processing_run_id,
        artifact_type,
        data,
        *,
        artifact_id=None,
        artifact_revision_id=None,
        producer_module,
        producer_version,
        rights_scope="internal",
        schema_id=None,
        schema_version=None,
    ):
        """见 ``LedgerService.put_run_artifact``（返回 ``(artifact_id, revision_id)``）。"""
        return tuple(
            self._call(
                "put_run_artifact",
                {
                    "processing_run_id": processing_run_id,
                    "artifact_type": artifact_type,
                    "data": data,
                    "artifact_id": artifact_id,
                    "artifact_revision_id": artifact_revision_id,
                    "producer_module": producer_module,
                    "producer_version": producer_version,
                    "rights_scope": rights_scope,
                    "schema_id": schema_id,
                    "schema_version": schema_version,
                },
            )
        )

    def seal_revision(self, artifact_revision_id, *, validation_report_revision_id=None):
        """见 ``LedgerService.seal_revision``。"""
        return self._call(
            "seal_revision",
            {
                "artifact_revision_id": artifact_revision_id,
                "validation_report_revision_id": validation_report_revision_id,
            },
        )

    def quarantine_revision(
        self, artifact_revision_id, reason, *, validation_report_revision_id=None
    ):
        """见 ``LedgerService.quarantine_revision``。"""
        return self._call(
            "quarantine_revision",
            {
                "artifact_revision_id": artifact_revision_id,
                "reason": reason,
                "validation_report_revision_id": validation_report_revision_id,
            },
        )

    def invalidate_revision(self, artifact_revision_id, reason):
        """见 ``LedgerService.invalidate_revision``。"""
        return self._call(
            "invalidate_revision",
            {"artifact_revision_id": artifact_revision_id, "reason": reason},
        )

    def supersede_revision(self, old_revision_id, new_revision_id):
        """见 ``LedgerService.supersede_revision``。"""
        return self._call(
            "supersede_revision",
            {
                "old_revision_id": old_revision_id,
                "new_revision_id": new_revision_id,
            },
        )

    def register_stage_package(
        self,
        step_run_id,
        package,
        data,
        *,
        stage_package_id=None,
        artifact_revision_id=None,
    ):
        """见 ``LedgerService.register_stage_package``。"""
        return tuple(
            self._call(
                "register_stage_package",
                {
                    "step_run_id": step_run_id,
                    "package": package,
                    "data": data,
                    "stage_package_id": stage_package_id,
                    "artifact_revision_id": artifact_revision_id,
                },
            )
        )

    def record_transformation(
        self,
        step_run_id,
        *,
        operation,
        tool,
        tool_version,
        configuration_revision_id,
        input_revision_ids,
        output_revision_ids,
        model_ref=None,
        validation_report_revision_id=None,
        human_event_revision_ids=(),
    ):
        """见 ``LedgerService.record_transformation``。"""
        return self._call(
            "record_transformation",
            {
                "step_run_id": step_run_id,
                "operation": operation,
                "tool": tool,
                "tool_version": tool_version,
                "configuration_revision_id": configuration_revision_id,
                "input_revision_ids": list(input_revision_ids),
                "output_revision_ids": list(output_revision_ids),
                "model_ref": model_ref,
                "validation_report_revision_id": validation_report_revision_id,
                "human_event_revision_ids": list(human_event_revision_ids),
            },
        )

    def await_human(self, step_run_id, pending_queue_revision_ids):
        """见 ``LedgerService.await_human``。"""
        return self._call(
            "await_human",
            {
                "step_run_id": step_run_id,
                "pending_queue_revision_ids": list(pending_queue_revision_ids),
            },
        )

    def record_human_event(
        self, step_run_id, resume_token, event_artifact_revision_id, *, decision_type=None
    ):
        """见 ``LedgerService.record_human_event``。"""
        return self._call(
            "record_human_event",
            {
                "step_run_id": step_run_id,
                "resume_token": resume_token,
                "event_artifact_revision_id": event_artifact_revision_id,
                "decision_type": decision_type,
            },
        )

    def resume(self, step_run_id, resume_token):
        """见 ``LedgerService.resume``。"""
        return self._call(
            "resume", {"step_run_id": step_run_id, "resume_token": resume_token}
        )

    def suspend(self, step_run_id, reason, source):
        """见 ``LedgerService.suspend``。"""
        return self._call(
            "suspend", {"step_run_id": step_run_id, "reason": reason, "source": source}
        )

    def recover(self, step_run_id, reason):
        """见 ``LedgerService.recover``。"""
        return self._call(
            "recover", {"step_run_id": step_run_id, "reason": reason}
        )

    def fail_step_run(self, step_run_id, failure_revision_ids, reason):
        """见 ``LedgerService.fail_step_run``。"""
        return self._call(
            "fail_step_run",
            {
                "step_run_id": step_run_id,
                "failure_revision_ids": list(failure_revision_ids),
                "reason": reason,
            },
        )

    def finish_step_run(self, step_run_id, result):
        """见 ``LedgerService.finish_step_run``。"""
        return self._call(
            "finish_step_run", {"step_run_id": step_run_id, "result": result}
        )

    def supersede_step_run(self, old_step_run_id, new_request, *, step_run_id=None):
        """见 ``LedgerService.supersede_step_run``。"""
        return self._call(
            "supersede_step_run",
            {
                "old_step_run_id": old_step_run_id,
                "new_request": new_request,
                "step_run_id": step_run_id,
            },
        )

    def write_checkpoint(
        self,
        step_run_id,
        *,
        edition_part_id,
        stage,
        completed_tasks,
        human_decisions,
        pending_queue,
        next_pointer,
        rework_impact_report_revision_id=None,
        artifact_id=None,
        artifact_revision_id=None,
    ):
        """见 ``LedgerService.write_checkpoint``。"""
        return self._call(
            "write_checkpoint",
            {
                "step_run_id": step_run_id,
                "edition_part_id": edition_part_id,
                "stage": stage,
                "completed_tasks": list(completed_tasks),
                "human_decisions": list(human_decisions),
                "pending_queue": list(pending_queue),
                "next_pointer": next_pointer,
                "rework_impact_report_revision_id": rework_impact_report_revision_id,
                "artifact_id": artifact_id,
                "artifact_revision_id": artifact_revision_id,
            },
        )

    def recover_from_checkpoint(
        self, edition_part_id, stage, new_request, *, step_run_id=None
    ):
        """见 ``LedgerService.recover_from_checkpoint``。"""
        result = self._call(
            "recover_from_checkpoint",
            {
                "edition_part_id": edition_part_id,
                "stage": stage,
                "new_request": new_request,
                "step_run_id": step_run_id,
            },
        )
        return (result[0], result[1])

    # --------------------------------------------- 只读 API（LedgerReader）
    def get_revision(self, artifact_revision_id):
        """见 ``LedgerReader.get_revision``。"""
        return self._call(
            "get_revision", {"artifact_revision_id": artifact_revision_id}
        )

    def get_step_run(self, step_run_id):
        """见 ``LedgerReader.get_step_run``。"""
        return self._call("get_step_run", {"step_run_id": step_run_id})

    def list_step_run_events(self, step_run_id):
        """见 ``LedgerReader.list_step_run_events``。"""
        return self._call("list_step_run_events", {"step_run_id": step_run_id})

    def list_transformations(self, step_run_id):
        """见 ``LedgerReader.list_transformations``。"""
        return self._call("list_transformations", {"step_run_id": step_run_id})

    def latest_checkpoint(self, edition_part_id, stage):
        """见 ``LedgerReader.latest_checkpoint``。"""
        return self._call(
            "latest_checkpoint",
            {"edition_part_id": edition_part_id, "stage": stage},
        )

    def list_checkpoints(self, edition_part_id, stage):
        """见 ``LedgerReader.list_checkpoints``。"""
        return self._call(
            "list_checkpoints",
            {"edition_part_id": edition_part_id, "stage": stage},
        )

    def run_status(self, processing_run_id):
        """见 ``LedgerReader.run_status``。"""
        return self._call("run_status", {"processing_run_id": processing_run_id})

    def stage_progress(self, processing_run_id):
        """见 ``LedgerReader.stage_progress``。"""
        return self._call(
            "stage_progress", {"processing_run_id": processing_run_id}
        )

    def read_object(self, sha256):
        """见 ``LedgerReader.read_object``。"""
        return self._call("read_object", {"sha256": sha256})

    def describe_revision(self, artifact_revision_id):
        """见 ``LedgerReader.describe_revision``。"""
        return self._call("describe_revision", {"artifact_revision_id": artifact_revision_id})

    def list_step_run_revisions(self, step_run_id, artifact_type=None, status=None):
        """见 ``LedgerReader.list_step_run_revisions``。"""
        return self._call(
            "list_step_run_revisions",
            {"step_run_id": step_run_id, "artifact_type": artifact_type, "status": status},
        )

    def list_artifact_revisions(self, artifact_id):
        """见 ``LedgerReader.list_artifact_revisions``。"""
        return self._call("list_artifact_revisions", {"artifact_id": artifact_id})

    def list_frozen_inputs(self, step_run_id):
        """见 ``LedgerReader.list_frozen_inputs``。"""
        return self._call("list_frozen_inputs", {"step_run_id": step_run_id})

    def get_processing_run(self, processing_run_id):
        """见 ``LedgerReader.get_processing_run``。"""
        return self._call("get_processing_run", {"processing_run_id": processing_run_id})

    def list_step_runs(self, edition_part_id, stage=None):
        """见 ``LedgerReader.list_step_runs``。"""
        return self._call("list_step_runs", {"edition_part_id": edition_part_id, "stage": stage})

    def list_stage_packages(self, stage):
        """见 ``LedgerReader.list_stage_packages``。"""
        return self._call("list_stage_packages", {"stage": stage})

    def count_artifacts(self, artifact_type):
        """见 ``LedgerReader.count_artifacts``。"""
        return self._call("count_artifacts", {"artifact_type": artifact_type})

    def latest_processing_run(self, edition_part_id, kind):
        """见 ``LedgerReader.latest_processing_run``。"""
        return self._call("latest_processing_run", {"edition_part_id": edition_part_id, "kind": kind})

    def latest_checkpoint_step_run(self, edition_part_id, stage, status):
        """见 ``LedgerReader.latest_checkpoint_step_run``。"""
        return self._call(
            "latest_checkpoint_step_run",
            {"edition_part_id": edition_part_id, "stage": stage, "status": status},
        )

    def list_revisions(
        self,
        artifact_type=None,
        status=None,
        step_run_ids=None,
        processing_run_id=None,
        prev_revision_id=None,
    ):
        """见 ``LedgerReader.list_revisions``。"""
        return self._call(
            "list_revisions",
            {
                "artifact_type": artifact_type,
                "status": status,
                "step_run_ids": None if step_run_ids is None else list(step_run_ids),
                "processing_run_id": processing_run_id,
                "prev_revision_id": prev_revision_id,
            },
        )

    def list_human_events(self, step_run_id=None):
        """见 ``LedgerReader.list_human_events``。"""
        return self._call("list_human_events", {"step_run_id": step_run_id})

    def list_transformation_inputs(self, transformation_id):
        """见 ``LedgerReader.list_transformation_inputs``。"""
        return self._call("list_transformation_inputs", {"transformation_id": transformation_id})

    def list_transformation_outputs(self, transformation_id):
        """见 ``LedgerReader.list_transformation_outputs``。"""
        return self._call("list_transformation_outputs", {"transformation_id": transformation_id})

    def list_transformation_human_events(self, transformation_id):
        """见 ``LedgerReader.list_transformation_human_events``。"""
        return self._call(
            "list_transformation_human_events", {"transformation_id": transformation_id}
        )

    # —— T03c M7 新增 ——
    def get_stage_package(self, stage_package_id=None, artifact_id=None):
        """见 ``LedgerReader.get_stage_package``。"""
        params = {}
        if stage_package_id is not None:
            params["stage_package_id"] = stage_package_id
        if artifact_id is not None:
            params["artifact_id"] = artifact_id
        return self._call("get_stage_package", params)


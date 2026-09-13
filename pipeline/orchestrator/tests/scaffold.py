"""Orchestrator 测试的公共脚手架（只使用 tempfile 目录）。

提供：临时 Ledger 上的 ProcessingRun + 已封存配置修订 + StepRun 请求；
以及 StagePackage Schema 校验器（注册 ``artifact_ref.schema.json`` 供 ``$ref`` 解析）。
"""

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema
from referencing import Registry as _RefRegistry, Resource
from referencing.jsonschema import DRAFT202012

from pipeline.contract_registry.ports import DirectLedgerAdapter
from pipeline.ledger import ids

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS_DIR = REPO_ROOT / "openspec" / "schemas"


def load_validator(name):
    """加载一个 Draft 2020-12 校验器，注册 ``artifact_ref.schema.json``。"""
    schema = json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))
    artifact_ref = json.loads(
        (SCHEMAS_DIR / "artifact_ref.schema.json").read_text(encoding="utf-8")
    )
    registry = _RefRegistry().with_resource(
        "artifact_ref.schema.json",
        Resource.from_contents(artifact_ref, default_specification=DRAFT202012),
    )
    return jsonschema.Draft202012Validator(schema, registry=registry)


def make_step_request(processing_run_id, configuration_revision_id, *, input_artifact_ids=()):
    """构造一份过 Schema 的 StepRequest。"""
    return {
        "schema_version": "1.0.0",
        "processing_run_id": processing_run_id,
        "step_run_id": ids.new_id("step_run_id"),
        "input_artifact_ids": list(input_artifact_ids),
        "technique_profile_id": "qizheng",
        "configuration_artifact_id": configuration_revision_id,
    }


class LedgerTestCase(unittest.TestCase):
    """公共脚手架：临时 Ledger 根、ProcessingRun 与配置修订。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "ledger"
        self.adapter = DirectLedgerAdapter(self.root)
        self.addCleanup(self.adapter.close)

    def start_run(self, technique_id="qizheng"):
        """建一个 edition_run 并返回 ``(processing_run_id, edition_part_id)``。"""
        edition_part_id = ids.new_id("artifact_id")
        processing_run_id = self.adapter.create_processing_run(
            "edition_run", edition_part_id, technique_id
        )
        return processing_run_id, edition_part_id

    def seed_configuration(self, processing_run_id, stage="m1", module_id=None, tasks=None):
        """写入一个 ``configuration`` 运行级修订（内容含 stage/module_id/tasks）。"""
        configuration = {
            "stage": stage,
            "module_id": module_id or ("stub.%s" % stage),
            "tasks": list(tasks if tasks is not None else ["t1", "t2"]),
        }
        data = json.dumps(configuration, sort_keys=True, ensure_ascii=False).encode("utf-8")
        _artifact_id, revision_id = self.adapter.put_run_artifact(
            processing_run_id,
            "configuration",
            data,
            producer_module="tests",
            producer_version="1.0",
        )
        return revision_id

    def begin(self, processing_run_id, configuration_revision_id, *, input_artifact_ids=()):
        """开启一个 StepRun 并返回其 step_run_id。"""
        request = make_step_request(
            processing_run_id,
            configuration_revision_id,
            input_artifact_ids=input_artifact_ids,
        )
        self.adapter.begin_step_run(request)
        return request

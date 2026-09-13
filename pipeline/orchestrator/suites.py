"""§20.10 存储端口一致性套件（规格 §20 第 10 条）。

放在 ``orchestrator`` 包内，使 ``contract_registry`` 的 ``catalog``/``ports``/
``conformance`` 保持不反向依赖 ``orchestrator``。套件在一根端口上跑完
``m1 → m2（人工挂起/恢复）→ m3``，产出可跨 Adapter 比对的运行事实。
"""

import json

from pipeline.contract_registry import DEFAULT_REGISTRY_PATH
from pipeline.contract_registry.catalog import Registry
from pipeline.ledger import ids

from .edition_run import run_until, start_edition_run
from .human import record_human_event, resume
from .stubs import StubModule

# 套件覆盖的阶段（首纵切前缀，含人工恢复路径）
SUITE_STAGES = ("m1", "m2", "m3", "m5")


def _suite_registry(stubs):
    import yaml

    doc = yaml.safe_load(DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8"))
    doc["modules"] = [stub.descriptor() for stub in stubs]
    return Registry.from_dict(
        doc, repo_root=DEFAULT_REGISTRY_PATH.resolve().parents[2], allow_stub=True
    )


def stub_edition_suite(port):
    """在 ``port`` 上跑一套桩版 EditionRun（含人工挂起与恢复），返回 ``processing_run_id``。"""
    stubs = [
        StubModule("m1"),
        StubModule("m2", human_queue=True),
        StubModule("m3"),
    ]
    registry = _suite_registry(stubs)
    modules = {stub.module_id: stub for stub in stubs}
    handle = start_edition_run(
        port, edition_part_id=ids.new_id("artifact_id"), technique_id="qizheng"
    )

    results = run_until(port, registry, handle, "m2", modules=modules)
    item = results[-1]
    step_run_id = item["step_run_id"]
    if (item.get("step_result") or {}).get("status") != "awaiting_human":
        raise RuntimeError("stub_edition_suite: m2 未进入 awaiting_human")
    token = item["step_result"]["resume_token"]

    _artifact_id, event_revision_id = port.put_artifact(
        step_run_id,
        "human_event",
        json.dumps({"decision": "stub_accept"}, sort_keys=True).encode("utf-8"),
        producer_module="stub.reviewer",
        producer_version="0.0.0",
    )
    port.seal_revision(event_revision_id)
    record_human_event(
        port, registry, handle, step_run_id, token, event_revision_id, modules=modules
    )
    resume(port, registry, handle, step_run_id, token, modules=modules)
    run_until(port, registry, handle, "m3", modules=modules)
    return handle["processing_run_id"]

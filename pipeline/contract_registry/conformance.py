"""Adapter 替换判定的规范化与报告（规格 §20.10）。

``normalize_outcome`` 把一次 ProcessingRun 的运行事实压成「去 ID、去时间」的可比对
结构；``substitution_report`` 在两个及以上 Adapter 上跑同一套件，比较规范化结果与相邻
Module Interface 指纹，给出 ``substitutable`` 结论。

本模块为纯逻辑，不依赖编排层，也不写 Ledger。
"""

import json

from .ports import PortGuard, missing_port_methods


def _as_json(value):
    """把 ``request_json`` / ``result_json``（字符串或已是对象）解析为对象或 ``None``。"""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return value


def normalize_outcome(port, processing_run_id):
    """把 ProcessingRun 的运行事实规范化为可比对结构（不含任何 ID 或时间）。"""
    status = port.run_status(processing_run_id)
    step_runs = sorted(
        status.get("step_runs") or [], key=lambda step: step.get("created_at") or ""
    )
    steps = []
    for step in step_runs:
        request = _as_json(step.get("request_json"))
        result = _as_json(step.get("result_json"))
        step_run_id = step.get("step_run_id")
        steps.append(
            {
                "stage": step.get("stage"),
                "status": step.get("status"),
                "input_count": (
                    len(request.get("input_artifact_ids", []))
                    if isinstance(request, dict)
                    else 0
                ),
                "output_count": (
                    len(result.get("output_artifact_ids", []))
                    if isinstance(result, dict)
                    else 0
                ),
                "failure_count": (
                    len(result.get("failure_artifact_ids", []))
                    if isinstance(result, dict)
                    else 0
                ),
                "supersedes": bool(step.get("supersedes_step_run_id")),
                "transformations": len(port.list_transformations(step_run_id)),
                "event_types": [
                    event["event_type"]
                    for event in port.list_step_run_events(step_run_id)
                ],
            }
        )
    return {"run_status": status.get("status"), "steps": steps}


def substitution_report(port_id, adapter_factories, suite, *, fingerprint):
    """在两个及以上 Adapter 上跑 ``suite``，判定同一端口换 Adapter 后是否可替换。

    :param adapter_factories: ``{adapter_id: 无参可调用}``，返回 ``(port, cleanup)``。
    :param suite: 可调用 ``(port) -> processing_run_id``。
    :param fingerprint: 可调用 ``(adapter_id) -> str``，相邻 Module Interface 指纹。
    """
    adapters = sorted(adapter_factories)
    conformant = {}
    outcomes = {}
    fingerprints = {}
    problems = []

    for adapter_id in adapters:
        port = None
        cleanup = None
        try:
            port, cleanup = adapter_factories[adapter_id]()
            missing = missing_port_methods(port)
            if missing:
                raise AttributeError("缺 LedgerPort 方法: %s" % ", ".join(missing))
            processing_run_id = suite(PortGuard(port))
            outcomes[adapter_id] = normalize_outcome(port, processing_run_id)
            conformant[adapter_id] = True
        except Exception as exc:  # noqa: BLE001 - 记为问题而非中断
            conformant[adapter_id] = False
            outcomes[adapter_id] = None
            problems.append("%s: %s: %s" % (adapter_id, type(exc).__name__, exc))
        finally:
            if cleanup is not None:
                cleanup()

    for adapter_id in adapters:
        try:
            fingerprints[adapter_id] = fingerprint(adapter_id)
        except Exception as exc:  # noqa: BLE001 - 记为问题而非中断
            fingerprints[adapter_id] = None
            problems.append("%s: fingerprint: %s" % (adapter_id, exc))

    normalized = [
        json.dumps(outcomes[adapter_id], sort_keys=True, ensure_ascii=False)
        for adapter_id in adapters
    ]
    outcomes_equal = bool(
        len(adapters) >= 2
        and all(conformant.values())
        and len(set(normalized)) == 1
    )
    interface_equal = bool(
        len(adapters) >= 2
        and all(value is not None for value in fingerprints.values())
        and len(set(fingerprints.values())) == 1
    )
    if len(adapters) < 2:
        problems.append("端口 %s 仅 %d 个 Adapter" % (port_id, len(adapters)))

    substitutable = bool(
        len(adapters) >= 2
        and all(conformant.values())
        and outcomes_equal
        and interface_equal
    )
    return {
        "port_id": port_id,
        "adapters": adapters,
        "conformant": conformant,
        "outcomes": outcomes,
        "outcomes_equal": outcomes_equal,
        "interface_equal": interface_equal,
        "substitutable": substitutable,
        "problems": problems,
    }

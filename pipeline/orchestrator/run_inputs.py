"""EditionRun 运行输入（TODO T04A 裁决 2/3）。

调度器**不**按「有没有某种产物」猜路线：运行输入里必须显式声明 ``route``。当前生产
登记表只登记电子文本路线（``route: text``）；OCR 路线的 M2 尚无生产模块，遇非 ``text``
一律拒收（理由逐字含「OCR 路线 M2 无生产模块（TODO T04c）」）。

运行输入在 ``start_edition_run`` 时落成运行级 ``configuration`` 修订（route + 来源目录 +
来源申报件）；``run_inputs`` 内**不得**含任何人工 token 或密钥。
"""

import json

from . import ORCH_TOOL, ORCH_TOOL_VERSION
from .errors import OrchestratorRefused

# 唯一受支持的路线（裁决 2）
TEXT_ROUTE = "text"

# 非 text 路线的一律拒收理由（逐字，含 TODO 编号）
OCR_ROUTE_REFUSAL = "OCR 路线 M2 无生产模块（TODO T04c）"

# 运行输入必备键（route 之外）
_REQUIRED_INPUT_KEYS = ("source_dir", "source_info")


def validate_run_inputs(run_inputs):
    """校验运行输入；返回原字典（不修改）。"""
    if not isinstance(run_inputs, dict):
        raise OrchestratorRefused(
            "缺少 EditionRun 运行输入：route 必须显式声明为 %r；%s"
            % (TEXT_ROUTE, OCR_ROUTE_REFUSAL)
        )
    route = run_inputs.get("route")
    if route != TEXT_ROUTE:
        raise OrchestratorRefused(
            "运行输入 route=%r 不受支持；%s" % (route, OCR_ROUTE_REFUSAL)
        )
    for key in _REQUIRED_INPUT_KEYS:
        if not run_inputs.get(key):
            raise OrchestratorRefused("运行输入缺必备键: %s" % key)
    if not isinstance(run_inputs.get("source_info"), dict):
        raise OrchestratorRefused("运行输入 source_info 必须是 dict")
    return run_inputs


def encode_run_inputs(run_inputs):
    """把运行输入序列化为运行级 configuration 修订的字节。"""
    return json.dumps(run_inputs, sort_keys=True, ensure_ascii=False).encode("utf-8")


def persist_run_inputs(port, processing_run_id, run_inputs):
    """把运行输入登记为运行级 ``configuration`` 修订，返回修订号。"""
    validate_run_inputs(run_inputs)
    _artifact_id, revision_id = port.put_run_artifact(
        processing_run_id,
        "configuration",
        encode_run_inputs(run_inputs),
        producer_module=ORCH_TOOL,
        producer_version=ORCH_TOOL_VERSION,
    )
    return revision_id

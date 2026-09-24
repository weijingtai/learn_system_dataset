"""EditionRun 运行输入（TODO T04A 裁决 2/3）。

调度器**不**按「有没有某种产物」猜路线：运行输入里必须显式声明 ``route``。当前生产
登记表只登记电子文本路线（``route: text``）；OCR 路线的 M2 尚无生产模块，遇非 ``text``
一律拒收（理由逐字含「OCR 路线 M2 无生产模块（TODO T04c）」）。

运行输入在 ``start_edition_run`` 时落成运行级 ``configuration`` 修订（route + 来源目录 +
来源申报件 + M4 技法画像配置）；``run_inputs`` 内**不得**含任何人工 token 或密钥。

``technique_profile``（TODO T04A 第 2 项）：``{technique_id, canon_dir}``，恰此两键、均为非空
字符串，``technique_id`` 必须等于 EditionRun 的技法号。M4 薄适配据此在本运行下登记运行级
``technique_profile`` 修订；路径全部由运行输入给出，调度器不读盘、不 import 加工 Module。
"""

import json

from . import ORCH_TOOL, ORCH_TOOL_VERSION
from .errors import OrchestratorRefused

# 唯一受支持的路线（裁决 2）
TEXT_ROUTE = "text"

# 非 text 路线的一律拒收理由（逐字，含 TODO 编号）
OCR_ROUTE_REFUSAL = "OCR 路线 M2 无生产模块（TODO T04c）"

# 运行输入必备键（route 之外）
_REQUIRED_INPUT_KEYS = ("source_dir", "source_info", "technique_profile")

# ``technique_profile`` 的键闭集（按字母序）
TECHNIQUE_PROFILE_KEYS = ("canon_dir", "technique_id")


def _validate_technique_profile(profile, technique_id):
    if not isinstance(profile, dict) or sorted(profile) != list(TECHNIQUE_PROFILE_KEYS):
        raise OrchestratorRefused(
            "运行输入 technique_profile 必须是恰含 %s 两键的 dict"
            % "/".join(TECHNIQUE_PROFILE_KEYS)
        )
    for key in TECHNIQUE_PROFILE_KEYS:
        if not isinstance(profile[key], str) or not profile[key]:
            raise OrchestratorRefused(
                "运行输入 technique_profile.%s 必须是非空字符串" % key
            )
    if technique_id is not None and profile["technique_id"] != technique_id:
        raise OrchestratorRefused(
            "运行输入 technique_profile.technique_id=%r 与 EditionRun 技法 %r 不一致"
            % (profile["technique_id"], technique_id)
        )


def validate_run_inputs(run_inputs, technique_id=None):
    """校验运行输入；返回原字典（不修改）。

    ``technique_id`` 给出时，``technique_profile.technique_id`` 必须与之相等。
    """
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
    _validate_technique_profile(run_inputs["technique_profile"], technique_id)
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

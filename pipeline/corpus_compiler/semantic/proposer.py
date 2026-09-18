from typing import Optional
"""M3 语义层 Proposer Adapter：请求体构造、录制回放与禁用桩（act/04，P6）。

零模型调用、零网络是首纵切红线（P6）：本模块**不得**引入任何网络库，也不得含任何
真实模型调用代码——act/04 contract 第 4 条点名的网络库，在本文件中一个都不出现。
可选的两条实现路径：

    1. ``ReplayProposer``：回放预先录制的手写合成响应（录制文档须标 ``synthetic: true``）；
    2. ``LiveProposer``：真实调用**桩**，未设环境变量即拒绝构造，设了之后 ``propose`` 仍恒抛
       ``ModelCallDisabled``——本批不提供任何真实调用实现。

请求体隔离（§12.2）：``build_request`` 只携带**当前窗口**原文，严禁泄漏其它窗口或对端
slot 的内容。
"""

import hashlib
import json
import os

import yaml

from pipeline.corpus_compiler.semantic.prompt_registry import (
    PromptProfile,
    PromptRegistry,
    get_default_registry,
)

# 提示词模板标识（向后兼容默认常量，防模板漂移）
PROMPT_TEMPLATE_ID = "m3_boundary_v1"

_default_profile = get_default_registry().require(PROMPT_TEMPLATE_ID)

# 古籍语义切分提示词模板：只输出 JSON，不复述原文（由资产注册表提供）
PROMPT_TEMPLATE = _default_profile.template

# 模板指纹：由资产内容自洽生成（防模板漂移，向后兼容常量）
PROMPT_TEMPLATE_SHA256 = _default_profile.sha256

# 录制文档 schema 标识
RECORDINGS_SCHEMA = "m3_boundary_recordings/1"

# LiveProposer 的启用开关：未设即禁用（首纵切恒禁用）
LIVE_PROPOSER_ENV_FLAG = "M3_SEMANTIC_LIVE_PROPOSER"

# 允许的提议方 slot
ALLOWED_SLOTS = ("a", "b")


class ModelCallDisabled(RuntimeError):
    """P6：首纵切禁止真实模型调用，任何真实调用路径都必须抛本异常。"""


class RecordingMiss(LookupError):
    """回放录制缺失：该 (window_id, slot) 无对应录制内容。"""


class RecordingSchemaError(ValueError):
    """录制文档不合规（schema / synthetic / template_id / 结构不符）。"""


def build_request(
    *,
    slot: str,
    model: dict,
    window: dict,
    template_id: str = PROMPT_TEMPLATE_ID,
    registry: Optional[PromptRegistry] = None,
) -> bytes:
    """为一侧模型构造切分请求体（确定性字节）。

    参数：
        slot: 提议方标识，必须为 ``"a"`` 或 ``"b"``。
        model: 模型描述映射（原样随请求携带）。
        window: 窗口字典（须含 ``window_id`` 与 ``text``）。

    返回：
        UTF-8 编码的 JSON 字节；同一入参反复构造结果**逐字节相同**。

    纪律（§12.2）：
        请求体只包含 ``window["text"]`` 这一份原文；不得携带其它窗口的文本、
        其它窗口的 ID，也不得携带对端 slot 的任何内容。

    异常：
        ValueError("SCH_002: ...")：slot 非法、window/model 形不符或窗口文本为空。
    """
    if slot not in ALLOWED_SLOTS:
        raise ValueError("SCH_002: slot 必须为 'a' 或 'b'，实际 %r" % (slot,))
    if not isinstance(window, dict):
        raise ValueError("SCH_002: window 必须为映射")
    if not isinstance(model, dict):
        raise ValueError("SCH_002: model 必须为映射")

    text = window.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("SCH_002: window.text 必须为非空字符串")

    reg = registry or get_default_registry()
    profile = reg.get(template_id)
    template_text = profile.template if profile else PROMPT_TEMPLATE
    prompt_id = profile.prompt_id if profile else template_id
    prompt_version = profile.version if profile else "1.0.0"
    prompt_sha256 = profile.sha256 if profile else PROMPT_TEMPLATE_SHA256

    payload = {
        "schema_version": "1.0.0",
        "template_id": template_id,
        "prompt_id": prompt_id,
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_sha256,
        "template": template_text,
        "slot": slot,
        "model": model,
        "window_id": window.get("window_id"),
        "window_text": text,
        "window_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")


def load_recordings(data: bytes, *, registry: Optional[PromptRegistry] = None) -> dict:
    """解析并校验回放录制文档。

    校验项（任一不符即抛 ``RecordingSchemaError``）：
        ``schema == "m3_boundary_recordings/1"``、``synthetic is True``（不得冒充真实模型
        输出）、``template_id == PROMPT_TEMPLATE_ID``、``recordings`` 为列表。
    """
    if not isinstance(data, (bytes, bytearray)):
        raise RecordingSchemaError("recordings 必须是字节")

    try:
        doc = yaml.safe_load(bytes(data).decode("utf-8"))
    except Exception as exc:
        raise RecordingSchemaError("recordings 不是合法 YAML/JSON: %s" % exc)

    if not isinstance(doc, dict):
        raise RecordingSchemaError("recordings 顶层必须是映射")

    if doc.get("schema") != RECORDINGS_SCHEMA:
        raise RecordingSchemaError(
            "schema 必须为 %r，实际 %r" % (RECORDINGS_SCHEMA, doc.get("schema"))
        )

    if doc.get("synthetic") is not True:
        raise RecordingSchemaError(
            "录制必须显式标注 synthetic: true（合成回放，不得冒充真实模型输出）"
        )

    reg = registry or get_default_registry()
    doc_template_id = doc.get("template_id")
    if not reg.contains(doc_template_id):
        raise RecordingSchemaError(
            "未知的 template_id: %r（未在 PromptRegistry 注册）" % (doc_template_id,)
        )

    if not isinstance(doc.get("recordings"), list):
        raise RecordingSchemaError("recordings 必须是列表")

    return doc


class ReplayProposer:
    """回放式提议器：只返回预先录制的合成响应，不做任何模型调用（P6）。"""

    def __init__(self, recordings: dict):
        if not isinstance(recordings, dict):
            raise RecordingSchemaError("recordings 必须是 load_recordings 返回的映射")

        self._recordings = recordings
        self._index: dict[tuple, str] = {}
        for item in recordings.get("recordings") or []:
            if not isinstance(item, dict):
                raise RecordingSchemaError("录制项必须是映射")
            response = item.get("response")
            if not isinstance(response, str):
                raise RecordingSchemaError(
                    "录制项缺 response 字符串: window_id=%r" % (item.get("window_id"),)
                )
            self._index[(item.get("window_id"), item.get("slot"))] = response

    def propose(self, *, slot: str, window: dict) -> bytes:
        """返回该 (window_id, slot) 的录制响应字节；无录制则抛 ``RecordingMiss``。"""
        window_id = window.get("window_id") if isinstance(window, dict) else None
        key = (window_id, slot)
        if key not in self._index:
            raise RecordingMiss(
                "无对应录制: slot=%r window_id=%r" % (slot, window_id)
            )
        return self._index[key].encode("utf-8")


class LiveProposer:
    """真实模型调用桩——**默认禁用**（P6）。

    未设 ``LIVE_PROPOSER_ENV_FLAG`` 时构造即抛 ``ModelCallDisabled``；即便显式设了环境
    变量，``propose`` 仍恒抛 ``ModelCallDisabled``：本批不提供任何真实调用实现。
    """

    def __init__(self):
        if not os.environ.get(LIVE_PROPOSER_ENV_FLAG):
            raise ModelCallDisabled(
                "P6: LiveProposer 默认禁用（未设环境变量 %s）" % LIVE_PROPOSER_ENV_FLAG
            )

    def propose(self, *, slot: str, window: dict) -> bytes:
        """恒禁用：真实调用在本批不存在，任何输入都拒绝。"""
        raise ModelCallDisabled(
            "P6: 首纵切零模型调用；LiveProposer 仅为禁用桩，无真实调用实现"
        )

"""M4 薄适配入口：把 EditionRun 的运行输入接到 ``step.run_m4``（TODO T04A 第 2 项）。

调度器按 ``legacy_self_driving`` 约定调用 ``(service, edition_part_id, *, run_inputs=...)``；
本模块只搬参数，不改变 ``step.run_m4`` 的签名与产出。

运行输入键 ``technique_profile``：``{"technique_id": ..., "canon_dir": ...}``，路径全部由运行
输入给出，本模块不写死任何路径。本运行（M3 产出所在的 ProcessingRun，也就是 ``run_m4``
解析输入的同一运行）下还没有该技法的 ``technique_profile`` 修订时，经公开函数
``adapters.registry.register_technique_profile`` 登记一次；已有则不重复登记。
运行输入不合法、技法号与本运行不符、canon 目录不存在或没有 ``*.yaml`` 时一律拒收，
拒收发生在任何写入之前。
"""

from pathlib import Path

from .adapters.registry import register_technique_profile
from .errors import ExtractionRefused
from .inputs import _profile_revisions, resolve_m3_outputs
from .step import run_m4 as _run_m4


def _technique_profile_inputs(run_inputs):
    """校验运行输入并返回 ``(technique_id, canon_dir)``（只读）。"""
    if not isinstance(run_inputs, dict):
        raise ExtractionRefused("缺少运行输入（run_inputs）", code="SCH_001")
    profile = run_inputs.get("technique_profile")
    if not isinstance(profile, dict):
        raise ExtractionRefused("运行输入缺 technique_profile", code="SCH_001")
    technique_id = profile.get("technique_id")
    canon_dir = profile.get("canon_dir")
    if not isinstance(technique_id, str) or not technique_id:
        raise ExtractionRefused(
            "运行输入 technique_profile.technique_id 必须是非空字符串", code="SCH_002"
        )
    if not isinstance(canon_dir, str) or not canon_dir or not Path(canon_dir).is_dir():
        raise ExtractionRefused(
            "运行输入 technique_profile.canon_dir 不是目录: %r" % (canon_dir,),
            code="REF_001",
        )
    if not any(Path(canon_dir).glob("*.yaml")):
        raise ExtractionRefused(
            "运行输入 technique_profile.canon_dir 下没有 canon *.yaml: %s" % canon_dir,
            code="REF_001",
        )
    return technique_id, canon_dir


def run_m4(service, edition_part_id, *, run_inputs=None):
    """调度器入口：按运行输入确保本运行有技法画像，再调用 ``step.run_m4``。"""
    technique_id, canon_dir = _technique_profile_inputs(run_inputs)
    m3 = resolve_m3_outputs(service, edition_part_id)
    if technique_id != m3["technique_id"]:
        raise ExtractionRefused(
            "运行输入 technique_profile.technique_id=%r 与本运行技法 %r 不一致"
            % (technique_id, m3["technique_id"]),
            code="REF_001",
        )
    if not _profile_revisions(service, m3["processing_run_id"], technique_id):
        register_technique_profile(
            service,
            m3["processing_run_id"],
            technique_id=technique_id,
            canon_dir=canon_dir,
        )
    return _run_m4(service, edition_part_id)

"""M2 薄适配入口：把 EditionRun 的运行输入接到 ``run_m2``（TODO T04A 裁决 2）。

调度器按 ``legacy_self_driving`` 约定调用 ``(service, edition_part_id, *, run_inputs=...)``；
本模块只做参数搬运（定位 M1 产出的 ``raw_text`` 修订），不改变 ``run_m2`` 的签名与产出。
"""

from .errors import DigitizationRefused
from .step import run_m2 as _run_m2


def _text_run_inputs(run_inputs):
    """校验运行输入并返回 ``source_info``。"""
    if not isinstance(run_inputs, dict):
        raise DigitizationRefused("缺少运行输入（run_inputs）", code="SCH_001")
    if run_inputs.get("route") != "text":
        raise DigitizationRefused(
            "运行输入 route 非 text: %r" % (run_inputs.get("route"),), code="SCH_002"
        )
    source_info = run_inputs.get("source_info")
    if not isinstance(source_info, dict):
        raise DigitizationRefused("运行输入缺 source_info", code="SCH_001")
    if not run_inputs.get("source_dir"):
        raise DigitizationRefused("运行输入缺 source_dir", code="SCH_001")
    return source_info


def _latest_raw_text_revision_id(service, edition_part_id):
    """定位最近一个 succeeded 的 M1 StepRun 产出的 ``raw_text`` 修订（MP1→M2 输入）。"""
    for row in reversed(service.list_step_runs(edition_part_id, stage="m1")):
        if row.get("status") != "succeeded":
            continue
        revisions = service.list_step_run_revisions(
            row["step_run_id"], artifact_type="raw_text"
        )
        if revisions:
            return revisions[0]["artifact_revision_id"]
    raise DigitizationRefused(
        "找不到 M1 产出的 raw_text 修订（edition_part=%s）" % edition_part_id,
        code="REF_001",
    )


def run_m2(service, edition_part_id, *, run_inputs=None):
    """调度器入口：电子文本路线 M2 清洗（等价于 ``run_m2(service, raw_text_rev, source_info, ep)``）。"""
    source_info = _text_run_inputs(run_inputs)
    raw_text_revision_id = _latest_raw_text_revision_id(service, edition_part_id)
    return _run_m2(service, raw_text_revision_id, source_info, edition_part_id)

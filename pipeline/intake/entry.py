"""M1 薄适配入口：把 EditionRun 的运行输入接到 ``run_m1``（TODO T04A 裁决 2）。

调度器按 ``legacy_self_driving`` 约定调用 ``(service, edition_part_id, *, run_inputs=...)``；
本模块只做参数搬运，不改变 ``run_m1`` 的签名与产出。

运行输入（EditionRun 级 configuration 修订，route 已由调度器校验）：

- ``route``：固定 ``"text"``（电子文本路线）；
- ``source_dir``：来源文件所在目录；
- ``source_info``：来源申报件字典（``source_info.yaml`` 的内容）。

本模块只走 ``read_source_files``（磁盘读取 + 编码归一 + 哈希），不做任何 Ledger 写入。
"""

from pathlib import Path

from .errors import IntakeRefused
from .source import read_source_files
from .step import run_m1 as _run_m1


def _text_run_inputs(run_inputs):
    """校验运行输入并返回 ``(source_dir, source_info)``。"""
    if not isinstance(run_inputs, dict):
        raise IntakeRefused("缺少运行输入（run_inputs）", code="SCH_001")
    if run_inputs.get("route") != "text":
        raise IntakeRefused(
            "运行输入 route 非 text: %r" % (run_inputs.get("route"),), code="SCH_002"
        )
    source_dir = run_inputs.get("source_dir")
    source_info = run_inputs.get("source_info")
    if not source_dir or not isinstance(source_info, dict):
        raise IntakeRefused("运行输入缺 source_dir / source_info", code="SCH_001")
    if not isinstance(source_info.get("pages"), list) or not source_info["pages"]:
        raise IntakeRefused("source_info.pages 必须为非空列表", code="SCH_002")
    return Path(source_dir), source_info


def run_m1(service, edition_part_id, *, run_inputs=None):
    """调度器入口：电子文本路线 M1 入库（等价于 ``run_m1(service, source_info, files, ep)``）。"""
    source_dir, source_info = _text_run_inputs(run_inputs)
    files = read_source_files(source_dir, source_info["pages"])
    return _run_m1(service, source_info, files, edition_part_id)

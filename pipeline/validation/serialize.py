"""M5 内容规范 JSON 序列化。

``canonical_json`` 作为 M5 全部新内容（Validator 报告、``gate_results``、
``validation_package``、配置）的确定性字节形式，保证同一 dict 恒产生同一
字节串，便于 ``content_sha256`` 复算与逐字节比对。
"""

import json


def canonical_json(doc):
    """把 ``doc`` 规范化为确定性 JSON 字节（utf-8）。

    规则：``sort_keys=True``、``ensure_ascii=False``、分隔符压缩为
    ``(",", ":")``。
    """
    return json.dumps(
        doc, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")

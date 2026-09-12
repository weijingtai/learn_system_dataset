"""m3 语料确定性序列化（规格 §11，金标字节对齐）。

序列化规则与金标生成脚本的 ``dump_yaml`` 逐项相同（本模块不 import 该
脚本，仅按同一规则独立实现）：

    yaml.dump(obj, Dumper=_M3Dumper, allow_unicode=True, sort_keys=False,
              default_flow_style=False, width=10**9, indent=2).encode("utf-8")

``_M3Dumper`` 是 ``yaml.SafeDumper`` 的私有子类，只本模块使用；本模块不
向全局 ``yaml.SafeDumper`` 注册任何 representer（避免污染进程内其他
使用 ``yaml.SafeDumper``/``yaml.safe_dump`` 的代码）。
"""

import yaml


class _M3Dumper(yaml.SafeDumper):
    """m3 语料私有 Dumper：继承 SafeDumper 已有 representer，不额外注册。"""


def dump_yaml(obj):
    """把 ``obj`` 序列化为确定性 YAML 字节（utf-8），规则与金标生成器一致。"""
    return yaml.dump(
        obj,
        Dumper=_M3Dumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=10 ** 9,
        indent=2,
    ).encode("utf-8")

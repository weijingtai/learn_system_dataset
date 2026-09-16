"""M1 确定性 YAML 序列化模块。

提供 dump_manifest_yaml 函数，采用私有 _M1Dumper 序列化，
将 64 位十六进制哈希字符串加双引号输出，其他字符串以 plain 输出，
且不向全局 yaml.SafeDumper 注册任何 representer。
"""

import re
import yaml

_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class _M1Dumper(yaml.SafeDumper):
    """M1 专用的 SafeDumper 私有子类。"""


def _str_representer(dumper, data):
    if _HEX64_PATTERN.match(data):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_M1Dumper.add_representer(str, _str_representer)


def dump_manifest_yaml(obj) -> bytes:
    """将对象序列化为确定性的 YAML 字节序列（UTF-8 编码）。

    参数：
        obj：待序列化的字典或列表对象。

    返回：
        UTF-8 编码的 YAML 字节序列。
    """
    return yaml.dump(
        obj,
        Dumper=_M1Dumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=10**9,
        indent=2,
    ).encode("utf-8")

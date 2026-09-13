"""Contract Registry（规格 §19 L2'）：声明式登记 L0 Schema、Stage Module、端口与 Adapter。

本包只使用 Python 标准库 + PyYAML + jsonschema；不 import 任何加工 Module 包，
Module 入口只在登记表中以 ``"模块:属性"`` 字符串声明，由 ``check_registry`` 按需解析。
"""

from pathlib import Path

# 工具的模块标识与版本（登记表顶层 registry_version 与之独立）
REGISTRY_TOOL = "pipeline.contract_registry"
REGISTRY_TOOL_VERSION = "0.1.0"

# 仓库根（pipeline/contract_registry/__init__.py → parents[2]）
REPO_ROOT = Path(__file__).resolve().parents[2]

# 默认登记表路径（仓库内 Git 跟踪的声明式文件）
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "registry.yaml"

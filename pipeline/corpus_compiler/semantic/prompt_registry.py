"""提示词资产管理与注册表（Prompt as Artifact）。

将 Prompt 从硬编码常量解耦为具备版本、自洽性哈希与元数据的独立资产，
支持多版本注册、A/B 评估对比以及全流程审计追溯。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass(frozen=True)
class PromptProfile:
    """提示词资产档案。"""

    prompt_id: str
    version: str
    template_id: str
    description: str
    template: str
    sha256: str
    schema_version: str = "0.1.0-draft"

    @classmethod
    def from_dict(cls, data: dict) -> "PromptProfile":
        prompt_id = data.get("prompt_id") or data.get("template_id", "unknown")
        version = str(data.get("version", "1.0.0"))
        template_id = data.get("template_id") or ("%s_v%s" % (prompt_id, version))
        description = data.get("description", "")
        template = data.get("template", "")
        declared_sha = data.get("sha256")
        actual_sha = hashlib.sha256(template.encode("utf-8")).hexdigest()
        if declared_sha and declared_sha != actual_sha:
            raise ValueError(
                "提示词资产自洽性校验失败: 声明 sha256=%r，实际重算 sha256=%r"
                % (declared_sha, actual_sha)
            )
        return cls(
            prompt_id=prompt_id,
            version=version,
            template_id=template_id,
            description=description,
            template=template,
            sha256=actual_sha,
            schema_version=data.get("schema_version", "0.1.0-draft"),
        )


class PromptRegistry:
    """提示词资产注册表。"""

    def __init__(self, prompts_dir: Optional[Path] = None):
        self._profiles: dict[str, PromptProfile] = {}
        self._prompts_dir = prompts_dir or (Path(__file__).parent / "prompts")
        self._load_from_dir()

    def _load_from_dir(self):
        if not self._prompts_dir.is_dir():
            return
        for file in sorted(self._prompts_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "template" in data:
                    profile = PromptProfile.from_dict(data)
                    self.register(profile)
            except Exception:
                continue

    def register(self, profile: PromptProfile):
        """注册一个提示词档案。"""
        self._profiles[profile.template_id] = profile

    def get(self, template_id: str) -> Optional[PromptProfile]:
        """按 template_id 查询档案；不存在返回 None。"""
        return self._profiles.get(template_id)

    def require(self, template_id: str) -> PromptProfile:
        """按 template_id 查询档案；不存在抛 KeyError。"""
        profile = self.get(template_id)
        if profile is None:
            raise KeyError("未注册的提示词模板标识: %r" % (template_id,))
        return profile

    def list_profiles(self) -> list[PromptProfile]:
        """返回所有已注册的提示词档案列表。"""
        return list(self._profiles.values())

    def contains(self, template_id: str) -> bool:
        """检查 template_id 是否已注册。"""
        return template_id in self._profiles


_DEFAULT_REGISTRY: Optional[PromptRegistry] = None


def get_default_registry() -> PromptRegistry:
    """获取或初始化全局默认提示词注册表。"""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = PromptRegistry()
        # 兜底预置 m3_boundary_v1，确保在无文件环境下绝对可用
        if not _DEFAULT_REGISTRY.contains("m3_boundary_v1"):
            _fallback_m3_v1 = PromptProfile.from_dict(
                {
                    "schema_version": "0.1.0-draft",
                    "prompt_id": "m3_boundary",
                    "version": "1.0.0",
                    "template_id": "m3_boundary_v1",
                    "description": "古籍语义切分提示词模板：只输出 JSON，不复述原文",
                    "sha256": "6982287af738663d077261676d72df32cbbcd55cfbcb0c15365b8cd7fdecee21",
                    "template": (
                        "你是古籍文本的语义切分助手。\n"
                        "任务：把下面给出的【窗口原文】切分为语义完整的片段。\n"
                        "输出要求：\n"
                        "1. 只输出 JSON，形如 "
                        '{"segments": [{"start_offset": 0, "end_offset": 3, "reason": "短语"}]}；\n'
                        "2. 偏移以窗口原文起点为 0，区间左闭右开，必须首尾相连并完整覆盖整个窗口；\n"
                        "3. 不得复述原文，不得在输出中夹带窗口原文的任何整句内容；\n"
                        "4. 不得输出 JSON 之外的解释、注释或 Markdown 代码围栏。\n"
                    ),
                }
            )
            _DEFAULT_REGISTRY.register(_fallback_m3_v1)
    return _DEFAULT_REGISTRY

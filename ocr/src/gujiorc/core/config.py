"""gujiorc.core.config — 配置加载（本地 + Colab 通用）。"""
from __future__ import annotations

from pathlib import Path


DEFAULTS = {
    # OCR
    "ocr": {
        "gap_thresh": 20,          # 区块切分阈值（OCR框y间隙）v2 修复标点合框
        "col_gap_thresh": 30,      # 列聚合阈值
        "conf_thresh": 0.6,        # 低置信度阈值
    },
    # 生僻字判定
    "rare": {
        "common_hanzi": "data/common_hanzi.txt",  # 外部常用字表（相对OCR_ROOT或绝对）
    },
    # 索引
    "index": {
        "db": "index.db",
    },
    # 进度汇报
    "progress": {
        "report_every": 5.0,       # 每 ≥5% 汇报一次
    },
}


def load_config(workdir: str | Path | None = None) -> dict:
    """加载 config.yaml（若存在）并覆盖默认值。

    workdir: 配置所在目录；默认从 OCR_ROOT 找；再 fallback 包目录。
    """
    config = _deep_copy(DEFAULTS)

    candidates = []
    if workdir:
        candidates.append(Path(workdir) / "config.yaml")
    import os
    root = os.environ.get("OCR_ROOT", "")
    if root:
        candidates.append(Path(root) / "config.yaml")

    for cand in candidates:
        if cand and cand.exists():
            try:
                import yaml
                with open(cand, encoding="utf-8") as f:
                    user = yaml.safe_load(f) or {}
                _deep_merge(config, user)
            except Exception:
                pass  # 配置无效则用默认
            break
    return config


def _deep_copy(d):
    import copy
    return copy.deepcopy(d)


def _deep_merge(base: dict, overlay: dict):
    """递归合并 overlay 到 base。"""
    for k, v in overlay.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
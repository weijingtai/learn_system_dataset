"""gujiorc.core.schema — 异常输入校验（M7_）。

对 Colab 输出的 / 本地编辑的 page JSON 做 schema 校验：
- 必填字段齐全
- box 坐标范围合法、类型正确
- 状态枚举合法
- 父子引用完整性（可选）
- 原始识别 orig_char / 映射 mapping 结构正确

校验失败返回可定位的错误列表（不静默）。除非 validate_only，
否则加载失败时应给出清晰错误而非运行崩溃。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import STATUSES, parse_box


# 每页必需字段
_REQUIRED_PAGE = {"page", "chars", "width", "height"}
# 每字必需字段
_REQUIRED_CHAR = {"id", "box", "char"}


class ValidationError(Exception):
    """Schema 校验失败，含错误列表。"""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def validate_page_dict(data: dict, page: str | None = None) -> list[str]:
    """校验一页的 dict（从 JSON 加载后）。返回错误列表（空 = 通过）。"""
    errors: list[str] = []
    if not isinstance(data, dict):
        errors.append(f"[{page or data}] 页面数据必须为 dict，得到 {type(data).__name__}")
        return errors

    # 必填字段
    for req in _REQUIRED_PAGE:
        if req not in data:
            errors.append(f"[{data.get('page', page or '?')}] 缺必填字段: {req}")

    # page 键与数据一致
    if page and data.get("page") not in (None, page):
        errors.append(f"[{page}] page 字段不匹配: 期望 {page}, 得到 {data.get('page')}")

    # 尺寸
    for dim in ("width", "height"):
        v = data.get(dim)
        if v is not None and (not isinstance(v, (int, float)) or v <= 0):
            errors.append(f"[{data.get('page_form', page)}] {dim} 必须为正数，得到 {v}")

    # chars 校验
    chars = data.get("chars")
    if not isinstance(chars, list):
        errors.append(f"[{data.get('page')}] chars 必须为 list，得到 {type(chars).__name__}")
    else:
        seen_ids: set[str] = set()
        for i, ch in enumerate(chars):
            cerr = _validate_char(ch, i)
            if cerr:
                errors.extend(cerr)
                continue
            cid = ch["id"]
            if cid in seen_ids:
                errors.append(f"[{data.get('page')}] 重复字框 id: {cid}")
            seen_ids.add(cid)

    return errors


def _validate_char(ch: Any, idx: int) -> list[str]:
    """校验单个字框。"""
    err: list[str] = []
    tag = f"chars[{idx}]"
    if not isinstance(ch, dict):
        err.append(f"{tag} 必须为 dict，得到 {type(ch).__name__}")
        return err

    cid = ch.get("id", "?")
    for req in _REQUIRED_CHAR:
        if req not in ch:
            err.append(f"{tag}(id={cid}) 缺字段: {req}")

    # box 校验
    if "box" in ch:
        try:
            box = parse_box(ch["box"])
            for k in ("x", "y", "w", "h"):
                v = box[k]
                if v < 0:
                    err.append(f"{tag}(id={cid}) box.{k} 不能为负: {v}")
                elif k in ("w", "h") and v == 0:
                    err.append(f"{tag}(id={cid}) box.{k} 不能为 0")
        except (ValueError, KeyError, TypeError) as e:
            err.append(f"{tag}(id={cid}) box 格式错误: {e}")

    # 状态枚举
    status = ch.get("status")
    if status is not None and status not in STATUSES:
        err.append(f"{tag}(id={cid}) 非法 status: {status!r}, 合法: {sorted(STATUSES)}")

    # rare_reason 枚举
    rr = ch.get("rare_reason")
    if rr is not None and rr not in ("not_in_common_set", "low_conf"):
        err.append(f"{tag}(id={cid}) 非法 rare_reason: {rr!r}")

    # mapping 结构
    mp = ch.get("mapping")
    if mp is not None:
        if not isinstance(mp, dict):
            err.append(f"{tag}(id={cid}) mapping 必须为 dict")
        else:
            for k in ("from", "target", "source"):
                if k not in mp:
                    err.append(f"{tag}(id={cid}) mapping 缺字段: {k}")

    return err


def validate_page_file(path: str | Path) -> list[str]:
    """校验一个 page JSON 文件。返回错误列表（空=通过）。返回空 list 而非抛异常。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
        return [f"无法读取 {path}: {e}"]
    page = Path(path).stem
    return validate_page_dict(data, page=page)


def check_json_loadability(path: str | Path) -> dict:
    """加载并校验页面 JSON。校验失败抛 ValidationError（供加载流程用）。"""
    errors = validate_page_file(path)
    if errors:
        raise ValidationError(errors)
    with open(path, encoding="utf-8") as f:
        return json.load(f)
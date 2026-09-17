"""G1 重放一致性 Validator（规格 §13.1 G1、§9 第 19 条）。

本模块是**唯一允许 import ``pipeline.corpus_compiler``** 的模块：
G1 重放按定义需执行生产编译工具，先比对 m3 配置的 ``tool``/``tool_version``
与已安装版本，再重放并逐字节比对。其余 Validator 一律独立实现，禁止 import
M3，以防「同错同过」。

**按证据级别分派（R83，第 100 条 D5）**：``offset_level`` 档重放电子文本
路线（``compile_offset_spans``）；``glyphbox_level`` 档逐字沿用原结构层重放
（``compile_structural``），行为不变。
"""

import hashlib
import re

from pipeline.corpus_compiler import M3_TOOL, M3_TOOL_VERSION
from pipeline.corpus_compiler.compiler import compile_structural
from pipeline.corpus_compiler.step_offset import M3_TEXT_TOOL, M3_TEXT_TOOL_VERSION
from pipeline.corpus_compiler.text_compiler import compile_offset_spans
from pipeline.ledger import ids

from .findings import make_finding

_ERROR = {"INTERNAL_DEMO": "error", "DEV_SEARCH": "error", "PUBLIC_RELEASE": "error"}

# source_id 的分段正则：字符集逐字取自 ``pipeline.ledger.ids``（第 102 条），
# 本模块只补捕获组，不另立形态。
_SOURCE_ID_PARTS = re.compile(r"^src_(%s)_(%s)$" % (ids.WORK, ids.EDITION))


def _subject(entity_id, revision_id=None, page=None):
    return {
        "entity_id": entity_id,
        "artifact_revision_id": revision_id,
        "page": page,
    }


def _is_offset(ctx):
    """证据级别是否为电子文本档 ``offset_level``（R83，第 100 条 D5）。"""
    return (ctx.get("spans_doc") or {}).get("evidence_level") == "offset_level"


def validate_replay(ctx):
    """核对 m3 工具版本并重放编译，与冻结 ``corpus_spans`` 逐字节比对。

    - 配置 ``tool``/``tool_version`` 与当前安装版本不符 →
      ``replay_tool_mismatch``（``code=None``，三级 ``error``）；
    - 重放所得 spans 字节 sha256 与冻结对象实得 sha256 不符 →
      ``replay_bytes_mismatch``（SRC_003，三级 ``error``）。
    """
    if _is_offset(ctx):
        return _replay_offset(ctx)

    config = ctx.get("configuration") or {}
    config_rev = ctx.get("configuration_revision_id") or (
        (ctx.get("revision_roles") or {}).get("configuration")
    )
    findings = []

    if (
        config.get("tool") != M3_TOOL
        or config.get("tool_version") != M3_TOOL_VERSION
    ):
        findings.append(
            make_finding(
                "g1_replay", "G1", "replay_tool_mismatch", None, _ERROR,
                _subject(config_rev or "configuration", config_rev),
                detail="m3 配置工具 %r@%r != 已安装 %r@%r"
                % (config.get("tool"), config.get("tool_version"), M3_TOOL, M3_TOOL_VERSION),
            )
        )
        return {
            "findings": findings,
            "checked": {"tool": config.get("tool"), "replayed": False},
        }

    recomputed = compile_structural(
        manifest=ctx.get("manifest"),
        page_docs=ctx.get("page_docs") or {},
        terminal_states=ctx.get("terminal_states") or {},
        batch_size=config.get("batch_size", 10),
    )
    spans_rev = ctx.get("corpus_spans_revision_id")
    frozen_entry = ((ctx.get("raw") or {}).get("frozen") or {}).get(spans_rev) or {}
    actual = frozen_entry.get("actual_sha256")
    recomputed_sha = hashlib.sha256(recomputed["spans_bytes"]).hexdigest()
    if recomputed_sha != actual:
        findings.append(
            make_finding(
                "g1_replay", "G1", "replay_bytes_mismatch", "SRC_003", _ERROR,
                _subject(spans_rev or "corpus_spans", spans_rev),
                detail="重放字节 %s != 冻结对象 %s" % (recomputed_sha, actual),
            )
        )

    return {
        "findings": findings,
        "checked": {
            "tool": config.get("tool"),
            "replayed": True,
            "recomputed_sha256": recomputed_sha,
        },
    }


def _replay_offset(ctx):
    """offset 档重放：核对电子文本工具版本并以 ``compile_offset_spans`` 复算。"""
    config = ctx.get("configuration") or {}
    config_rev = ctx.get("configuration_revision_id") or (
        (ctx.get("revision_roles") or {}).get("configuration")
    )
    spans_doc = ctx.get("spans_doc") or {}
    spans_rev = ctx.get("corpus_spans_revision_id")
    findings = []

    if (
        config.get("tool") != M3_TEXT_TOOL
        or config.get("tool_version") != M3_TEXT_TOOL_VERSION
    ):
        findings.append(
            make_finding(
                "g1_replay", "G1", "replay_tool_mismatch", None, _ERROR,
                _subject(config_rev or "configuration", config_rev),
                detail="m3 电子文本配置工具 %r@%r != 已安装 %r@%r"
                % (
                    config.get("tool"),
                    config.get("tool_version"),
                    M3_TEXT_TOOL,
                    M3_TEXT_TOOL_VERSION,
                ),
            )
        )
        return {
            "findings": findings,
            "checked": {"tool": config.get("tool"), "replayed": False},
        }

    source_match = _SOURCE_ID_PARTS.match(spans_doc.get("source_id") or "")
    if source_match is None:
        findings.append(
            make_finding(
                "g1_replay", "G1", "replay_bytes_mismatch", "SRC_003", _ERROR,
                _subject(spans_rev or "corpus_spans", spans_rev),
                detail="spans source_id 无法解析 work/edition: %r"
                % (spans_doc.get("source_id"),),
            )
        )
        return {
            "findings": findings,
            "checked": {"tool": config.get("tool"), "replayed": False},
        }

    work, edition = source_match.groups()
    recomputed = compile_offset_spans(
        work=work,
        edition=edition,
        edition_part_artifact_id=spans_doc.get("edition_part_artifact_id"),
        raw_text_revision_id=ctx.get("raw_text_revision_id"),
        raw_text=ctx.get("raw_text"),
        cleaned_text_revision_id=ctx.get("cleaned_text_revision_id"),
        cleaned_text=ctx.get("cleaned_text"),
        patches=ctx.get("patches") or [],
    )
    frozen_entry = ((ctx.get("raw") or {}).get("frozen") or {}).get(spans_rev) or {}
    actual = frozen_entry.get("actual_sha256")
    recomputed_sha = hashlib.sha256(recomputed["spans_bytes"]).hexdigest()
    if recomputed_sha != actual:
        findings.append(
            make_finding(
                "g1_replay", "G1", "replay_bytes_mismatch", "SRC_003", _ERROR,
                _subject(spans_rev or "corpus_spans", spans_rev),
                detail="重放字节 %s != 冻结对象 %s" % (recomputed_sha, actual),
            )
        )

    return {
        "findings": findings,
        "checked": {
            "tool": config.get("tool"),
            "replayed": True,
            "recomputed_sha256": recomputed_sha,
        },
    }

"""M3 纯函数结构编译器（规格 §11、§11.1）。

本模块只做确定性纯计算：不读文件、不访问 Ledger、不取系统时间、不用
随机数。所有输入均为调用方已解析好的 dict（M1 manifest、M2 OCR 页
JSON、异常页终态映射），输出 StructuralSpan 列表、``spans_doc`` 及其
金标序列化字节（规则见 ``serialize.dump_yaml``）。
"""

import hashlib
import re

from pipeline.ledger import ids
from pipeline.ledger.errors import InvalidIdentifier, SchemaViolation

from .errors import CompileRefused
from .serialize import dump_yaml

# §8.1：来源标识 src_<work>_ed<NN>
_SOURCE_ID_RE = re.compile(r"^src_([a-z][a-z0-9]*)_ed([0-9]{2})$")
# 页名 page_NNN 或 page_NNNN
_PAGE_NUMBER_RE = re.compile(r"^page_([0-9]{3,4})$")

# §10.1 异常页终态枚举 + 未标注（None，等同 manually_transcribed 一样要求有文字）
_KNOWN_TERMINAL_STATES = frozenset({None, "manually_transcribed", "known_unrecognizable"})


def parse_source_id(source_id):
    """解析 ``source_id`` 为 ``(work, edition)``。

    不匹配 §8.1 格式 ``src_<work>_ed<NN>`` 时抛 ``InvalidIdentifier(code="ID_001")``。
    """
    match = _SOURCE_ID_RE.match(source_id) if isinstance(source_id, str) else None
    if match is None:
        raise InvalidIdentifier(
            "source_id 格式非法（应形如 src_<work>_ed<NN>）: %r" % (source_id,),
            code="ID_001",
        )
    return match.group(1), match.group(2)


def page_number(page):
    """解析页名为整数页号；不匹配 ``page_NNN``/``page_NNNN`` 则 ``SchemaViolation(SCH_002)``。"""
    match = _PAGE_NUMBER_RE.match(page) if isinstance(page, str) else None
    if match is None:
        raise SchemaViolation(
            "页名格式非法（应形如 page_NNN 或 page_NNNN）: %r" % (page,),
            code="SCH_002",
        )
    return int(match.group(1))


def page_block(page_doc):
    """页块 = 该页 OCR 各行文本以 ``"\\n"`` 连接。"""
    return "\n".join(line["text"] for line in page_doc["lines"])


def compile_structural(*, manifest, page_docs, terminal_states, batch_size=10):
    """把 M1 manifest + M2 OCR 页 + 终态，确定性编译为 M3 StructuralSpan 集合。

    参数：
        manifest：M1 ``manifest.yaml`` 解析后的 dict。
        page_docs：``{page: OCR 页 JSON dict}``。
        terminal_states：``{page: 终态字符串}``；页序中未出现的页视为
            ``None``（要求同 ``manually_transcribed``：必须有文字行）。
        batch_size：每批最多行数，必须 ``>= 1``，否则 ``SchemaViolation(SCH_002)``。

    返回 dict，键：``spans``、``spans_doc``、``spans_bytes``、
    ``spans_sha256``、``page_blocks``、``coverage``、``excluded_pages``、
    ``batches``。
    """
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
        raise SchemaViolation(
            "batch_size 必须为 >= 1 的整数: %r" % (batch_size,), code="SCH_002"
        )

    work, edition = parse_source_id(manifest["source_id"])

    # ---- R1：页序与 page_docs 一一对应（页序缺页 / page_docs 多页均拒绝） ----
    pages = manifest["edition_part"]["pages"]
    page_set = set(pages)
    for page in pages:
        if page not in page_docs:
            raise CompileRefused(
                "页序中的页缺少对应 OCR 页文档: %s" % page, code="REF_001"
            )
    for page in page_docs:
        if page not in page_set:
            raise CompileRefused(
                "page_docs 出现页序外的页: %s" % page, code="SCH_002"
            )

    asset_sha = {item["page"]: item["sha256"] for item in manifest["source_assets"]}

    # ---- R2：逐页终态，分流为 excluded_pages（排除）/ covered（覆盖） ----
    excluded_pages = {}
    covered_pages = []
    for page in pages:
        state = terminal_states.get(page)
        lines = page_docs[page]["lines"]
        if state == "deferred":
            raise CompileRefused(
                "页 %s 终态为 deferred，依据 §10.1 严格阻断，不得进入 M3" % page
            )
        if state not in _KNOWN_TERMINAL_STATES:
            raise SchemaViolation(
                "页 %s 终态非法枚举: %r" % (page, state), code="SCH_002"
            )
        if state == "known_unrecognizable":
            if lines:
                raise CompileRefused(
                    "页 %s 终态为 known_unrecognizable 却有文字行，禁止裸标" % page
                )
            excluded_pages[page] = state
            continue
        if not lines:
            raise CompileRefused(
                "页 %s 无终态覆盖且 0 行，疑似漏编（既非排除页也无内容）" % page
            )
        covered_pages.append(page)

    # ---- R3/R4/R5/R6：覆盖页逐行切段、批次分配、字框锚点 ----
    spans = []
    page_blocks = {}
    coverage = {}
    batches = []
    batch_counter = 0  # 已分配批次总数；批号从 1 全局递增，按页序逐页累加

    for page in covered_pages:
        doc = page_docs[page]
        lines = doc["lines"]
        block = page_block(doc)
        page_blocks[page] = block
        coverage[page] = 1.0

        image_sha = asset_sha.get(page)
        if image_sha is None:
            raise CompileRefused(
                "页 %s 缺少 source_assets 图像哈希" % page, code="REF_001"
            )

        pnum = page_number(page)
        pos = 0
        groups_used = 0
        for idx, line in enumerate(lines):
            text = line["text"]
            start = pos
            end = start + len(text)
            pos = end + (1 if idx < len(lines) - 1 else 0)

            if idx + 1 > 99:
                raise InvalidIdentifier(
                    "页 %s 第 %d 行超出两位行序上限（最多 99）" % (page, idx + 1),
                    code="ID_001",
                )

            group = idx // batch_size
            batch_number = batch_counter + group + 1
            batch_id = "%s_b%03d" % (work, batch_number)
            if batch_id not in batches:
                batches.append(batch_id)
            groups_used = group + 1

            span_id = ids.validate(
                "source_span_id",
                "ss_%s_ed%s_p%04d_s%02d" % (work, edition, pnum, idx + 1),
            )

            chars = [
                {
                    "char_index": ci,
                    "glyph_id": ch["id"],
                    "char": ch["char"],
                    "box": dict(ch["box"]),
                }
                for ci, ch in enumerate(doc["chars"])
                if ch["parent"] == line["id"]
            ]
            source_anchor = {
                "page": page,
                "image_sha256": image_sha,
                "line_id": line["id"],
                "bbox": dict(line["box"]),
                "chars": chars,
            }
            spans.append(
                {
                    "span_id": span_id,
                    "batch_id": batch_id,
                    "page": page,
                    "line_index": idx,
                    "start_offset": start,
                    "end_offset": end,
                    "text": text,
                    "source_anchor": source_anchor,
                }
            )
        assert pos == len(block), "页 %s offset 未覆盖整块" % page
        batch_counter += groups_used

    spans_doc = {
        "work": manifest["work_title"],
        "source_id": manifest["source_id"],
        "edition_part_artifact_id": manifest["edition_part"]["artifact_id"],
        "evidence_level": "glyphbox_level",
        "content_status": "machine_extracted",
        "span_count": len(spans),
        "batch_count": len(batches),
        "spans": spans,
    }
    spans_bytes = dump_yaml(spans_doc)

    return {
        "spans": spans,
        "spans_doc": spans_doc,
        "spans_bytes": spans_bytes,
        "spans_sha256": hashlib.sha256(spans_bytes).hexdigest(),
        "page_blocks": page_blocks,
        "coverage": coverage,
        "excluded_pages": excluded_pages,
        "batches": batches,
    }

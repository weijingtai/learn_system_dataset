"""M2 原始文本冻结模块。

提供 freeze_raw_text 函数，对输入的原始字节统一 UTF-8 编码并记录原始编码元数据。
"""


def freeze_raw_text(content: bytes, encoding: str = "utf-8") -> dict:
    """冻结原始文本内容，返回包含标准化字节与元数据的字典。

    参数：
        content：原始文件字节。
        encoding：原始编码声明或推导编码。

    返回：
        {"content": bytes, "encoding_original": str, "encoding_normalized": "utf-8", "has_bom": bool, "size": int}
    """
    has_bom = False
    if content.startswith(b"\xef\xbb\xbf"):
        has_bom = True
        text = content[3:].decode("utf-8")
        norm_bytes = text.encode("utf-8")
    else:
        try:
            text = content.decode(encoding)
            norm_bytes = text.encode("utf-8")
        except UnicodeDecodeError:
            # 回退尝试常见编码
            text = content.decode("utf-8", errors="replace")
            norm_bytes = text.encode("utf-8")

    return {
        "content": norm_bytes,
        "encoding_original": encoding,
        "encoding_normalized": "utf-8",
        "has_bom": has_bom,
        "size": len(norm_bytes),
    }

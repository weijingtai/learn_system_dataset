"""M2 纯函数：确定性修补集与可逆映射（规格 §4.3、§6、G7-RULINGS §81）。

提供 Patch 数据结构、build_patches 与 apply_patches。
"""

from dataclasses import dataclass

from .cleaner import Finding, patch_replacement


@dataclass
class Patch:
    """确定性修补项（规格 §4.3）。"""

    patch_id: str
    raw_start: int
    raw_end: int
    cleaned_start: int
    cleaned_end: int
    action: str
    basis: str
    replacement: str = ""


def build_patches(raw_text: str, cleaned_text: str, findings: list[Finding]) -> list[Patch]:
    """对比原始文本与清洗后文本，生成确定性 patch 列表，并关联到各 Finding。

    参数：
        raw_text：原始文本。
        cleaned_text：清洗后的文本。
        findings：发现项列表（会就地更新其 patch_id）。

    返回：
        list[Patch]，patch_id 从 "patch_001" 起顺序编号。
    """
    patches: list[Patch] = []
    # 筛选出 action == "patched" 的发现
    patched_findings = [f for f in findings if f.action == "patched"]
    patched_findings.sort(key=lambda f: f.raw_start)

    # 依次计算在 cleaned_text 中的偏移
    cleaned_offset = 0
    raw_offset = 0

    for idx, f in enumerate(patched_findings, start=1):
        patch_id = f"patch_{idx:03d}"
        f.patch_id = patch_id

        # 在当前 patch 之前，未修改的文本长度
        prefix_len = f.raw_start - raw_offset
        cleaned_start = cleaned_offset + prefix_len

        # 推导 replacement 内容（与 clean_text 共用同一处定义，第 85/96 条）
        replacement = patch_replacement(f)

        cleaned_end = cleaned_start + len(replacement)

        patch = Patch(
            patch_id=patch_id,
            raw_start=f.raw_start,
            raw_end=f.raw_end,
            cleaned_start=cleaned_start,
            cleaned_end=cleaned_end,
            action=f.action,
            basis=f.basis,
            replacement=replacement,
        )
        patches.append(patch)

        raw_offset = f.raw_end
        cleaned_offset = cleaned_end

    return patches


def apply_patches(raw_text: str, patches: list[Patch]) -> str:
    """将 patches 应用到原始文本上，恢复为清洗后文本（验证双向可逆性）。

    参数：
        raw_text：原始文本。
        patches：修补项列表。

    返回：
        清洗后文本字符串。
    """
    sorted_patches = sorted(patches, key=lambda p: p.raw_start)
    chars = []
    idx = 0
    for p in sorted_patches:
        if p.raw_start > idx:
            chars.append(raw_text[idx : p.raw_start])
        chars.append(p.replacement)
        idx = p.raw_end

    if idx < len(raw_text):
        chars.append(raw_text[idx:])

    return "".join(chars)

"""content-addressed Object Store（规格 §17）。

大文件和中间产物按 SHA-256 存放；相同内容物理去重，逻辑引用由 Revision 记录。
写入先落 ``objects/tmp/<uuid>``，再用 ``os.replace`` 原子归位，避免半成品对象。
"""

import hashlib
import os
import uuid
from pathlib import Path

from .errors import MissingReference


class ObjectStore:
    """基于 SHA-256 内容寻址的本地对象存储。

    :param root: Ledger 根目录；对象实际位于 ``root/objects/<前2位>/<sha256>``。
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.objects_dir = self.root / "objects"
        self.tmp_dir = self.objects_dir / "tmp"

    def path_for(self, sha256: str) -> Path:
        """返回对象应落盘的路径（不保证已存在）。"""
        return self.objects_dir / sha256[:2] / sha256

    def exists(self, sha256) -> bool:
        """对象是否已存在。"""
        return self.path_for(sha256).is_file()

    def put(self, data: bytes) -> tuple[str, int]:
        """写入 ``data``，返回 ``(sha256, size)``；内容相同则去重、不重写。"""
        digest = hashlib.sha256(data).hexdigest()
        size = len(data)
        target = self.path_for(digest)
        if target.is_file():
            return digest, size
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.tmp_dir / uuid.uuid4().hex
        with open(tmp_path, "wb") as handle:
            handle.write(data)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_path, target)
        return digest, size

    def get(self, sha256: str) -> bytes:
        """读取对象字节；不存在抛 ``MissingReference``（``REF_001``）。"""
        path = self.path_for(sha256)
        if not path.is_file():
            raise MissingReference("对象不存在: %s" % sha256, code="REF_001")
        return path.read_bytes()

    def verify(self, sha256) -> bool:
        """重算哈希并比对；不一致或对象缺失返回 ``False``。"""
        path = self.path_for(sha256)
        if not path.is_file():
            return False
        return hashlib.sha256(path.read_bytes()).hexdigest() == sha256

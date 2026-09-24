"""写入者锁（规格 §17）：单机单写入者，独占 ``writer.lock``。

POSIX 用 ``fcntl.flock``；Windows 没有 fcntl，改用 ``msvcrt.locking`` 锁住文件首字节，语义相同。

进程级锁阻止第二个 Ledger 写入者启动；只读查询不取锁（见 ``store.MetadataStore``
的 ``open_readonly``）。
"""

import os

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt
from pathlib import Path

from .errors import WriterLocked


def _lock(fd):
    """非阻塞独占锁；取不到抛 ``OSError``。"""
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    else:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)


def _unlock(fd):
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_UN)
    else:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


class WriterLock:
    """Ledger 写入者独占锁。

    :param root: Ledger 根目录；锁文件为 ``root/writer.lock``。
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.path = self.root / "writer.lock"
        self._fd = None

    def acquire(self):
        """取独占锁；取不到抛 ``WriterLocked``。同一实例重复调用幂等。"""
        if self._fd is not None:
            return self
        self.root.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            _lock(fd)
        except OSError:
            os.close(fd)
            raise WriterLocked("Ledger 写入者锁已被占用: %s" % self.path)
        self._fd = fd
        return self

    def release(self):
        """释放锁；未持锁时不做任何事。"""
        if self._fd is not None:
            _unlock(self._fd)
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return False

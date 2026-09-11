"""本地 Ledger 进程（规格 §17）：Unix domain socket + 换行分隔 JSON。

用法::

    python -m pipeline.ledger.ledgerd --root <dir> [--socket <path>]

- 启动即 ``LedgerService(root)``（内部取 ``WriterLock``）；取不到写锁时打印
  ``LEDGER_WRITER_LOCKED <root>`` 并 ``exit 3``，不启动监听；
- 收到 ``SIGTERM`` / ``SIGINT``：关闭 socket、释放锁、``exit 0``，并删除 socket 文件；
- 每个请求向 stderr 写一行日志（时间、op、ok/err）；
- 服务端串行处理请求（单线程接受 + 顺序执行）。

请求 / 响应协议见 ``pipeline.ledger.client`` 模块 docstring。
"""

import argparse
import base64
import datetime
import json
import signal
import socket
import sys
from pathlib import Path

from .errors import LedgerError, WriterLocked
from .service import LedgerService

# 只读 op：直接落到进程持有的 Object Store（不经过 LedgerReader 的新连接）
DIRECT_OPS = {"read_object": lambda service: service.objects.get}

# 不接受远程调用的进程内方法
RESERVED_OPS = {"close", "__enter__", "__exit__"}

# 等待连接的超时（秒）：让信号处理器能被及时观察到
ACCEPT_TIMEOUT = 0.2

RECV_SIZE = 65536


def default_socket_path(root):
    """默认 socket 路径：``<root>/ledger.sock``。"""
    return Path(root) / "ledger.sock"


def _decode_args(args):
    """把 ``"<name>_b64"`` 参数还原为 ``<name>`` 的 bytes。"""
    decoded = {}
    for key, value in (args or {}).items():
        if key.endswith("_b64"):
            decoded[key[:-4]] = base64.b64decode(value)
        else:
            decoded[key] = value
    return decoded


def _encode_result(value):
    """bytes 结果用 ``data_b64`` 编码；tuple 转 list（JSON 无 tuple）。"""
    if isinstance(value, (bytes, bytearray)):
        return {"data_b64": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, tuple):
        return list(value)
    return value


def resolve_operation(service, op):
    """把 op 名解析为可调用对象；未知 op 返回 ``None``。"""
    if not isinstance(op, str) or not op or op.startswith("_") or op in RESERVED_OPS:
        return None
    direct = DIRECT_OPS.get(op)
    if direct is not None:
        return direct(service)
    func = getattr(service, op, None)
    return func if callable(func) else None


def handle_request(service, request):
    """处理一条 JSON 请求，返回一条 JSON 响应（不抛异常）。"""
    op = request.get("op") if isinstance(request, dict) else None
    func = resolve_operation(service, op)
    if func is None:
        return {
            "ok": False,
            "error": {
                "type": "UnknownOperation",
                "code": None,
                "message": "未知操作: %r" % (op,),
            },
        }
    try:
        result = func(**_decode_args(request.get("args")))
    except LedgerError as exc:
        return {
            "ok": False,
            "error": {
                "type": type(exc).__name__,
                "code": exc.code,
                "message": str(exc),
            },
        }
    except (TypeError, ValueError) as exc:
        return {
            "ok": False,
            "error": {"type": type(exc).__name__, "code": None, "message": str(exc)},
        }
    return {"ok": True, "result": _encode_result(result)}


def _log(op, response):
    """每个请求向 stderr 写一行日志：时间、op、ok/err。"""
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    if response.get("ok"):
        status = "ok"
    else:
        status = "err=%s" % (response.get("error") or {}).get("type")
    sys.stderr.write("%s %s %s\n" % (stamp, op, status))
    sys.stderr.flush()


def serve_connection(service, conn):
    """顺序服务一条连接上的全部请求，直到对端关闭。"""
    buffer = b""
    while True:
        chunk = conn.recv(RECV_SIZE)
        if not chunk:
            return
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if not line.strip():
                continue
            op = None
            try:
                request = json.loads(line.decode("utf-8"))
                op = request.get("op")
            except (UnicodeDecodeError, ValueError) as exc:
                response = {
                    "ok": False,
                    "error": {
                        "type": "ValueError",
                        "code": None,
                        "message": "请求不是合法 JSON: %s" % exc,
                    },
                }
            else:
                response = handle_request(service, request)
            _log(op, response)
            conn.sendall(
                json.dumps(response, ensure_ascii=False).encode("utf-8") + b"\n"
            )


def run(root, socket_path):
    """启动单写入者进程；返回进程退出码。"""
    root = Path(root)
    socket_path = Path(socket_path)
    try:
        service = LedgerService(root)
    except WriterLocked:
        print("LEDGER_WRITER_LOCKED %s" % root)
        return 3

    stop = {"flag": False}

    def _on_signal(signum, frame):
        stop["flag"] = True

    previous = {}
    for signum in (signal.SIGTERM, signal.SIGINT):
        previous[signum] = signal.signal(signum, _on_signal)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        socket_path.parent.mkdir(parents=True, exist_ok=True)
        if socket_path.exists():
            socket_path.unlink()
        server.bind(str(socket_path))
        server.listen(16)
        server.settimeout(ACCEPT_TIMEOUT)
        while not stop["flag"]:
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                serve_connection(service, conn)
    finally:
        try:
            server.close()
        except OSError:
            pass
        if socket_path.exists():
            try:
                socket_path.unlink()
            except OSError:
                pass
        service.close()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    return 0


def main(argv=None):
    """``python -m pipeline.ledger.ledgerd`` 入口。"""
    parser = argparse.ArgumentParser(
        prog="pipeline.ledger.ledgerd",
        description="本地 Artifact Ledger 单写入者进程（规格 §17）",
    )
    parser.add_argument("--root", required=True, help="Ledger 根目录")
    parser.add_argument(
        "--socket", default=None, help="Unix domain socket 路径（默认 <root>/ledger.sock）"
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    socket_path = Path(args.socket) if args.socket else default_socket_path(root)
    return run(root, socket_path)


if __name__ == "__main__":
    sys.exit(main())

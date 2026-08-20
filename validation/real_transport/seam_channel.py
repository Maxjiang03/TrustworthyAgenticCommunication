"""The seam channel: the runner's harness-held callables, served across a process.

Post-seal validation apparatus (DEVIATIONS D-018). Outside `src/` and `analysis/`.

`src/sut/protocol/mcp_tools.py` states the sealed design's own principle: "The
effector is injected, harness-held. The SUT defines the seam and never sees the
ledger writer behind it." `install_boundary` follows the same shape -- it takes
`decide`, `correlation_provider` and `emit` as injected callables and owns none
of them.

This module carries exactly those three across a process boundary, so the sealed
MCP server and the sealed mediation boundary can run in a CHILD process while
the arm, the clock and the runner's own recording closures stay in the PARENT,
unmodified and sealed. Nothing sealed is re-implemented here; the callables are
the runner's own and they execute in the parent. Only the call travels.

**Why a second channel at all.** The child's stdin/stdout are the real MCP
transport and must carry nothing but MCP frames. The seams therefore need their
own path, and this is it: a loopback TCP socket, line-delimited JSON, one
connection, one request in flight at a time (the supervisor thread blocks on the
tool call, so the boundary is never re-entered concurrently).

**A seam failure is never allowed to look like a denial.** If the channel breaks,
`decide` cannot answer, the sealed boundary raises, the tool call errors, and the
cell would record as BLOCKED -- a harness fault wearing the costume of a result.
So every failure is counted on the parent side and the sweep marks any cell that
saw one as a harness error rather than scoring it. Fail loudly, never quietly
into a `B`.
"""

import json
import socket
import threading
from collections.abc import Callable, Mapping
from typing import Any

from src.harness.schema import MediationEvent


class SeamChannelError(RuntimeError):
    """A seam call could not be completed. Never a decision; always a fault."""


def _send(sock: socket.socket, payload: Mapping[str, Any]) -> None:
    sock.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))


class _LineReader:
    """Minimal buffered line reader over a blocking socket."""

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._buf = b""

    def readline(self) -> str | None:
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                return None
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\n")
        return line.decode("utf-8")


class SeamServer:
    """Parent side. Serves the runner's own sealed closures to the child.

    The closures are re-bound per cell by `bind`, which the rebound
    `install_boundary` calls with whatever `run_scenario` passed it. Cells run
    strictly in sequence, so there is no race between a rebind and a call.
    """

    def __init__(self) -> None:
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(8)
        self.port: int = self._listener.getsockname()[1]

        self._decide: Callable[[str, Mapping[str, Any]], tuple[bool, str]] | None = None
        self._correlation: Callable[[], str] | None = None
        self._emit: Callable[[MediationEvent], None] | None = None

        # Faults, counted and NEVER converted into a verdict.
        self.faults: list[str] = []
        self._cell_faults_at_start = 0

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    # -- lifecycle -----------------------------------------------------------
    def bind(
        self,
        *,
        decide: Callable[[str, Mapping[str, Any]], tuple[bool, str]],
        correlation_provider: Callable[[], str],
        emit: Callable[[MediationEvent], None],
    ) -> None:
        """Bind this cell's seams. Called from the rebound `install_boundary`."""
        self._decide = decide
        self._correlation = correlation_provider
        self._emit = emit
        self._cell_faults_at_start = len(self.faults)

    def faults_this_cell(self) -> list[str]:
        return self.faults[self._cell_faults_at_start :]

    def close(self) -> None:
        self._stop.set()
        try:
            self._listener.close()
        except OSError:
            pass

    # -- serving -------------------------------------------------------------
    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._listener.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        reader = _LineReader(conn)
        try:
            while True:
                line = reader.readline()
                if line is None:
                    return
                try:
                    request = json.loads(line)
                    _send(conn, self._handle(request))
                except Exception as exc:  # noqa: BLE001 -- reported, never swallowed
                    self.faults.append(f"{type(exc).__name__}: {exc}")
                    try:
                        _send(conn, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})
                    except OSError:
                        return
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _handle(self, request: Mapping[str, Any]) -> dict[str, Any]:
        method = request.get("m")
        if method == "decide":
            if self._decide is None:
                raise SeamChannelError("decide called before any cell bound its seams")
            admitted, reason = self._decide(str(request["tool"]), dict(request["arguments"]))
            return {"ok": True, "admitted": bool(admitted), "reason": str(reason)}
        if method == "correlation":
            if self._correlation is None:
                raise SeamChannelError("correlation called before any cell bound its seams")
            return {"ok": True, "value": str(self._correlation())}
        if method == "emit":
            if self._emit is None:
                raise SeamChannelError("emit called before any cell bound its seams")
            # Reconstructed with the SEALED model, from fields the SEALED
            # boundary computed in the child. Only the bytes travelled.
            self._emit(MediationEvent(**dict(request["event"])))
            return {"ok": True}
        raise SeamChannelError(f"unknown seam method {method!r}")


class SeamClient:
    """Child side. Thin stubs the sealed `install_boundary` accepts verbatim."""

    def __init__(self, port: int) -> None:
        self._sock = socket.create_connection(("127.0.0.1", port), timeout=60)
        self._reader = _LineReader(self._sock)
        self._lock = threading.Lock()

    def _call(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            _send(self._sock, payload)
            line = self._reader.readline()
        if line is None:
            raise SeamChannelError("the seam channel closed mid-call")
        reply = json.loads(line)
        if not reply.get("ok"):
            raise SeamChannelError(str(reply.get("error", "unspecified seam failure")))
        return reply

    # The three callables sealed `install_boundary` takes, with its signatures.
    def decide(self, tool: str, arguments: Mapping[str, Any]) -> tuple[bool, str]:
        reply = self._call({"m": "decide", "tool": tool, "arguments": dict(arguments)})
        return bool(reply["admitted"]), str(reply["reason"])

    def correlation_provider(self) -> str:
        return str(self._call({"m": "correlation"})["value"])

    def emit(self, event: Any) -> None:
        fields = {
            "correlation_id": event.correlation_id,
            "admitted": event.admitted,
            "reason_code": event.reason_code,
            "boundary_ts_ns": event.boundary_ts_ns,
        }
        self._call({"m": "emit", "event": fields})

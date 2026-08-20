"""The harness's own five-tool MCP server, run as a CHILD PROCESS over stdio.

Post-seal validation apparatus (DEVIATIONS D-017). Outside `src/` and
`analysis/`; imports the sealed server builder read-only and unmodified.

This is the whole server side of the real-transport validation: the same
`build_server` the sealed campaign uses, the same frozen five tools and the
same `Ω` mapping -- but served over a REAL stdio transport to a client in
another operating-system process, instead of over the in-memory object
streams `create_connected_server_and_client_session` sets up.

The effector records intents to stdout-adjacent state? NO -- stdout is the
transport here and must carry nothing but MCP frames. Effects are appended to
the file named by AASC_VALIDATION_EFFECTS, one JSON object per line, so the
parent can read what the tools actually did without touching the protocol
stream. The tools remain the sealed sandboxed stubs: they record an intent and
return a string, because a tool performing a real side effect is a
pre-registered forbidden action (D-017 clause 4).
"""

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.sut.protocol.mcp_tools import build_server  # noqa: E402

EFFECTS_PATH = os.environ.get("AASC_VALIDATION_EFFECTS")


def effector(**fields):
    """Append one effect record. Never writes to stdout: that is the transport."""
    if not EFFECTS_PATH:
        return
    with open(EFFECTS_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(fields, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    server = build_server(effector)
    # stdio: the real transport. stdout carries MCP frames and nothing else.
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

"""Child process: the sealed MCP server AND the sealed mediation boundary.

Post-seal validation apparatus (DEVIATIONS D-018). Outside `src/` and
`analysis/`; imports the sealed builders read-only and unmodified.

This is the server half of the full real-transport sweep, and it differs from
`mcp_server_child.py` (D-017 run 1, left untouched so that run stays
reproducible) in the one way that matters: **the mediation boundary lives
here**, in the child, wrapping the sealed server's `Tool.fn` exactly as
`src/harness/runner.py:770` does in the campaign.

That placement is the point. In run 1 the monitor had to move client-side --
`arm.decide` called before `call_tool` -- because a child-process server has no
`Tool.fn` the parent can reach, and that relocation was the run's one disclosed
apparatus difference. Here the sealed `install_boundary` runs in the child, so
`decide` is called AFTER the real transport has delivered and the server has
parsed, on wire-parsed arguments. The arguments the boundary judges are the
arguments that crossed the pipe.

The three callables `install_boundary` takes are the PARENT's -- the runner's
own sealed closures -- reached over `seam_channel`. Nothing sealed is
re-implemented on either side.

stdout is the MCP transport and carries nothing else; the local effector
appends to the file named by AASC_VALIDATION_EFFECTS, which records what this
process was actually asked to do. The tools remain the sealed sandboxed stubs:
a tool performing a real side effect is a pre-registered forbidden action
(D-017 clause 4, carried forward by D-018).
"""

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.harness.mediation.boundary import install_boundary  # noqa: E402
from src.sut.protocol.mcp_tools import build_server  # noqa: E402
from validation.real_transport.seam_channel import SeamClient  # noqa: E402

EFFECTS_PATH = os.environ.get("AASC_VALIDATION_EFFECTS")
SEAM_PORT = os.environ.get("AASC_SEAM_PORT")


def effector(**fields):
    """Append one effect record. Never writes to stdout: that is the transport."""
    if not EFFECTS_PATH:
        return
    with open(EFFECTS_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(fields, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    if not SEAM_PORT:
        raise SystemExit("AASC_SEAM_PORT is required: the boundary's seams live in the parent")
    seams = SeamClient(int(SEAM_PORT))

    server = build_server(effector)
    # The SEALED boundary, on the SEALED server, in this process -- wrapping
    # Tool.fn as the campaign does, with the PARENT's closures behind it.
    install_boundary(
        server,
        decide=seams.decide,
        correlation_provider=seams.correlation_provider,
        emit=seams.emit,
    )
    # stdio: the real transport. stdout carries MCP frames and nothing else.
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

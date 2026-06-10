"""Python entry point for the bundled DreamSeed Code layer."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DREAMSEED_LAYER = PROJECT_ROOT / "dreamseed-layer"
DREAMSEED_AGENT = DREAMSEED_LAYER / "bin" / "dreamseed-agent.js"


def main(argv: list[str] | None = None) -> int:
    """Run the source-first DreamSeed Code CLI through Node.js."""

    args = list(sys.argv[1:] if argv is None else argv)
    node = shutil.which("node")
    if not node:
        print("DreamSeed requires Node.js 18+ on PATH.", file=sys.stderr)
        return 1
    if not DREAMSEED_AGENT.exists():
        print(f"DreamSeed layer is missing: {DREAMSEED_AGENT}", file=sys.stderr)
        return 1
    return subprocess.call([node, str(DREAMSEED_AGENT), *args], cwd=str(DREAMSEED_LAYER))


if __name__ == "__main__":
    raise SystemExit(main())

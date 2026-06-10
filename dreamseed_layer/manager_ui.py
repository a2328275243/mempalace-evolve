"""Python entry point for the DreamSeed model manager."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DREAMSEED_LAYER = PROJECT_ROOT / "dreamseed-layer"
MANAGER_SCRIPT = DREAMSEED_LAYER / "scripts" / "provider_manager.mjs"


def main(argv: list[str] | None = None) -> int:
    """Open the DreamSeed provider manager."""

    args = list(sys.argv[1:] if argv is None else argv)
    node = shutil.which("node")
    if not node:
        print("DreamSeed Manager requires Node.js 18+ on PATH.", file=sys.stderr)
        return 1
    if not MANAGER_SCRIPT.exists():
        print(f"DreamSeed manager script is missing: {MANAGER_SCRIPT}", file=sys.stderr)
        return 1
    return subprocess.call([node, str(MANAGER_SCRIPT), *args], cwd=str(DREAMSEED_LAYER))


if __name__ == "__main__":
    raise SystemExit(main())

"""Standalone Stop hook script for Claude Code.

Copy this file to your project or reference it in .claude/settings.json:

{
  "hooks": {
    "Stop": [{
      "type": "command",
      "command": "python /path/to/stop_hook.py"
    }]
  }
}

Customize PALACE_PATH and WING below for your setup.
"""

import json
import sys
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────
PALACE_PATH = str(Path.home() / ".mempalace" / "palace")
WING = "global"  # Change to your project name
# ─────────────────────────────────────────────────────────────────

def main():
    from mempalace_evolve.hooks.claude_code import run_stop_hook

    # Accept transcript path as argument or read from stdin
    source = sys.argv[1] if len(sys.argv) > 1 else None
    result = run_stop_hook(
        source=source,
        palace_path=PALACE_PATH,
        wing=WING,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

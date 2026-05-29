# Claude Code Hook Integration

Auto-digest your coding sessions into long-term memory — zero manual effort.

## How It Works

```
Session ends → Stop hook fires → transcript is parsed → 
knowledge extracted → memories stored → KG updated
```

## Quick Setup

### 1. Install

```bash
pip install mempalace-evolve
```

### 2. Configure Claude Code hooks

Add to your `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "python -m mempalace_evolve.hooks.claude_code \"$TRANSCRIPT_PATH\"",
        "timeout": 30000
      }
    ]
  }
}
```

### 3. (Optional) Set environment variables

```bash
# Custom palace location (default: ~/.mempalace/palace)
export MEMPALACE_PATH="/path/to/your/palace"

# Wing name for this project (default: "global")
export MEMPALACE_WING="my_project"
```

## What Gets Extracted

The hook automatically identifies and stores:

| Type | Examples |
|------|----------|
| **Decisions** | "We decided to use PostgreSQL" |
| **Error patterns** | "Fixed CORS by adding middleware" |
| **Architecture** | "API uses hexagonal architecture" |
| **Config** | "Redis timeout set to 30s" |

## Per-Project Wing

To store memories per-project, set `MEMPALACE_WING` in your project's `.claude/settings.json`:

```json
{
  "env": {
    "MEMPALACE_WING": "my_project_name"
  },
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "python -m mempalace_evolve.hooks.claude_code"
      }
    ]
  }
}
```

## Verify It Works

After a coding session, check what was captured:

```bash
mempalace export --wing my_project --format markdown
```

Or in Python:

```python
from mempalace_evolve import MemPalace
palace = MemPalace("~/.mempalace/palace", wing="my_project")
print(palace.stats())
```

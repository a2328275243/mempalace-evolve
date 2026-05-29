# Cursor MCP Integration

Use MemPalace as an MCP server in Cursor for persistent memory across sessions.

## Quick Setup

### 1. Install

```bash
pip install mempalace-evolve[mcp]
```

### 2. Run the setup wizard

```bash
mempalace setup
```

The wizard auto-detects Cursor and writes the MCP config for you.

### 3. Manual setup (if wizard doesn't detect Cursor)

Add to `~/.cursor/mcp.json` (or your project's `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "python",
      "args": ["-m", "mempalace_evolve.adapters.mcp_server"],
      "env": {
        "MEMPALACE_PATH": "~/.mempalace/palace",
        "MEMPALACE_WING": "my_project"
      }
    }
  }
}
```

### 4. Restart Cursor

After config change, restart Cursor. You'll see `mempalace` in the MCP tools list.

## Available MCP Tools

Once connected, your AI assistant can use:

| Tool | Description |
|------|-------------|
| `mempalace_remember` | Store a memory (content + room) |
| `mempalace_recall` | Semantic search for relevant memories |
| `mempalace_forget` | Delete a memory by ID |
| `mempalace_add_fact` | Add a knowledge graph triple |
| `mempalace_query_entity` | Query entity relationships |
| `mempalace_context_for` | Get formatted context for a topic |

## Usage in Cursor

Once configured, just ask naturally:

- "Remember that we chose PostgreSQL for the database"
- "What do you know about our auth system?"
- "What errors have we seen before?"

The AI will automatically use the MCP tools to store and retrieve memories.

## Per-Project Memory

For project-specific memory, create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "python",
      "args": ["-m", "mempalace_evolve.adapters.mcp_server"],
      "env": {
        "MEMPALACE_WING": "my_project_name"
      }
    }
  }
}
```

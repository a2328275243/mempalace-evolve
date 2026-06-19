#!/usr/bin/env python3
"""Import one existing CC Switch provider into a DreamSeed local provider file.

This is a migration helper only. DreamSeed runtime does not depend on CC Switch.
The output file is private because it can contain an API token.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or "provider"


def load_provider(db_path: Path, provider_name: str, app_type: str) -> tuple[str, dict, str | None]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT p.name, p.settings_config, pe.url
            FROM providers AS p
            LEFT JOIN provider_endpoints AS pe
              ON pe.provider_id = p.id
              AND pe.app_type = p.app_type
            WHERE p.app_type = ?
              AND (p.name = ? OR p.id = ?)
            ORDER BY pe.id
            LIMIT 1
            """,
            (app_type, provider_name, provider_name),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise SystemExit(f"Provider not found: {provider_name!r} ({app_type})")

    data = json.loads(row["settings_config"] or "{}")
    env = data.get("env") if isinstance(data, dict) else None
    if not isinstance(env, dict):
        raise SystemExit(f"Provider has no env object: {provider_name!r}")

    return row["name"], env, row["url"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a CC Switch provider into DreamSeed local config.")
    parser.add_argument("--provider", default="GLM", help="CC Switch provider name or id.")
    parser.add_argument("--app-type", default="claude", help="CC Switch app_type to read.")
    parser.add_argument(
        "--db",
        default=str(Path.home() / ".cc-switch" / "cc-switch.db"),
        help="Path to cc-switch.db.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Private DreamSeed provider config to write, for example .dreamseed/providers.local.json.",
    )
    args = parser.parse_args()

    name, env, endpoint = load_provider(Path(args.db), args.provider, args.app_type)
    token = env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY") or env.get("OPENAI_API_KEY")
    if not token:
        raise SystemExit(f"Provider has no usable API token: {name}")

    base_url = env.get("ANTHROPIC_BASE_URL") or env.get("OPENAI_BASE_URL") or endpoint
    model = (
        env.get("ANTHROPIC_MODEL")
        or env.get("ANTHROPIC_DEFAULT_MODEL")
        or env.get("ANTHROPIC_DEFAULT_OPUS_MODEL")
        or env.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
        or env.get("OPENAI_MODEL")
    )
    if not base_url or not model:
        raise SystemExit(f"Provider is missing base URL or model: {name}")

    slug = slugify(name)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    config = {
        "activeProvider": slug,
        "providers": {
            slug: {
                "type": "openai-chat",
                "baseUrl": base_url,
                "apiKey": token,
                "model": model,
                "chatCompletionsPath": "/v1/chat/completions",
                "systemPrefix": "Always place the final answer in visible message content.",
                "timeoutMs": 120000,
            }
        },
    }

    output.write_text(json.dumps(config, ensure_ascii=False, indent=2) + os.linesep, encoding="utf-8")
    print(json.dumps({"ok": True, "provider": name, "slug": slug, "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

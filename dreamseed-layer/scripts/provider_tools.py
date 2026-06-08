from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

TEMPLATES = {
    "openai-compatible": {
        "type": "openai-chat",
        "baseUrl": "https://api.openai.com",
        "apiKeyEnv": "DREAMSEED_API_KEY",
        "model": "gpt-4o-mini",
        "chatCompletionsPath": "/v1/chat/completions",
    },
    "glm": {
        "type": "openai-chat",
        "baseUrl": "https://open.bigmodel.cn/api/paas",
        "apiKeyEnv": "GLM_API_KEY",
        "model": "glm-4.5",
        "chatCompletionsPath": "/v4/chat/completions",
    },
    "deepseek-compatible": {
        "type": "openai-chat",
        "baseUrl": "https://api.deepseek.com",
        "apiKeyEnv": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "chatCompletionsPath": "/v1/chat/completions",
    },
    "gemini-compatible": {
        "type": "openai-chat",
        "baseUrl": "https://generativelanguage.googleapis.com",
        "apiKeyEnv": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
        "chatCompletionsPath": "/v1beta/openai/chat/completions",
    },
    "ollama-local": {
        "type": "openai-chat",
        "baseUrl": "http://127.0.0.1:11434",
        "apiKeyEnv": "OLLAMA_API_KEY",
        "model": "llama3.1",
        "chatCompletionsPath": "/v1/chat/completions",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="DreamSeed provider templates and redacted diagnostics.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("templates", "export-redacted", "import-redacted", "latency", "health", "discover"):
        p = sub.add_parser(name)
        p.add_argument("--config", default="")
        p.add_argument("--from", dest="from_path", default="")
        p.add_argument("--yes", action="store_true")
        p.add_argument("--provider", default="")
        p.add_argument("--port", type=int, default=int(os.environ.get("DREAMSEED_PROVIDER_PORT", "17891")))
        p.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "templates":
        output = {"ok": True, "templates": TEMPLATES}
    elif args.command == "export-redacted":
        output = export_redacted(resolve_config(args.config), args.provider)
    elif args.command == "import-redacted":
        output = import_redacted(args.from_path, resolve_write_config(args.config), yes=args.yes)
    elif args.command == "latency":
        output = latency(args.port, resolve_config(args.config), args.provider)
    elif args.command == "health":
        output = health(args.port, resolve_config(args.config), args.provider)
    elif args.command == "discover":
        output = discover(resolve_config(args.config), args.provider)
    else:
        return 2

    if args.json:
        print_json(output)
    else:
        print_table(output, args.command)
    return 0 if output.get("ok", True) else 1


def resolve_config(explicit: str = "") -> Path:
    appdata = os.environ.get("APPDATA", "")
    home = os.environ.get("DREAMSEED_HOME") or os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    candidates = [
        explicit,
        os.environ.get("DREAMSEED_PROVIDER_CONFIG", ""),
        str(Path(appdata) / "DreamSeed" / "providers.local.json") if appdata else "",
        str(Path(home) / ".dreamseed" / "providers.local.json") if home else "",
        str(ROOT / ".dreamseed" / "providers.local.json"),
        str(ROOT / "config" / "providers.local.json"),
        str(ROOT / "config" / "providers.example.json"),
    ]
    for value in candidates:
        if value and Path(value).exists():
            return Path(value)
    return ROOT / "config" / "providers.example.json"


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def export_redacted(path: Path, provider_name: str = "") -> dict[str, Any]:
    data = read_json(path) or {"providers": {}}
    redacted = json.loads(json.dumps(data))
    for provider in (redacted.get("providers") or {}).values():
        if "apiKey" in provider:
            provider["apiKey"] = "<redacted>"
        if "authorization" in provider:
            provider["authorization"] = "<redacted>"
    active = provider_name or redacted.get("activeProvider")
    return {"ok": True, "configPath": str(path), "activeProvider": active, "config": redacted}


def resolve_write_config(explicit: str = "") -> Path:
    if explicit:
        return Path(explicit)
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        return Path(appdata) / "DreamSeed" / "providers.local.json"
    home = os.environ.get("DREAMSEED_HOME") or os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    if home:
        return Path(home) / ".dreamseed" / "providers.local.json"
    return ROOT / ".dreamseed" / "providers.local.json"


def import_redacted(from_path: str, dest: Path, yes: bool = False) -> dict[str, Any]:
    if not from_path:
        return {"ok": False, "error": "missing --from template path"}
    if not yes:
        return {"ok": False, "error": "refusing to import provider template without --yes"}
    source = Path(from_path)
    data = read_json(source)
    if not isinstance(data, dict):
        return {"ok": False, "error": "template is not valid JSON", "source": str(source)}
    config = data.get("config") if isinstance(data.get("config"), dict) else data
    providers = config.get("providers") if isinstance(config, dict) else None
    if not isinstance(providers, dict) or not providers:
        return {"ok": False, "error": "template must contain providers"}
    for name, provider in providers.items():
        if not isinstance(provider, dict):
            return {"ok": False, "error": f"provider {name} is not an object"}
        if provider.get("apiKey") and provider.get("apiKey") != "<redacted>":
            return {"ok": False, "error": f"provider {name} contains inline apiKey; import refused"}
        provider.pop("apiKey", None)
        provider.setdefault("apiKeyEnv", f"DREAMSEED_{str(name).upper().replace('-', '_').replace('.', '_')}_API_KEY")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "configPath": str(dest), "providers": sorted(providers), "activeProvider": config.get("activeProvider")}


def health(port: int, path: Path, provider_name: str = "") -> dict[str, Any]:
    bridge = get_json(f"http://127.0.0.1:{port}/health", timeout=2.0)
    if bridge.get("ok"):
        return {**bridge, "mode": "bridge"}
    config = provider_config_health(path, provider_name)
    return {**config, "mode": "config", "bridge": bridge}


def latency(port: int, path: Path, provider_name: str = "") -> dict[str, Any]:
    start = time.perf_counter()
    bridge = get_json(f"http://127.0.0.1:{port}/health", timeout=2.0)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    if bridge.get("ok"):
        return {**bridge, "mode": "bridge", "latencyMs": elapsed_ms}
    return provider_latency(path, provider_name, bridge)


def discover(path: Path, provider_name: str = "") -> dict[str, Any]:
    selected = select_provider(path, provider_name)
    if not selected["ok"]:
        return selected
    name = selected["provider"]
    provider = selected["config"]
    base = str(provider.get("baseUrl") or "").rstrip("/")
    if not base:
        return {"ok": False, "error": "active provider has no baseUrl", "provider": name}
    key = provider.get("apiKey") or os.environ.get(str(provider.get("apiKeyEnv") or ""))
    if not key:
        return {"ok": False, "error": "provider key is missing; discovery skipped", "provider": name}
    path_suffix = provider.get("modelsPath") or "/v1/models"
    url = base + path_suffix
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + key, "X-API-Key": key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        return {"ok": False, "error": str(exc), "provider": name, "url": redact_url(url)}
    models = payload.get("data") or payload.get("models") or []
    names = [item if isinstance(item, str) else item.get("id") or item.get("name") for item in models]
    return {"ok": True, "provider": name, "models": [value for value in names if value][:50]}


def provider_config_health(path: Path, provider_name: str = "") -> dict[str, Any]:
    selected = select_provider(path, provider_name)
    if not selected["ok"]:
        return selected
    provider = selected["config"]
    auth = describe_auth(provider)
    ok = bool(provider.get("baseUrl") and provider.get("model") and auth["ok"])
    return {
        "ok": ok,
        "configPath": str(path),
        "provider": selected["provider"],
        "type": provider.get("type", "openai-chat"),
        "baseUrl": redact_url(str(provider.get("baseUrl", ""))),
        "model": provider.get("model", ""),
        "auth": auth["label"],
        "badge": "ready" if ok else "needs-configuration",
    }


def provider_latency(path: Path, provider_name: str = "", bridge: dict[str, Any] | None = None) -> dict[str, Any]:
    selected = select_provider(path, provider_name)
    if not selected["ok"]:
        return {**selected, "mode": "direct", "bridge": bridge or {}}
    provider = selected["config"]
    key = provider.get("apiKey") or os.environ.get(str(provider.get("apiKeyEnv") or ""))
    if not key:
        return {
            "ok": False,
            "mode": "direct",
            "bridge": bridge or {},
            "provider": selected["provider"],
            "error": "provider key is missing; set apiKey in private config or the configured apiKeyEnv",
        }
    if provider.get("type", "openai-chat") != "openai-chat":
        return {
            "ok": False,
            "mode": "direct",
            "bridge": bridge or {},
            "provider": selected["provider"],
            "error": "direct latency currently supports openai-chat compatible providers",
        }

    route = provider.get("chatCompletionsPath") or "/v1/chat/completions"
    url = join_url(str(provider.get("baseUrl", "")), route)
    timeout = min(30.0, max(2.0, float(provider.get("timeoutMs") or 120000) / 1000.0))
    body = {
        "model": provider.get("model"),
        "messages": [{"role": "user", "content": "Reply exactly: ok"}],
        "max_tokens": 16,
        "stream": False,
    }
    headers = {
        "Authorization": "Bearer " + key,
        "X-API-Key": key,
        "Accept": "application/json",
        "Content-Type": "application/json",
        **(provider.get("headers") or {}),
    }
    start = time.perf_counter()
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        payload = json.loads(raw) if raw else {}
        return {
            "ok": True,
            "mode": "direct",
            "provider": selected["provider"],
            "model": provider.get("model"),
            "baseUrl": redact_url(str(provider.get("baseUrl", ""))),
            "route": route,
            "latencyMs": elapsed_ms,
            "outputPreview": extract_openai_preview(payload)[:80],
            "bridge": bridge or {},
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return {
            "ok": False,
            "mode": "direct",
            "provider": selected["provider"],
            "model": provider.get("model"),
            "baseUrl": redact_url(str(provider.get("baseUrl", ""))),
            "route": route,
            "error": f"upstream {exc.code}: {detail}",
            "bridge": bridge or {},
        }
    except Exception as exc:
        return {
            "ok": False,
            "mode": "direct",
            "provider": selected["provider"],
            "model": provider.get("model"),
            "baseUrl": redact_url(str(provider.get("baseUrl", ""))),
            "route": route,
            "error": str(exc),
            "bridge": bridge or {},
        }


def select_provider(path: Path, provider_name: str = "") -> dict[str, Any]:
    data = read_json(path) or {}
    providers = data.get("providers") or {}
    if not providers:
        return {"ok": False, "configPath": str(path), "error": "provider config has no providers"}
    name = provider_name or data.get("activeProvider") or next(iter(providers), "")
    provider = providers.get(name) or {}
    if not provider:
        return {"ok": False, "configPath": str(path), "provider": name, "error": "provider not found"}
    return {"ok": True, "configPath": str(path), "provider": name, "config": provider}


def describe_auth(provider: dict[str, Any]) -> dict[str, Any]:
    if provider.get("apiKey"):
        return {"ok": True, "label": "stored in private config"}
    env_name = str(provider.get("apiKeyEnv") or "")
    if env_name:
        return {"ok": bool(os.environ.get(env_name)), "label": f"env {env_name} is {'set' if os.environ.get(env_name) else 'missing'}"}
    return {"ok": False, "label": "missing"}


def join_url(base: str, suffix: str) -> str:
    return base.rstrip("/") + "/" + suffix.lstrip("/")


def extract_openai_preview(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    content = message.get("content") if isinstance(message, dict) else ""
    return content if isinstance(content, str) else ""


def get_json(url: str, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        return {"ok": True, "url": url, "health": payload}
    except urllib.error.URLError as exc:
        return {"ok": False, "url": url, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def redact_url(url: str) -> str:
    return url.split("?")[0]


def print_table(output: dict[str, Any], command: str) -> None:
    if command == "templates":
        print("DreamSeed provider templates")
        for name, template in output["templates"].items():
            print(f"  - {name}: model={template['model']} url={template['baseUrl']}")
        return
    print(json.dumps(output, ensure_ascii=False, indent=2))


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())

# Installation

DreamSeed publishes a normal `dreamseed` command. The command is source-first:
it starts DreamSeed's provider bridge when configured, then runs one configured
compatible runtime. DreamSeed does not ship or select a second fast/lite kernel.

## Install From A Clone

```powershell
git clone <your-repo-url> dreamseed-code
cd dreamseed-code
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed.ps1
dreamseed --help
```

The installer writes a small user-level shim to:

```text
%LOCALAPPDATA%\DreamSeed\bin\dreamseed.cmd
```

It also adds that directory to the user `PATH`. Open a new terminal after
installation.

The installer also runs `scripts\install-python-deps.ps1` unless
`-SkipPythonDeps` is passed. Python packages are installed into
`.dreamseed-runtime\python-site` inside the clone, so DreamSeed does not need to
modify global Python site-packages.

If `vendor\python-wheels` contains wheels, the installer prefers them. For a
strict offline install:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed.ps1 -OfflinePythonDeps
```

## Install With NPM

From the repository root:

```powershell
npm install -g .
dreamseed --help
```

The package exposes this bin entry:

```json
{
  "bin": {
    "dreamseed": "bin/dreamseed-agent.js"
  }
}
```

NPM install only links the Node command. Install the Python memory/MCP
dependencies separately:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-python-deps.ps1
```

## Configure A Provider Without CC Switch

Use the built-in model manager. For most OpenAI-compatible providers, users only need the base URL, API key, and model name.

Open the local manager before entering the agent:

```powershell
dreamseed manager
```

In the manager you can add, delete, edit, test, and switch models. The private config is written to:

```text
%APPDATA%\DreamSeed\providers.local.json
```

Advanced CLI setup is still available:

```powershell
dreamseed provider setup --name openai --url https://api.openai.com --key your-token --model gpt-4o-mini
```

Add another provider/model:

```powershell
dreamseed provider setup --name glm --url https://your-glm-endpoint.example.com --key your-token --model GLM-5.1
```

Switch models:

```powershell
dreamseed provider list
dreamseed provider use glm
```

Check it without printing secrets:

```powershell
dreamseed provider status
```

Then test:

```powershell
dreamseed provider test
# or:
dreamseed --print "Output exactly: ok"
```

Do not commit `providers.local.json` or any token.

## Runtime

```powershell
[Environment]::SetEnvironmentVariable("DREAMSEED_COMPAT_KERNEL_JS", "<path-to-compatible-kernel.js>", "User")
dreamseed --help
```

or:

```powershell
[Environment]::SetEnvironmentVariable("DREAMSEED_COMPAT_KERNEL_CLI", "compatible-agent", "User")
dreamseed --help
```

When the runtime is configured, DreamSeed injects `.dreamseed/settings.json`,
`.mcp.json`, skills, agents, memory paths, provider bridge settings, and the
system prompt automatically.

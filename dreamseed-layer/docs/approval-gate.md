# DreamSeed Approval Gate

DreamSeed uses an auto-review approval gate inspired by Codex-style approval modes:
safe read-only work should proceed without friction, while risky operations fall
through to the native approval prompt.

Policy file:

```text
config/approval.policy.json
```

Runtime hook:

```text
.dreamseed/settings.json -> hooks.PermissionRequest -> scripts/dreamseed-approval-gate.ps1
```

Behavior:

- Low risk: auto-allow. Examples: `Read`, `Grep`, `Glob`, `git status`, `git diff`.
- Medium or high risk: ask the user through the native permission prompt.
- Critical risk: deny. Examples: shutdown commands, format commands, root recursive deletion, obvious secret-bearing commands.

Useful checks:

```powershell
dreamseed approval status
dreamseed approval audit
dreamseed approval check --tool Bash --command "git status --short"
dreamseed approval check --tool Bash --command "Remove-Item -Recurse -Force D:\data"
```

The gate writes summary-only audit records to `logs/approval-gate/`, which is
excluded from release packages.

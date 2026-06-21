---
name: hook-observer
description: Audit DreamSeed hooks and diagnose hook errors. Use when hooks fail, run slowly, duplicate work, or might write memory without review.
---

# Hook Observer

## Goal
Keep hooks reliable, observable, and low-noise.

## Workflow
1. Run `dreamseed doctor hooks` before changing hook settings.
2. Check command paths, shell, timeout, async behavior, and status messages.
3. Ensure Stop and PostCompact write only memory candidates.
4. Record only summary traces under `logs/hook-trace/`; never store raw prompts or secrets.
5. After changes, run the full smoke script.

## Rules
- Do not add high-frequency hooks without a clear test.
- Do not write directly to MemPalace from hooks.
- Missing hook scripts are failures, not warnings.

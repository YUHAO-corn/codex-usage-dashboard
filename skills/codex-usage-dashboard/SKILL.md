---
name: codex-usage-dashboard
description: Use this when a user wants to install, configure, open, or understand the Codex Usage Dashboard; check Codex token usage; compare Codex session logs with CC Switch logs; or get a local HTML report for Codex token/cost usage.
metadata:
  short-description: Open a local Codex token usage dashboard
---

# Codex Usage Dashboard

This skill helps a user view Codex token and estimated cost usage without manually remembering terminal commands.

Use the repository CLI as the single implementation. Do not reimplement log parsing inside the skill.

## What To Do

If the user is setting this up from the repository link, explain the two usage paths first:

```text
You can use the command directly: run codex-usage to open the report.
You can use the Skill: ask me to use $codex-usage-dashboard and I will open the report and explain it.
```

If the user wants the Skill path, make sure the CLI is installed too. The Skill is the AI-facing entry point; the CLI is the implementation it runs.

1. Locate or install the CLI.
   - If already inside this repository, run `python3 bin/codex-usage`.
   - Otherwise prefer `pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git`.
   - If `pipx` is unavailable, clone the repository and run `python3 bin/codex-usage`.

2. Prefer Codex session logs for total usage.
   - Check `~/.codex/sessions`.
   - If it exists, make sure `ccusage-codex` is available.
   - If missing and npm is available, install it with `npm install -g @ccusage/codex`.
   - Then run `codex-usage` or `python3 bin/codex-usage`.

3. Use CC Switch only when that is the desired accounting view or Codex session parsing is unavailable.
   - Check `~/.cc-switch/cc-switch.db`.
   - Run `codex-usage --source cc-switch` when the user asks for proxy/provider-switching records.

4. Explain the result in plain language.
   - Codex session logs are the preferred source for total Codex token usage.
   - CC Switch is useful for proxy request records and provider-switching context.
   - Costs are estimates, not provider invoices.
   - The dashboard is local and does not upload usage data.

## Common Commands

```bash
codex-usage
codex-usage week
codex-usage 30d
codex-usage --summary month
codex-usage --source cc-switch
codex-usage --since 2026-05-01 --until 2026-05-13
```

## Guardrails

- Do not generate mock usage reports for a user's real usage.
- Do not commit or share a user's generated dashboard if it contains real usage data.
- If creating screenshots for public docs, use demo data only.
- Ask before running installs that require network access.

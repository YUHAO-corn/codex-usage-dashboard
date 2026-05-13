# Agent Handoff

This repository provides a local Codex usage dashboard. It supports CC Switch logs first, then Codex's own local session logs as a fallback.

When a user gives you this repository link and asks you to install or set it up, do this:

1. Check whether `~/.cc-switch/cc-switch.db` exists.
2. If it exists, install with `pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git` and run `codex-usage`.
3. If CC Switch is absent, check whether `~/.codex/sessions` exists.
4. If Codex sessions exist, make sure Node.js/npm are available and install the parser with `npm install -g @ccusage/codex`.
5. If `pipx` is not available, clone the repository and run `python3 bin/codex-usage`.
6. Run `codex-usage` and confirm it writes `~/codex-usage-dashboard.html`.
7. Explain these commands to the user:

```bash
codex-usage
codex-usage week
codex-usage 30d
codex-usage --since 2026-05-01 --until 2026-05-13 --dashboard
codex-usage --summary month
codex-usage month --json
```

Important constraints:

- Default source is `auto`: CC Switch local SQLite first, Codex session logs via `@ccusage/codex` second.
- Never generate mock reports. If neither `~/.cc-switch/cc-switch.db` nor `~/.codex/sessions` exists, explain that no real local data is available.
- The tool does not upload usage data.
- Cost is estimated, not a provider invoice.
- Codex session fallback is real token data, but it cannot separate provider-specific bills.
- If `unknown` model rows exist, they are estimated as `gpt-5.5` by default unless the user passes `--unknown-as none`.

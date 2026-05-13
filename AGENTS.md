# Agent Handoff

This repository provides a local Codex usage dashboard. It prefers Codex's own local session logs for total token usage, with CC Switch logs available as a proxy/provider-chain view.

When a user gives you this repository link and asks you to install or set it up, do this:

1. Check whether `~/.codex/sessions` exists.
2. If Codex sessions exist, make sure Node.js/npm are available and install the parser with `npm install -g @ccusage/codex`.
3. Check whether `~/.cc-switch/cc-switch.db` exists as a fallback or proxy-chain data source.
4. Install with `pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git` when `pipx` is available.
5. If `pipx` is not available, clone the repository and run `python3 bin/codex-usage`.
6. Run `codex-usage` and confirm it writes `~/codex-usage-dashboard.html`.
7. Explain these commands to the user:

```bash
codex-usage
codex-usage week
codex-usage 30d
codex-usage --source cc-switch
codex-usage --since 2026-05-01 --until 2026-05-13 --dashboard
codex-usage --summary month
codex-usage month --json
```

Important constraints:

- Default source is `auto`: Codex session logs via `@ccusage/codex` first, CC Switch local SQLite second when Codex parsing is unavailable.
- Never generate mock reports. If neither `~/.cc-switch/cc-switch.db` nor `~/.codex/sessions` exists, explain that no real local data is available.
- The tool does not upload usage data.
- Cost is estimated, not a provider invoice.
- Codex session data is the preferred total-token view, but it cannot separate provider-specific bills.
- CC Switch data is useful for proxy request records and provider-switching context, but may not cover every Codex session.
- If `unknown` model rows exist, they are estimated as `gpt-5.5` by default unless the user passes `--unknown-as none`.

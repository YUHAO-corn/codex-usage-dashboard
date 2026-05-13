# Agent Handoff

This repository provides a local Codex usage dashboard for CC Switch users.

When a user gives you this repository link and asks you to install or set it up, do this:

1. Check whether `~/.cc-switch/cc-switch.db` exists.
2. Install with `pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git` if `pipx` is available.
3. If `pipx` is not available, clone the repository and run `python3 bin/codex-usage dashboard`.
4. Run `codex-usage dashboard` and confirm it writes `~/codex-usage-dashboard.html`.
5. Explain these commands to the user:

```bash
codex-usage dashboard
codex-usage dashboard week
codex-usage dashboard 30d
codex-usage --since 2026-05-01 --until 2026-05-13 --dashboard
codex-usage month --json
```

Important constraints:

- The current data source is CC Switch's local SQLite database.
- The tool does not upload usage data.
- Cost is estimated, not a provider invoice.
- If `unknown` model rows exist, they are estimated as `gpt-5.5` by default unless the user passes `--unknown-as none`.

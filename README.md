# Codex Usage Dashboard

Local Codex token and cost analytics for people who switch providers through CC Switch.

Run one command and open a self-contained HTML dashboard that summarizes every Codex record in the local CC Switch SQLite database, regardless of which provider was active.

## Features

- Cross-provider Codex usage totals from `~/.cc-switch/cc-switch.db`
- Input, output, cached input, request count, and estimated cost
- Daily trend chart and model distribution
- Terminal summary, JSON export, and HTML dashboard
- No server and no external web assets

## Usage

```bash
codex-usage dashboard
codex-usage dashboard 30d
codex-usage 30d --dashboard
codex-usage month
codex-usage last7 --daily
codex-usage month --json
```

The default dashboard output is:

```text
~/codex-usage-dashboard.html
```

## Cost Notes

Costs are estimates. The command reads CC Switch's local pricing table and fills a few missing OpenAI model prices locally. Historical rows whose model is `unknown` are estimated as `gpt-5.5` by default:

```bash
codex-usage month --unknown-as none
```

## Development

```bash
python3 -m py_compile codex_usage_dashboard/cli.py
python3 bin/codex-usage dashboard --no-open
```

## License

MIT

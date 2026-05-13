# Codex Usage Dashboard

**English** | [中文](#中文)

A local token and estimated cost dashboard for Codex. Run `codex-usage` and it opens a local HTML report with input tokens, output tokens, cached input tokens, model breakdowns, daily trends, and estimated cost.

By default it reads Codex's own local session logs through [`@ccusage/codex`](https://www.npmjs.com/package/@ccusage/codex). If you use CC Switch and want the proxy/provider-chain view, it can also read the local CC Switch SQLite database.

![status](https://img.shields.io/badge/status-local%20first-1c7c54)
![python](https://img.shields.io/badge/python-3.10%2B-2457a6)
![license](https://img.shields.io/badge/license-MIT-c89020)

![Codex Usage Dashboard screenshot](docs/assets/dashboard-preview.png)

> The screenshot uses demo data only. It does not include real local usage.

## Who It Is For

- You use Codex CLI or Codex Desktop.
- You want to see weekly, monthly, or custom-range Codex token usage.
- You may use CC Switch across multiple providers, or you may not use CC Switch at all.
- You want to give a GitHub link to an AI coding agent and have it install, configure, and explain the report for you.

## Two Ways To Use It

This project supports both a CLI and a Skill. They use the same implementation; only the entry point is different.

If you are comfortable with commands, install it and run `codex-usage`.

If you prefer using an AI agent, install the included Skill. Then ask your agent to use `$codex-usage-dashboard`; it will check your environment, run the report, and explain the data source.

## CLI Usage

Recommended install:

```bash
pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git
codex-usage
```

You can also clone and run it directly:

```bash
git clone https://github.com/YUHAO-corn/codex-usage-dashboard.git
cd codex-usage-dashboard
python3 bin/codex-usage
```

By default it writes and opens:

```text
~/codex-usage-dashboard.html
```

## Skill Usage

This repository ships a Codex-compatible Skill at `skills/codex-usage-dashboard`.

The Skill does not replace the CLI or duplicate the parser. It tells an AI agent how to inspect your environment, install dependencies, choose the right data source, run `codex-usage`, and explain the report.

If your AI client can install Skills from GitHub, give it this path:

```text
https://github.com/YUHAO-corn/codex-usage-dashboard/tree/main/skills/codex-usage-dashboard
```

You can say:

```text
Please install this Codex Usage Dashboard Skill:
https://github.com/YUHAO-corn/codex-usage-dashboard/tree/main/skills/codex-usage-dashboard
```

Restart Codex or your AI client after installation if Skills are loaded at startup.

After installation, use:

```text
Use $codex-usage-dashboard to open my Codex usage report and explain the data source.
```

## Data Sources

Default mode is `--source auto`:

- If `~/.codex/sessions/**/rollout-*.jsonl` exists, it prefers Codex's local session logs. This is the better view for total Codex token usage and is not mock data.
- If Codex session parsing is unavailable but `~/.cc-switch/cc-switch.db` exists, it falls back to CC Switch local SQLite.
- If you specifically want the proxy/provider-chain view, run `codex-usage --source cc-switch`.

Codex session parsing needs `ccusage-codex`. Install it once:

```bash
npm install -g @ccusage/codex
codex-usage
```

If it is not installed globally, the tool will try to run `@ccusage/codex` through `npx`. The first run may need Node.js and network access.

## For AI Coding Agents

If you are Codex, Claude Code, or another local AI coding agent and a user gives you this repository, first explain that there are two entry points:

```text
You can use the CLI directly: run codex-usage to open the report.
You can also install the Skill: then ask me to use $codex-usage-dashboard and I will open the report and explain it.
```

If the user chooses CLI:

1. Check Python: `python3 --version`, requiring Python 3.10+.
2. Check Codex sessions: `~/.codex/sessions`.
3. If Codex sessions exist, check Node.js/npm and install the parser with `npm install -g @ccusage/codex`.
4. Check CC Switch fallback data: `~/.cc-switch/cc-switch.db`.
5. Install this project: `pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git`.
6. Run `codex-usage` and confirm the browser opens `~/codex-usage-dashboard.html`.
7. Tell the user the common commands:

```bash
codex-usage                    # open this month's dashboard
codex-usage week               # this week
codex-usage 30d                # last 30 days
codex-usage --source cc-switch # force CC Switch source
codex-usage --summary month    # terminal summary
codex-usage month --json       # JSON output
```

If the user chooses Skill:

1. Install the Skill path: `https://github.com/YUHAO-corn/codex-usage-dashboard/tree/main/skills/codex-usage-dashboard`.
2. Make sure the CLI is available too, because the Skill invokes `codex-usage` instead of copying the parser.
3. Install or verify `@ccusage/codex` so Codex local sessions can be used first.
4. Ask the user to restart Codex or the relevant AI client so Skills are reloaded.
5. Tell the user the future prompt:

```text
Use $codex-usage-dashboard to open my Codex usage report and explain the data source.
```

If the user has neither CC Switch data nor `~/.codex/sessions`, there is no real local usage data to report. Do not generate a mock report.

## Periods

Built-in periods:

```bash
codex-usage today
codex-usage yesterday
codex-usage week
codex-usage last7
codex-usage last14
codex-usage month
codex-usage 30d
codex-usage last90
codex-usage quarter
codex-usage year
codex-usage all
```

Custom date ranges:

```bash
codex-usage --since 2026-05-01 --until 2026-05-13
codex-usage --since 2026-05-01 --until 2026-05-13 --json
```

Older dashboard-style commands still work:

```bash
codex-usage dashboard
codex-usage dashboard 30d
codex-usage 30d --dashboard
```

## Output Modes

HTML dashboard is the default:

```bash
codex-usage
codex-usage 30d
codex-usage --no-open
```

Terminal summary:

```bash
codex-usage --summary month
codex-usage --summary last7 --daily
```

JSON:

```bash
codex-usage month --json
```

Language:

```bash
codex-usage --lang auto # default, follows browser/system language
codex-usage --lang en   # English dashboard
codex-usage --lang zh   # Chinese dashboard
```

## What The Dashboard Shows

- Total tokens
- Input tokens
- Output tokens
- Cached input tokens
- Cached input ratio
- Estimated cost
- Daily trends
- Model breakdown
- Daily and model detail tables
- Current data source and accounting notes

## Reliability Notes

Cost is an estimate, not a provider invoice.

The Codex session source reads local Codex JSONL logs. It is a good view for total Codex token usage. It does not separate the bill by provider and it does not replace official provider invoices, but it is much more useful than mock data or screenshots.

The CC Switch source reads local proxy request logs. It is useful for requests that passed through CC Switch and provider-switching context. It may not cover every Codex session.

## Privacy

- Reads only local `~/.cc-switch/cc-switch.db` or `~/.codex/sessions`
- Does not upload usage data
- Writes a local HTML file
- The dashboard does not depend on remote JS or CSS

## Development

```bash
python3 -m py_compile codex_usage_dashboard/cli.py
python3 bin/codex-usage --no-open
python3 bin/codex-usage --source codex --summary today
```

## 中文

一个本地 Codex 用量仪表盘。运行 `codex-usage`，它会生成并打开 HTML 报告，统计 input / output / cached input token、模型分布、每日趋势和估算费用。

它默认优先读取 Codex 自己的 session 日志，并复用 [`@ccusage/codex`](https://www.npmjs.com/package/@ccusage/codex) 做 token 统计；需要代理链路或供应商切换口径时，也可以切到 CC Switch 的本地请求日志。

## 适合谁

- 你用 Codex CLI / Codex Desktop。
- 你想看本周、本月、近 30 天或自定义范围的 Codex token 用量。
- 你可能用 CC Switch 切多个供应商，也可能完全不用 CC Switch。
- 你想把一个开源链接丢给 AI agent，让它帮你装好并解释以后怎么用。

## 两种用法

这个项目同时支持命令行和 Skill。两种方式用的是同一套统计逻辑，区别只是入口不同。

如果你愿意直接运行命令，安装后执行 `codex-usage` 就会打开本地用量网页。

如果你更希望通过 AI agent 使用，可以安装仓库里的 Skill。以后你只要让 AI 使用 `$codex-usage-dashboard`，它就会帮你检查环境、运行统计，并解释报告。

## 命令行用法

推荐用 `pipx` 安装：

```bash
pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git
codex-usage
```

也可以直接 clone 后运行：

```bash
git clone https://github.com/YUHAO-corn/codex-usage-dashboard.git
cd codex-usage-dashboard
python3 bin/codex-usage
```

默认会生成并打开：

```text
~/codex-usage-dashboard.html
```

## Skill 用法

这个仓库也附带一个 Codex-compatible Skill：`skills/codex-usage-dashboard`。

Skill 不替代 CLI，也不复制一套统计逻辑。它的作用是让 AI agent 知道该怎么帮用户检查环境、安装依赖、选择数据源、运行 `codex-usage`，并解释报告。

如果你的 AI 支持从 GitHub 安装 Skill，可以把这个路径交给它：

```text
https://github.com/YUHAO-corn/codex-usage-dashboard/tree/main/skills/codex-usage-dashboard
```

你可以直接对 AI 说：

```text
请帮我安装这个 Codex Usage Dashboard Skill：
https://github.com/YUHAO-corn/codex-usage-dashboard/tree/main/skills/codex-usage-dashboard
```

安装后重启 Codex 或对应 AI 客户端，让它重新加载 Skills。

安装后可以这样说：

```text
用 $codex-usage-dashboard 打开我的 Codex 用量报告，并解释数据源。
```

## 数据源

默认 `--source auto`：

- 如果存在 `~/.codex/sessions/**/rollout-*.jsonl`，优先使用 Codex 本地真实日志。这个口径更适合统计 Codex 总 token，不是 mock 数据。
- 如果 Codex session 解析器不可用，但存在 `~/.cc-switch/cc-switch.db`，自动退回 CC Switch 本地 SQLite。
- 如果你想强制看代理链路口径，可以运行 `codex-usage --source cc-switch`。

Codex session 口径需要 `ccusage-codex`。建议先安装一次：

```bash
npm install -g @ccusage/codex
codex-usage
```

如果没有全局安装，工具会尝试用 `npx` 临时运行 `@ccusage/codex`，首次运行需要网络和 Node.js。

## 给 AI Agent 的安装提示

如果你是 Codex、Claude Code 或其它本地 AI coding agent，用户给你这个仓库链接后，请先告诉用户有两种方式：

```text
你可以直接用命令行：以后运行 codex-usage 就会打开报告。
你也可以把它装成 Skill：以后让我使用 $codex-usage-dashboard，我会帮你打开报告并解释数据。
```

如果用户选择命令行：

1. 检查 Python 版本：`python3 --version`，需要 Python 3.10+。
2. 检查 Codex session 目录：`~/.codex/sessions`。
3. 如果 Codex sessions 存在，确认 Node.js/npm 可用，并安装统计解析器：`npm install -g @ccusage/codex`。
4. 检查 CC Switch 数据库：`~/.cc-switch/cc-switch.db`，这是备用或代理账本口径。
5. 安装本项目：`pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git`。
6. 运行 `codex-usage`，确认浏览器打开 `~/codex-usage-dashboard.html`。
7. 告诉用户以后常用命令：

```bash
codex-usage                    # 打开本月仪表盘
codex-usage week               # 本周仪表盘
codex-usage 30d                # 近 30 天仪表盘
codex-usage --source cc-switch # 强制使用 CC Switch 口径
codex-usage --summary month    # 终端摘要
codex-usage month --json       # JSON 输出
```

如果用户选择 Skill：

1. 安装 Skill 路径：`https://github.com/YUHAO-corn/codex-usage-dashboard/tree/main/skills/codex-usage-dashboard`。
2. 同时确保 CLI 可用，因为 Skill 会调用 `codex-usage`，不会自己复制统计逻辑。
3. 安装或确认 `@ccusage/codex` 可用，以便优先读取 Codex 本地 session。
4. 让用户重启 Codex 或对应 AI 客户端，让它重新加载 Skills。
5. 告诉用户以后这样调用：

```text
用 $codex-usage-dashboard 打开我的 Codex 用量报告，并解释数据源。
```

如果用户机器上既没有 CC Switch，也没有 `~/.codex/sessions`，那就没有真实本地数据可统计。不要生成 mock 报告。

## 支持的统计周期

内置周期：

```bash
codex-usage today
codex-usage yesterday
codex-usage week
codex-usage last7
codex-usage last14
codex-usage month
codex-usage 30d
codex-usage last90
codex-usage quarter
codex-usage year
codex-usage all
```

任意日期范围：

```bash
codex-usage --since 2026-05-01 --until 2026-05-13
codex-usage --since 2026-05-01 --until 2026-05-13 --json
```

老用法仍然可用：

```bash
codex-usage dashboard
codex-usage dashboard 30d
codex-usage 30d --dashboard
```

## 输出方式

HTML dashboard 是默认输出：

```bash
codex-usage
codex-usage 30d
codex-usage --no-open
```

终端摘要：

```bash
codex-usage --summary month
codex-usage --summary last7 --daily
```

JSON：

```bash
codex-usage month --json
```

语言：

```bash
codex-usage --lang auto # 默认，跟随浏览器/系统语言
codex-usage --lang en   # 英文仪表盘
codex-usage --lang zh   # 中文仪表盘
```

## 页面里能看到什么

- Token 总量
- 输入 token
- 输出 token
- 缓存输入 token
- 缓存输入占输入的比例
- 估算费用
- 每日趋势
- 模型分布
- 每日明细和模型明细
- 当前数据源和统计口径说明

## 可靠性说明

费用是估算，不是供应商真实账单。

Codex session 数据源来自 Codex 本地 JSONL 日志，适合统计真实 Codex token 总用量。它不会区分你背后到底用了哪个供应商，也不能替代供应商账单，但比 mock 数据或终端截屏可靠得多。

CC Switch 数据源来自本地代理请求日志，适合统计“经过 CC Switch 的 Codex 请求”和供应商切换链路。它不一定覆盖所有 Codex session。

## 数据和隐私

- 只读取本机 `~/.cc-switch/cc-switch.db` 或 `~/.codex/sessions`
- 不上传你的用量数据
- 生成的是本地 HTML 文件
- Dashboard 不依赖远程 JS/CSS

## 开发

```bash
python3 -m py_compile codex_usage_dashboard/cli.py
python3 bin/codex-usage --no-open
python3 bin/codex-usage --source codex --summary today
```

## License

MIT

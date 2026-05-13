# Codex Usage Dashboard

一个给 Codex + CC Switch 用户看的本地用量仪表盘。

运行一个命令，它会读取本机 CC Switch 的 Codex 使用记录，生成并打开一个中文 HTML dashboard，统计所有经过 Codex 的 token 和估算费用。不区分你当时切的是 OpenAI 官方、代理、Kimi、MiMo，还是其它渠道。

![status](https://img.shields.io/badge/status-local%20first-1c7c54)
![python](https://img.shields.io/badge/python-3.10%2B-2457a6)
![license](https://img.shields.io/badge/license-MIT-c89020)

## 适合谁

- 你用 Codex CLI / Codex Desktop。
- 你用 CC Switch 在多个供应商之间切换。
- 你想知道自己本周、本月、近 30 天到底用了多少 input / output / cached input token。
- 你不想分别去不同供应商后台查账。

## 快速使用

推荐用 `pipx` 或 `uv tool` 安装：

```bash
pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git
codex-usage dashboard
```

也可以直接 clone 后运行：

```bash
git clone https://github.com/YUHAO-corn/codex-usage-dashboard.git
cd codex-usage-dashboard
python3 bin/codex-usage dashboard
```

默认会生成并打开：

```text
~/codex-usage-dashboard.html
```

## 给 AI Agent 的安装提示

如果你是 Codex、Claude Code 或其它本地 AI coding agent，请按下面步骤帮助用户安装：

1. 确认用户本机存在 CC Switch 数据库：`~/.cc-switch/cc-switch.db`
2. 安装项目：`pipx install git+https://github.com/YUHAO-corn/codex-usage-dashboard.git`
3. 如果没有 `pipx`，就 clone 仓库并运行：`python3 bin/codex-usage dashboard`
4. 运行 `codex-usage dashboard`，确认浏览器打开 `~/codex-usage-dashboard.html`
5. 告诉用户以后常用命令：

```bash
codex-usage dashboard          # 打开本月仪表盘
codex-usage dashboard week     # 本周
codex-usage dashboard 30d      # 近 30 天
codex-usage month              # 终端摘要
codex-usage month --json       # JSON 输出
```

如果用户没有 CC Switch，这个工具暂时无法统计，因为当前版本的数据源是 CC Switch 的本地 SQLite 日志。

## 支持的统计周期

内置周期：

```bash
codex-usage dashboard today
codex-usage dashboard yesterday
codex-usage dashboard week
codex-usage dashboard last7
codex-usage dashboard last14
codex-usage dashboard month
codex-usage dashboard 30d
codex-usage dashboard last90
codex-usage dashboard quarter
codex-usage dashboard year
codex-usage dashboard all
```

任意日期范围：

```bash
codex-usage --since 2026-05-01 --until 2026-05-13 --dashboard
codex-usage --since 2026-05-01 --until 2026-05-13 --json
```

## 输出方式

HTML dashboard：

```bash
codex-usage dashboard
codex-usage dashboard 30d
codex-usage 30d --dashboard
```

终端摘要：

```bash
codex-usage month
codex-usage last7 --daily
```

JSON：

```bash
codex-usage month --json
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

## 费用口径

费用是估算，不是供应商真实账单。

工具会优先读取 CC Switch 本地价格表，并补充少量内置价格。历史记录里如果模型名是 `unknown`，默认按 `gpt-5.5` 估算，页面会明确标注这个假设。

如果想严格只统计已知模型价格：

```bash
codex-usage dashboard --unknown-as none
```

## 数据和隐私

- 只读取本机 `~/.cc-switch/cc-switch.db`
- 不上传数据
- 生成的是本地 HTML 文件
- 不依赖远程 JS/CSS

## 开发

```bash
python3 -m py_compile codex_usage_dashboard/cli.py
python3 bin/codex-usage dashboard --no-open
```

## License

MIT

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sqlite3
import sys
import webbrowser
from decimal import Decimal, InvalidOperation
from pathlib import Path


DEFAULT_DB = Path.home() / ".cc-switch" / "cc-switch.db"
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
DEFAULT_OUTPUT = Path.home() / "codex-usage-dashboard.html"
SOURCE_LABELS = {
    "cc-switch": "CC Switch 本地 SQLite",
    "codex": "Codex 本地 session 日志",
}

# USD per 1M tokens. These fill gaps in older CC Switch pricing tables.
DEFAULT_PRICES = {
    "gpt-5.5": {"input": "5.00", "output": "30.00", "cache_read": "0.50", "cache_creation": "0"},
    "gpt-5.4": {"input": "2.50", "output": "15.00", "cache_read": "0.25", "cache_creation": "0"},
    "gpt-5.4-mini": {"input": "0.75", "output": "4.50", "cache_read": "0.075", "cache_creation": "0"},
    "gpt-5.3-codex": {"input": "1.75", "output": "14.00", "cache_read": "0.175", "cache_creation": "0"},
    "gpt-5.2": {"input": "1.75", "output": "14.00", "cache_read": "0.175", "cache_creation": "0"},
    "gpt-5.2-codex": {"input": "1.75", "output": "14.00", "cache_read": "0.175", "cache_creation": "0"},
    "gpt-5.1": {"input": "1.25", "output": "10.00", "cache_read": "0.125", "cache_creation": "0"},
    "gpt-5.1-codex": {"input": "1.25", "output": "10.00", "cache_read": "0.125", "cache_creation": "0"},
    "gpt-5": {"input": "1.25", "output": "10.00", "cache_read": "0.125", "cache_creation": "0"},
    "gpt-5-codex": {"input": "1.25", "output": "10.00", "cache_read": "0.125", "cache_creation": "0"},
    "gpt-5-mini": {"input": "0.25", "output": "2.00", "cache_read": "0.025", "cache_creation": "0"},
    "gpt-5-nano": {"input": "0.05", "output": "0.40", "cache_read": "0.005", "cache_creation": "0"},
}


def dec(value, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def normalize_model(model: str | None) -> str:
    if not model:
        return "unknown"
    value = str(model).strip()
    value = re.sub(r"\((high|medium|low|minimal|xhigh)\)$", "", value)
    value = re.sub(r"-(high|medium|low|minimal|xhigh)$", "", value)
    return value or "unknown"


def local_now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def parse_date(value: str | None, end: bool = False) -> int | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise SystemExit(f"Invalid date '{value}', expected YYYY-MM-DD")
    if end:
        parsed += dt.timedelta(days=1)
    return int(parsed.replace(tzinfo=local_now().tzinfo).timestamp())


def parse_timestamp(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_now().tzinfo)
    return parsed.astimezone()


def period_bounds(args: argparse.Namespace) -> tuple[int | None, int | None, str, str]:
    if args.since or args.until:
        return parse_date(args.since), parse_date(args.until, end=True), args.since or "beginning", args.until or "now"

    today = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    if args.period == "today":
        return int(today.timestamp()), None, "today", "now"
    if args.period == "yesterday":
        start = today - dt.timedelta(days=1)
        return int(start.timestamp()), int(today.timestamp()), "yesterday", "today"
    if args.period == "week":
        start = today - dt.timedelta(days=today.weekday())
        return int(start.timestamp()), None, "this week", "now"
    if args.period == "last7":
        start = local_now() - dt.timedelta(days=7)
        return int(start.timestamp()), None, "last 7 days", "now"
    if args.period == "last14":
        start = local_now() - dt.timedelta(days=14)
        return int(start.timestamp()), None, "last 14 days", "now"
    if args.period == "month":
        return int(today.replace(day=1).timestamp()), None, "this month", "now"
    if args.period == "30d":
        start = local_now() - dt.timedelta(days=30)
        return int(start.timestamp()), None, "last 30 days", "now"
    if args.period == "last90":
        start = local_now() - dt.timedelta(days=90)
        return int(start.timestamp()), None, "last 90 days", "now"
    if args.period == "quarter":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=quarter_month, day=1)
        return int(start.timestamp()), None, "this quarter", "now"
    if args.period == "year":
        start = today.replace(month=1, day=1)
        return int(start.timestamp()), None, "this year", "now"
    if args.period == "all":
        return None, None, "beginning", "now"
    raise SystemExit(f"Unknown period '{args.period}'")


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"CC Switch database not found: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def default_prices() -> dict[str, dict[str, Decimal]]:
    return {k: {kk: dec(vv) for kk, vv in v.items()} for k, v in DEFAULT_PRICES.items()}


def load_prices(conn: sqlite3.Connection) -> dict[str, dict[str, Decimal]]:
    prices = default_prices()
    try:
        rows = conn.execute(
            """
            SELECT model_id, input_cost_per_million, output_cost_per_million,
                   cache_read_cost_per_million, cache_creation_cost_per_million
            FROM model_pricing
            """
        ).fetchall()
    except sqlite3.Error:
        rows = []

    for row in rows:
        prices[normalize_model(row["model_id"])] = {
            "input": dec(row["input_cost_per_million"]),
            "output": dec(row["output_cost_per_million"]),
            "cache_read": dec(row["cache_read_cost_per_million"]),
            "cache_creation": dec(row["cache_creation_cost_per_million"]),
        }

    prices["gpt-5.5"] = {kk: dec(vv) for kk, vv in DEFAULT_PRICES["gpt-5.5"].items()}
    return prices


def where_clause(start_ts: int | None, end_ts: int | None) -> tuple[str, list[int]]:
    clauses = ["app_type = 'codex'"]
    params: list[int] = []
    if start_ts is not None:
        clauses.append("created_at >= ?")
        params.append(start_ts)
    if end_ts is not None:
        clauses.append("created_at < ?")
        params.append(end_ts)
    return " AND ".join(clauses), params


def fetch_rows(conn: sqlite3.Connection, start_ts: int | None, end_ts: int | None) -> list[sqlite3.Row]:
    where, params = where_clause(start_ts, end_ts)
    return conn.execute(
        f"""
        SELECT date(datetime(created_at, 'unixepoch', 'localtime')) AS day,
               model,
               COUNT(*) AS requests,
               SUM(input_tokens) AS input_tokens,
               SUM(output_tokens) AS output_tokens,
               SUM(cache_read_tokens) AS cache_read_tokens,
               SUM(cache_creation_tokens) AS cache_creation_tokens,
               SUM(CAST(total_cost_usd AS REAL)) AS logged_cost_usd
        FROM proxy_request_logs
        WHERE {where}
        GROUP BY day, model
        ORDER BY day ASC, SUM(input_tokens + output_tokens) DESC
        """,
        params,
    ).fetchall()


def date_arg_from_ts(timestamp: int | None, inclusive_end: bool = False) -> str | None:
    if timestamp is None:
        return None
    if inclusive_end:
        timestamp -= 1
    return dt.datetime.fromtimestamp(timestamp, tz=local_now().tzinfo).strftime("%Y-%m-%d")


def ccusage_base_command(args: argparse.Namespace) -> list[str]:
    if args.ccusage_bin:
        return [args.ccusage_bin]

    installed = shutil.which("ccusage-codex")
    if installed:
        return [installed]

    return ["npx", "--yes", "@ccusage/codex@latest"]


def ccusage_command(args: argparse.Namespace, start_ts: int | None, end_ts: int | None) -> list[str]:
    command = [*ccusage_base_command(args), "daily", "--json", "--locale", "en-CA"]
    since = date_arg_from_ts(start_ts)
    until = date_arg_from_ts(end_ts, inclusive_end=True)
    if since:
        command.extend(["--since", since])
    if until:
        command.extend(["--until", until])
    if args.timezone:
        command.extend(["--timezone", args.timezone])
    if args.ccusage_offline:
        command.append("--offline")
    return command


def fetch_ccusage_rows(args: argparse.Namespace, start_ts: int | None, end_ts: int | None) -> list[dict]:
    codex_home = Path(args.codex_home).expanduser()
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.exists():
        raise SystemExit(f"Codex session directory not found: {sessions_dir}")

    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    command = ccusage_command(args, start_ts, end_ts)
    try:
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    except FileNotFoundError:
        raise SystemExit("npx not found. Install Node.js first, or use CC Switch as the data source.")

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(
            "@ccusage/codex failed. If this machine does not have CC Switch, install the parser with "
            "`npm install -g @ccusage/codex` and retry. Raw error:\n" + stderr
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"@ccusage/codex returned invalid JSON: {exc}") from exc

    rows: list[dict] = []
    for day_item in payload.get("daily", []):
        day = parse_ccusage_day(day_item.get("date"))
        if not day:
            continue
        day_cost = dec(day_item.get("costUSD"))
        day_tokens = dec(day_item.get("totalTokens"))
        models = day_item.get("models") if isinstance(day_item.get("models"), dict) else {}
        if not models:
            models = {"unknown": day_item}

        for model, stats in models.items():
            model_tokens = dec(stats.get("totalTokens"))
            cost_share = Decimal("1") if day_tokens <= 0 else model_tokens / day_tokens
            rows.append(
                {
                    "day": day,
                    "model": model or "unknown",
                    "requests": 1,
                    "input_tokens": int(stats.get("inputTokens") or 0),
                    "output_tokens": int(stats.get("outputTokens") or 0),
                    "reasoning_output_tokens": int(stats.get("reasoningOutputTokens") or 0),
                    "cache_read_tokens": int(stats.get("cachedInputTokens") or 0),
                    "cache_creation_tokens": 0,
                    "logged_cost_usd": 0,
                    "estimated_cost_usd": day_cost * cost_share,
                }
            )
    return rows


def parse_ccusage_day(value: str | None) -> str | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def row_value(row: sqlite3.Row | dict, key: str, default=0):
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


def estimate_cost(item: dict, prices: dict[str, dict[str, Decimal]], unknown_as: str | None) -> Decimal | None:
    model = normalize_model(item["model"])
    if model == "unknown" and unknown_as and unknown_as != "none":
        model = normalize_model(unknown_as)
    price = prices.get(model)
    if not price:
        return None

    input_tokens = dec(item["input_tokens"])
    output_tokens = dec(item["output_tokens"])
    cache_read_tokens = dec(item["cache_read_tokens"])
    cache_creation_tokens = dec(item["cache_creation_tokens"])
    uncached_input = max(Decimal("0"), input_tokens - cache_read_tokens)
    return (
        uncached_input * price["input"]
        + cache_read_tokens * price["cache_read"]
        + output_tokens * price["output"]
        + cache_creation_tokens * price["cache_creation"]
    ) / Decimal("1000000")


def summarize(rows: list[sqlite3.Row | dict], prices: dict[str, dict[str, Decimal]], unknown_as: str | None) -> dict:
    daily: dict[str, dict] = {}
    models: dict[str, dict] = {}
    total = empty_bucket()
    missing_price: set[str] = set()

    for row in rows:
        item = {
            "day": row_value(row, "day"),
            "model": row_value(row, "model", "unknown") or "unknown",
            "normalized_model": normalize_model(row_value(row, "model", "unknown")),
            "requests": int(row_value(row, "requests") or 0),
            "input_tokens": int(row_value(row, "input_tokens") or 0),
            "output_tokens": int(row_value(row, "output_tokens") or 0),
            "reasoning_output_tokens": int(row_value(row, "reasoning_output_tokens") or 0),
            "cache_read_tokens": int(row_value(row, "cache_read_tokens") or 0),
            "cache_creation_tokens": int(row_value(row, "cache_creation_tokens") or 0),
            "logged_cost_usd": dec(row_value(row, "logged_cost_usd")),
        }
        item["total_tokens"] = item["input_tokens"] + item["output_tokens"]
        provided_cost = row_value(row, "estimated_cost_usd", None)
        item["estimated_cost_usd"] = dec(provided_cost) if provided_cost is not None else estimate_cost(item, prices, unknown_as)
        item["estimated_as"] = (
            normalize_model(unknown_as)
            if item["normalized_model"] == "unknown" and unknown_as and unknown_as != "none"
            else item["normalized_model"]
        )

        day_bucket = daily.setdefault(item["day"], empty_bucket(day=item["day"]))
        add_bucket(day_bucket, item)

        model_bucket = models.setdefault(item["model"], empty_bucket(model=item["model"], normalized_model=item["normalized_model"], estimated_as=item["estimated_as"]))
        add_bucket(model_bucket, item)
        add_bucket(total, item)

        if item["estimated_cost_usd"] is None:
            missing_price.add(item["model"])

    daily_rows = sorted(daily.values(), key=lambda i: i["day"])
    model_rows = sorted(models.values(), key=lambda i: i["total_tokens"], reverse=True)
    for bucket in [total, *daily_rows, *model_rows]:
        finalize_bucket(bucket)

    unknown_tokens = sum(i["total_tokens"] for i in model_rows if normalize_model(i.get("model")) == "unknown")
    return {
        "generated_at": local_now().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "total": total,
        "daily": daily_rows,
        "models": model_rows,
        "missing_price_models": sorted(missing_price),
        "unknown_tokens": unknown_tokens,
        "unknown_as": unknown_as,
    }


def empty_bucket(**extra) -> dict:
    bucket = {
        "requests": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "total_tokens": 0,
        "logged_cost_usd": Decimal("0"),
        "estimated_cost_usd": Decimal("0"),
        "unpriced_tokens": 0,
    }
    bucket.update(extra)
    return bucket


def add_bucket(bucket: dict, item: dict) -> None:
    for key in ["requests", "input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens", "total_tokens"]:
        bucket[key] += item[key]
    bucket["logged_cost_usd"] += item["logged_cost_usd"]
    if item["estimated_cost_usd"] is None:
        bucket["unpriced_tokens"] += item["total_tokens"]
    else:
        bucket["estimated_cost_usd"] += item["estimated_cost_usd"]


def finalize_bucket(bucket: dict) -> None:
    input_tokens = bucket["input_tokens"]
    bucket["cache_ratio"] = float(bucket["cache_read_tokens"] / input_tokens) if input_tokens else 0
    bucket["output_ratio"] = float(bucket["output_tokens"] / bucket["total_tokens"]) if bucket["total_tokens"] else 0


def json_ready(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(type(value).__name__)


def zh_period(value: str) -> str:
    return {
        "today": "今天",
        "yesterday": "昨天",
        "week": "本周",
        "last7": "近 7 天",
        "last14": "近 14 天",
        "month": "本月",
        "30d": "近 30 天",
        "last90": "近 90 天",
        "quarter": "本季度",
        "year": "今年",
        "all": "全部",
    }.get(value, value)


def zh_window(value: str) -> str:
    return {
        "today": "今天",
        "yesterday": "昨天",
        "this week": "本周",
        "last 7 days": "近 7 天",
        "last 14 days": "近 14 天",
        "this month": "本月",
        "last 30 days": "近 30 天",
        "last 90 days": "近 90 天",
        "this quarter": "本季度",
        "this year": "今年",
        "beginning": "开始",
        "now": "现在",
    }.get(value, value)


def fmt_int(value: int) -> str:
    return f"{int(value):,}"


def fmt_mtokens(value: int) -> str:
    return f"{Decimal(value) / Decimal('1000000'):.2f}M"


def fmt_money(value: Decimal | float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"${dec(value).quantize(Decimal('0.01'))}"


def print_summary(data: dict, period: str, start_label: str, end_label: str) -> None:
    total = data["total"]
    print(f"Codex usage: {period} ({start_label} -> {end_label})")
    print(f"Data source: {data.get('source_label', 'unknown')}")
    print(f"Records: {fmt_int(total['requests'])} {data.get('record_label', 'records')}")
    print(f"Tokens: {fmt_int(total['total_tokens'])} total | {fmt_int(total['input_tokens'])} input | {fmt_int(total['output_tokens'])} output")
    print(f"Cached input: {fmt_int(total['cache_read_tokens'])} ({total['cache_ratio'] * 100:.1f}%)")
    print(f"Estimated cost: {fmt_money(total['estimated_cost_usd'])}")
    print(f"Logged cost: {fmt_money(total['logged_cost_usd'])}")
    if data["unknown_tokens"] and data["unknown_as"]:
        print(f"Assumption: unknown model tokens ({fmt_int(data['unknown_tokens'])}) estimated as {data['unknown_as']}")
    if data["missing_price_models"]:
        print("Missing price for: " + ", ".join(data["missing_price_models"]))
    print()
    print("By model:")
    print(f"{'model':<18} {'req':>8} {'tokens':>12} {'input':>12} {'output':>10} {'cached':>12} {'est cost':>10}")
    for item in data["models"]:
        print(
            f"{item['model']:<18} {fmt_int(item['requests']):>8} "
            f"{fmt_mtokens(item['total_tokens']):>12} {fmt_mtokens(item['input_tokens']):>12} "
            f"{fmt_mtokens(item['output_tokens']):>10} {fmt_mtokens(item['cache_read_tokens']):>12} "
            f"{fmt_money(item['estimated_cost_usd']):>10}"
        )


def print_daily(data: dict) -> None:
    print(f"{'day':<12} {'req':>8} {'tokens':>12} {'input':>12} {'output':>10} {'cached':>12} {'est cost':>10}")
    for item in reversed(data["daily"]):
        print(
            f"{item['day']:<12} {fmt_int(item['requests']):>8} "
            f"{fmt_mtokens(item['total_tokens']):>12} {fmt_mtokens(item['input_tokens']):>12} "
            f"{fmt_mtokens(item['output_tokens']):>10} {fmt_mtokens(item['cache_read_tokens']):>12} "
            f"{fmt_money(item['estimated_cost_usd']):>10}"
        )


def render_dashboard(data: dict, period: str, start_label: str, end_label: str) -> str:
    payload = json.dumps(data, default=json_ready, ensure_ascii=False)
    title = f"Codex 用量 · {html.escape(zh_window(start_label))}"
    window_label = f"{zh_window(start_label)} → {zh_window(end_label)}"
    source_label = data.get("source_label", "未知")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --ink: #191713;
      --muted: #6f6a5d;
      --paper: #f8f4ea;
      --panel: rgba(255, 252, 242, .82);
      --line: rgba(39, 35, 28, .16);
      --green: #1c7c54;
      --blue: #2457a6;
      --red: #b7432f;
      --gold: #c89020;
      --shadow: 0 20px 60px rgba(52, 43, 28, .14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        linear-gradient(90deg, rgba(25,23,19,.045) 1px, transparent 1px) 0 0 / 28px 28px,
        linear-gradient(0deg, rgba(25,23,19,.035) 1px, transparent 1px) 0 0 / 28px 28px,
        linear-gradient(135deg, rgba(200,144,32,.18), transparent 36%, rgba(36,87,166,.12) 72%, transparent),
        var(--paper);
      font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Avenir Next, ui-sans-serif, sans-serif;
      font-variant-numeric: lining-nums tabular-nums;
      min-height: 100vh;
    }}
    .grain {{
      pointer-events: none;
      position: fixed;
      inset: 0;
      opacity: .20;
      mix-blend-mode: multiply;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.7' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.28'/%3E%3C/svg%3E");
    }}
    main {{ width: min(1240px, calc(100vw - 40px)); margin: 0 auto; padding: 34px 0 56px; position: relative; }}
    header {{
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 24px;
      align-items: end;
      margin-bottom: 22px;
    }}
    h1 {{
      margin: 0;
      max-width: 850px;
      font-family: "Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", Georgia, serif;
      font-size: clamp(44px, 7vw, 96px);
      line-height: .94;
      letter-spacing: 0;
    }}
    .subtitle {{ color: var(--muted); font-size: 15px; line-height: 1.5; max-width: 520px; }}
    .stamp {{
      border: 1px solid var(--line);
      background: rgba(255,255,255,.42);
      padding: 16px;
      box-shadow: var(--shadow);
      display: grid;
      gap: 8px;
      transform: rotate(-1deg);
    }}
    .stamp strong {{ font-family: "Songti SC", "Noto Serif CJK SC", Georgia, serif; font-size: 26px; font-variant-numeric: lining-nums tabular-nums; }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 22px 0;
    }}
    .pill {{
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      padding: 9px 12px;
      border-radius: 999px;
      font-size: 13px;
      box-shadow: 0 8px 18px rgba(52,43,28,.08);
    }}
    .grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }}
    .card {{
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
      border-radius: 8px;
      padding: 18px;
      backdrop-filter: blur(10px);
      min-width: 0;
      animation: rise .7s ease both;
    }}
    .metric {{ grid-column: span 3; min-height: 132px; }}
    .wide {{ grid-column: span 8; }}
    .side {{ grid-column: span 4; }}
    .full {{ grid-column: 1 / -1; }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
    .value {{ font-family: Avenir Next, "PingFang SC", ui-sans-serif, sans-serif; font-size: clamp(28px, 4vw, 46px); line-height: 1; margin-top: 12px; font-weight: 650; font-variant-numeric: lining-nums tabular-nums; }}
    .hint {{ color: var(--muted); margin-top: 10px; font-size: 13px; }}
    .bar-stack {{ display: grid; gap: 10px; margin-top: 16px; }}
    .bar-row {{ display: grid; grid-template-columns: 96px 1fr 158px; gap: 10px; align-items: center; font-size: 13px; color: var(--muted); }}
    .bar-track {{ height: 12px; background: rgba(25,23,19,.08); border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: inherit; transform-origin: left; animation: grow .9s ease both; }}
    .input {{ background: var(--green); }}
    .output {{ background: var(--red); }}
    .cached {{ background: var(--blue); }}
    .cost {{ background: var(--gold); }}
    .chart {{
      height: 310px;
      display: grid;
      grid-template-columns: repeat(var(--n), minmax(12px, 1fr));
      gap: 8px;
      align-items: end;
      padding-top: 18px;
    }}
    .day {{
      min-width: 0;
      display: grid;
      gap: 7px;
      align-items: end;
      height: 100%;
      position: relative;
    }}
    .col {{
      width: 100%;
      min-height: 2px;
      border-radius: 5px 5px 2px 2px;
      background: linear-gradient(180deg, var(--green), #86b879);
      position: relative;
      box-shadow: inset 0 1px rgba(255,255,255,.45);
    }}
    .col::after {{
      content: '';
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: var(--cache);
      background: linear-gradient(180deg, rgba(36,87,166,.72), rgba(36,87,166,.95));
      border-radius: inherit;
    }}
    .date-label {{ font-size: 10px; color: var(--muted); writing-mode: vertical-rl; justify-self: center; height: 42px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid var(--line); text-align: right; white-space: nowrap; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }}
    .legend {{ display: flex; gap: 14px; flex-wrap: wrap; margin-top: 12px; color: var(--muted); font-size: 12px; }}
    .swatch {{ width: 10px; height: 10px; display: inline-block; margin-right: 6px; border-radius: 50%; }}
    .note {{ border-left: 4px solid var(--gold); padding-left: 12px; color: var(--muted); font-size: 13px; line-height: 1.5; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(18px); }} to {{ opacity: 1; transform: none; }} }}
    @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
    @media (max-width: 900px) {{
      main {{ width: min(100vw - 24px, 760px); padding-top: 22px; }}
      header {{ grid-template-columns: 1fr; }}
      .metric, .wide, .side {{ grid-column: 1 / -1; }}
      .chart {{ gap: 4px; }}
      th, td {{ font-size: 12px; padding: 8px 6px; }}
    }}
  </style>
</head>
<body>
  <div class="grain"></div>
  <main>
    <header>
      <div>
        <h1>Codex 用量账本</h1>
        <p class="subtitle">统计 Codex 的本地用量；有 CC Switch 时读取代理请求日志，没有时读取 Codex 原生 session 日志。</p>
      </div>
      <div class="stamp">
        <span class="label">统计窗口</span>
        <strong>{html.escape(window_label)}</strong>
        <span class="hint">生成时间 {html.escape(data["generated_at"])}</span>
      </div>
    </header>
    <div class="toolbar">
      <span class="pill">数据源：{html.escape(source_label)}</span>
      <span class="pill">范围：仅 Codex</span>
      <span class="pill">周期：{html.escape(zh_period(period))}</span>
      <span class="pill">费用：估算</span>
    </div>
    <section class="grid" id="app"></section>
  </main>
  <script id="usage-data" type="application/json">{payload}</script>
  <script>
    const data = JSON.parse(document.getElementById('usage-data').textContent);
    const app = document.getElementById('app');
    const total = data.total;
    const fmt = new Intl.NumberFormat();
    const money = new Intl.NumberFormat(undefined, {{ style: 'currency', currency: 'USD', maximumFractionDigits: 2 }});
    const mtok = (n) => `${{(n / 1_000_000).toFixed(2)}}M`;
    const pct = (n) => `${{(n * 100).toFixed(1)}}%`;
    const cost = (n) => money.format(n || 0);
    const maxDaily = Math.max(...data.daily.map(d => d.total_tokens), 1);
    const maxModel = Math.max(...data.models.map(m => m.total_tokens), 1);

    function metric(label, value, hint) {{
      return `<article class="card metric"><div class="label">${{label}}</div><div class="value">${{value}}</div><div class="hint">${{hint}}</div></article>`;
    }}

    function composition() {{
      const inputShare = total.total_tokens ? total.input_tokens / total.total_tokens : 0;
      const outputShare = total.total_tokens ? total.output_tokens / total.total_tokens : 0;
      const cachedShare = total.input_tokens ? total.cache_read_tokens / total.input_tokens : 0;
      return `<article class="card side">
        <div class="label">Token 构成</div>
        <div class="bar-stack">
          ${{bar('输入', inputShare, `${{mtok(total.input_tokens)}} · ${{pct(inputShare)}} 总量`, 'input')}}
          ${{bar('输出', outputShare, `${{mtok(total.output_tokens)}} · ${{pct(outputShare)}} 总量`, 'output')}}
          ${{bar('缓存输入', cachedShare, `${{mtok(total.cache_read_tokens)}} · ${{pct(cachedShare)}} 输入`, 'cached')}}
        </div>
        <p class="note">缓存输入是输入 token 的一部分，单独列出是因为它通常按更低价格计费。</p>
      </article>`;
    }}

    function bar(name, ratio, text, cls) {{
      return `<div class="bar-row"><span>${{name}}</span><div class="bar-track"><div class="bar-fill ${{cls}}" style="width:${{Math.max(ratio * 100, 1)}}%"></div></div><span>${{text}}</span></div>`;
    }}

    function dailyChart() {{
      const days = data.daily.slice(-30);
      return `<article class="card wide">
        <div class="label">每日 Token 趋势</div>
        <div class="chart" style="--n:${{days.length}}">
          ${{days.map(d => {{
            const h = Math.max(2, d.total_tokens / maxDaily * 100);
            const cache = d.input_tokens ? d.cache_read_tokens / d.input_tokens * 100 : 0;
            return `<div class="day" title="${{d.day}} · ${{fmt.format(d.total_tokens)}} tokens · ${{cost(d.estimated_cost_usd)}}">
              <div class="col" style="height:${{h}}%; --cache:${{cache}}%"></div>
              <div class="date-label">${{d.day.slice(5)}}</div>
            </div>`;
          }}).join('')}}
        </div>
        <div class="legend">
          <span><i class="swatch input"></i>总输入</span>
          <span><i class="swatch cached"></i>其中缓存输入</span>
          <span><i class="swatch output"></i>输出见下方表格</span>
        </div>
      </article>`;
    }}

    function modelBars() {{
      return `<article class="card side">
        <div class="label">模型分布</div>
        <div class="bar-stack">
          ${{data.models.map(m => bar(m.model, m.total_tokens / maxModel, mtok(m.total_tokens), m.model === 'unknown' ? 'cost' : 'input')).join('')}}
        </div>
      </article>`;
    }}

    function modelTable() {{
      return `<article class="card full">
        <div class="label">模型明细</div>
        <table>
          <thead><tr><th>模型</th><th>记录/统计点</th><th>总量</th><th>输入</th><th>输出</th><th>缓存输入</th><th>估算费用</th></tr></thead>
          <tbody>
            ${{data.models.map(m => `<tr>
              <td>${{m.model}}</td><td>${{fmt.format(m.requests)}}</td><td>${{mtok(m.total_tokens)}}</td>
              <td>${{mtok(m.input_tokens)}}</td><td>${{mtok(m.output_tokens)}}</td><td>${{mtok(m.cache_read_tokens)}}</td>
              <td>${{cost(m.estimated_cost_usd)}}</td>
            </tr>`).join('')}}
          </tbody>
        </table>
      </article>`;
    }}

    function dayTable() {{
      return `<article class="card full">
        <div class="label">每日明细</div>
        <table>
          <thead><tr><th>日期</th><th>记录/统计点</th><th>总量</th><th>输入</th><th>输出</th><th>缓存输入</th><th>估算费用</th></tr></thead>
          <tbody>
            ${{data.daily.slice().reverse().map(d => `<tr>
              <td>${{d.day}}</td><td>${{fmt.format(d.requests)}}</td><td>${{mtok(d.total_tokens)}}</td>
              <td>${{mtok(d.input_tokens)}}</td><td>${{mtok(d.output_tokens)}}</td><td>${{mtok(d.cache_read_tokens)}}</td>
              <td>${{cost(d.estimated_cost_usd)}}</td>
            </tr>`).join('')}}
          </tbody>
        </table>
      </article>`;
    }}

    const unknownNote = data.unknown_tokens
      ? `<article class="card full"><p class="note">历史记录里有 ${{fmt.format(data.unknown_tokens)}} 个 token 的模型名是 unknown。本页面默认按 ${{data.unknown_as || '未计价'}} 估算；如果要严格只看已知模型价格，可运行 <code>codex-usage dashboard --unknown-as none</code>。</p></article>`
      : '';

    app.innerHTML = [
      metric('Token 总量', mtok(total.total_tokens), `${{fmt.format(total.requests)}} 个${{data.record_label || '统计点'}}`),
      metric('输入', mtok(total.input_tokens), `其中 ${{mtok(total.cache_read_tokens)}} 是缓存输入，占输入 ${{pct(total.cache_ratio)}}`),
      metric('输出', mtok(total.output_tokens), `占总 token ${{pct(total.output_ratio)}}`),
      metric('估算费用', cost(total.estimated_cost_usd), data.cost_note || `本地记录费用 ${{cost(total.logged_cost_usd)}}`),
      dailyChart(),
      composition(),
      modelBars(),
      data.source_note ? `<article class="card full"><p class="note">${{data.source_note}}</p></article>` : '',
      unknownNote,
      modelTable(),
      dayTable(),
    ].join('');
  </script>
</body>
</html>"""


def write_dashboard(data: dict, period: str, start_label: str, end_label: str, output: Path, should_open: bool) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_dashboard(data, period, start_label, end_label), encoding="utf-8")
    if should_open:
        webbrowser.open(output.resolve().as_uri())
    return output


def build_data(args: argparse.Namespace) -> tuple[dict, str, str]:
    start_ts, end_ts, start_label, end_label = period_bounds(args)
    unknown_as = None if args.unknown_as == "none" else args.unknown_as
    db_path = Path(args.db).expanduser()
    source = args.source

    if source == "auto":
        source = "cc-switch" if db_path.exists() else "codex"

    if source == "cc-switch":
        conn = connect(db_path)
        prices = load_prices(conn)
        rows = fetch_rows(conn, start_ts, end_ts)
        source_note = "数据来自 CC Switch 的本地 SQLite 请求日志，适合统计不同供应商切换后的 Codex 总用量。"
        cost_note = f"CC Switch 已记录费用 {fmt_money(sum((dec(row_value(row, 'logged_cost_usd')) for row in rows), Decimal('0')))}"
        record_label = "CC Switch 请求记录"
    elif source == "codex":
        prices = default_prices()
        rows = fetch_ccusage_rows(args, start_ts, end_ts)
        source_note = "数据来自 Codex 本地 session 日志，并由 @ccusage/codex 解析 token_count 事件；它不依赖 CC Switch，但不能区分具体供应商账单。"
        cost_note = "由 @ccusage/codex 基于本地 token 日志和模型价格估算"
        record_label = "日/模型统计点"
    else:
        raise SystemExit(f"Unknown data source '{source}'")

    data = summarize(rows, prices, unknown_as)
    data["period"] = args.period
    data["start"] = start_label
    data["end"] = end_label
    data["source"] = source
    data["source_label"] = SOURCE_LABELS[source]
    data["source_note"] = source_note
    data["cost_note"] = cost_note
    data["record_label"] = record_label
    return data, start_label, end_label


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    periods = {"today", "yesterday", "week", "last7", "last14", "month", "30d", "last90", "quarter", "year", "all"}
    if argv and argv[0] == "dashboard":
        dashboard_period = "month"
        rest = argv[1:]
        if rest and rest[0] in periods:
            dashboard_period = rest[0]
            rest = rest[1:]
        argv = [dashboard_period, "--dashboard", *rest]

    parser = argparse.ArgumentParser(description="Open a local Codex token and cost dashboard.")
    parser.add_argument("period", nargs="?", default="month", choices=["today", "yesterday", "week", "last7", "last14", "month", "30d", "last90", "quarter", "year", "all"])
    parser.add_argument("--since", help="Start date, YYYY-MM-DD. Overrides period.")
    parser.add_argument("--until", help="End date, YYYY-MM-DD inclusive. Overrides period.")
    parser.add_argument("--source", choices=["auto", "cc-switch", "codex"], default="auto", help="Data source. Default: auto, using CC Switch when available, otherwise Codex session logs via @ccusage/codex.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help=f"CC Switch sqlite db path. Default: {DEFAULT_DB}")
    parser.add_argument("--codex-home", default=str(DEFAULT_CODEX_HOME), help=f"Codex home path. Default: {DEFAULT_CODEX_HOME}")
    parser.add_argument("--ccusage-bin", default=os.environ.get("CCUSAGE_CODEX_BIN"), help="Path to an installed ccusage-codex executable. Default: search PATH, then fall back to npx.")
    parser.add_argument("--timezone", default=os.environ.get("TZ"), help="IANA timezone passed to @ccusage/codex for Codex session logs.")
    parser.add_argument("--ccusage-offline", action="store_true", help="Ask @ccusage/codex to use cached pricing data.")
    parser.add_argument("--daily", action="store_true", help="Show daily rows instead of model summary.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--dashboard", action="store_true", help="Generate and open the HTML dashboard.")
    parser.add_argument("--summary", action="store_true", help="Print a terminal summary instead of opening the dashboard.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help=f"Dashboard output path. Default: {DEFAULT_OUTPUT}")
    parser.add_argument("--no-open", action="store_true", help="Generate dashboard without opening a browser.")
    parser.add_argument("--unknown-as", default="gpt-5.5", help="Estimate rows whose model is unknown as this model. Use 'none' to leave them unpriced. Default: gpt-5.5")
    args = parser.parse_args(argv)

    dashboard_requested = args.dashboard or not args.summary and not args.json and not args.daily

    data, start_label, end_label = build_data(args)
    if dashboard_requested:
        output = write_dashboard(data, args.period, start_label, end_label, Path(args.output).expanduser(), should_open=not args.no_open)
        print(f"Dashboard written to {output}")
        return 0

    if args.json:
        print(json.dumps(data, default=json_ready, ensure_ascii=False, indent=2))
    elif args.daily:
        print_daily(data)
    else:
        print_summary(data, args.period, start_label, end_label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

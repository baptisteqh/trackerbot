# trackerbot

Personal stock and ETF portfolio tracker.

trackerbot reads positions from eToro (public API, read-only) or from a
local YAML file, computes technical indicators on prices, evaluates a set
of watch rules, produces a readable report, and optionally pushes alerts
to Telegram. A separate command fetches a daily market watch via the
Perplexity API. A local dashboard (Next.js + shadcn) consumes the same
data through a hardened HTTP endpoint.

The bot places no orders, modifies nothing on the broker side, and opens
no inbound port: all traffic is outbound-only.

Disclaimer: Personal project, built for my own use. Nothing in this
repository constitutes investment advice or a recommendation to buy or
sell any security. Past performance is not indicative of future results.
Use at your own risk.

## Security posture

- Publishable repository: no secret is or should ever be committed. All
  keys live in a local `.env` that `.gitignore` excludes. Only
  `.env.example` documents the expected variables.
- Private positions: `data/` and `portfolio.yaml` are gitignored. The
  shipped `portfolio.example.yaml` only contains fictional entries.
- No eToro write endpoint is implemented. Keys must be issued with the
  read-only scope `etoro-public:trade.real:read`.
- No Telegram webhook: the bot only calls `sendMessage`, it never listens.
- The local HTTP API (`trackerbot serve`) binds to `127.0.0.1` only and
  applies six defense-in-depth layers (see `src/trackerbot/api.py`).

## Installation

Requires Python 3.12.

```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The optional `[api]` extra installs FastAPI + uvicorn if you want to run
the local HTTP server without the full dev toolchain:

```
pip install -e ".[api]"
```

## Configuration

Copy `.env.example` to `.env` and fill in what you use:

```
cp .env.example .env
```

Variables:

- `ETORO_API_KEY`, `ETORO_USER_KEY`: keys issued from the verified eToro
  account, read-only. `ETORO_ENVIRONMENT` is `demo` or `real` (stay on
  `demo` until real-account reads have been validated).
- `PERPLEXITY_API_KEY`: Perplexity API key used by the `veille` command
  and by `notify --avec-veille`.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: BotFather token and the ID of
  the single authorized chat that receives messages.
- `PORTFOLIO_FILE`: path to the YAML portfolio used when no eToro key is
  provided. Defaults to `data/portfolio.yaml`.

To start without eToro, copy the example:

```
cp portfolio.example.yaml data/portfolio.yaml
```

### Activating eToro keys (read-only)

1. Verify the eToro account (ID + proof of address): the API is not
   available before KYC validation.
2. From `https://www.etoro.com/settings/api`, generate a key pair with
   only the `etoro-public:trade.real:read` scope. No write scope is
   needed; none is used by the bot.
3. Fill `ETORO_API_KEY` and `ETORO_USER_KEY` in `.env`. Keep
   `ETORO_ENVIRONMENT=demo` until real-account reads have been validated.
4. Run `trackerbot doctor` to confirm the keys are read and the remote
   portfolio responds.

If eToro answers `401`, the key likely lacks the right scopes or the
account is not verified. The bot never writes to `.env`; if in doubt,
revoke the key from the eToro UI and reissue it.

## Usage

All commands live behind the `trackerbot` executable.

| Command                               | Effect                                                             |
| ------------------------------------- | ------------------------------------------------------------------ |
| `trackerbot status`                   | Full report in the console (positions + metrics + signals).        |
| `trackerbot status --sans-cotations`  | Same report, without calling Yahoo Finance.                        |
| `trackerbot status --benchmark SPY`   | Adds portfolio beta against a benchmark (SPY by default).          |
| `trackerbot status --fondamentaux`    | Adds PER, margin, D/E, ROE and a valuation score per position.     |
| `trackerbot watch`                    | Sends to Telegram only if there is an ATTENTION or ALERT signal.   |
| `trackerbot notify`                   | Sends the full report to Telegram.                                 |
| `trackerbot notify --avec-veille`     | Same, appending the daily Perplexity market watch.                 |
| `trackerbot veille`                   | Prints the daily Perplexity market watch.                          |
| `trackerbot doctor`                   | Verifies configuration and integration access.                     |
| `trackerbot serve`                    | Starts the local HTTP API (`127.0.0.1:8000`) for the dashboard.    |

Add `-v` to enable DEBUG logs.

## Watch rules

Rules live in `src/trackerbot/signals.py`. They are pure functions and
come in three levels: `info`, `attention`, `alerte`. The `watch` command
only notifies on the two most urgent levels.

Available rules:

- Stop-loss hit or approaching.
- Take-profit reached.
- Marked pullback from the recent high.
- Intraday move beyond a threshold.
- Moving-average crossover.
- RSI in overbought or oversold zone.
- Unusual latent gain or loss.

Thresholds are grouped in the `Seuils` dataclass and can be tuned without
touching rule code.

## Portfolio metrics

Beyond per-position indicators, the report shows a portfolio-level block:
annualized Sharpe ratio (risk-free rate default 4%), annualized volatility
and return, max drawdown, HHI concentration index, largest-position
weight, and beta against a benchmark (SPY by default, tunable via
`--benchmark`). All formulas live as pure functions in
`src/trackerbot/metrics.py`.

## Fundamentals and valuation score

`trackerbot status --fondamentaux` fetches minimal fundamentals via Yahoo
(yfinance): PER, PB, net margin, debt-to-equity ratio, ROE, dividend
yield, revenue growth. A 0–7 Graham/Buffett-lite score
(`valuation.py`) rewards the criteria met: PER < 15, PB < 1.5, margin >
10%, D/E < 1, ROE > 10%, growth > 5%, dividend paid. Thresholds live in
`SeuilsValorisation` and can be tuned without touching the rules.

The option is opt-in because each ticker triggers an extra network call.

## Local dashboard

A Next.js 16 + shadcn dashboard lives in `dashboard/`. Design tokens and
component brief are documented in `dashboard/DESIGN.md`.

To run it locally:

```
# terminal 1 — backend
trackerbot serve

# terminal 2 — frontend
cd dashboard
npm install
npm run dev
```

Then open `http://localhost:3000`. If the backend is down the dashboard
falls back to a hardcoded demo payload so you can preview the UI without
running the API.

### API surface

Two endpoints (see `src/trackerbot/api.py` for the full threat model):

- `GET /rapport` — reads the last successful report from cache.
  Idempotent, no network side-effect. Safe against `<img>`-based CSRF.
- `POST /refresh` — recomputes the report according to `{"scope":
  "quotes" | "veille" | "fundamentals" | "all"}`. Requires a whitelisted
  `Origin`, a valid `X-XSRF-Token` (double-submit against the `xsrf-token`
  cookie set by `GET /csrf`), and a per-scope rate limit is enforced.

The server refuses any `--host` other than `127.0.0.1` / `localhost` as a
defense-in-depth measure.

## Structure

```
src/trackerbot/
  config.py         reads environment variables
  models.py         Position, Cotation, Signal, Niveau
  indicators.py     SMA, RSI, crossovers, volatility (pure functions)
  metrics.py        Sharpe, drawdown, HHI, beta (pure functions)
  signals.py        watch rules
  fundamentals.py   Yahoo fundamentals
  valuation.py      valuation score (pure function)
  market.py         quote access via yfinance
  research.py       Perplexity market watch
  storage.py        SQLite history + JSON cache of the latest report
  payload.py        Rapport -> dashboard JSON (stdlib only)
  api.py            FastAPI HTTP API (opt-in extra)
  report.py         report aggregation
  cli.py            trackerbot commands
  sources/          local file, eToro
  notify/           Telegram sender
dashboard/          Next.js + shadcn app consuming the bot data
```

## Tests

```
pytest
```

Tests are entirely offline: no network calls. They cover indicators,
models, rules, configuration, report, sources, storage, API, and
valuation.

Additional checks:

```
ruff check .
mypy
```

## Limits

- yfinance is an unofficial Yahoo Finance client. It breaks from time to
  time: all quote-fetching logic lives in `market.py`, and the report
  gracefully degrades positions whose quote is missing.
- Technical signals are not investment advice. The bot describes what is
  happening in the market; it does not tell you what to do.

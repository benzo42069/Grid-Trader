# Grid-Trader (Safety-First Spot Grid Engine MVP)

This repository implements a **safety-first** crypto spot grid trading engine MVP with:

- one process, one strategy instance
- one exchange + one spot symbol
- static neutral grid only (arithmetic or geometric spacing)
- limit + GTC only
- post-only default true
- strict config schema and semantic validation
- mandatory reconciliation before placement
- local SQLite journal + snapshot persistence
- risk-authoritative stop flow

Default strategy templates are now:
- symbol: `XRP/USD` (human-facing canonical form)
- mode: `live` for the live example, with explicit arming required
- paper mode remains available via `config/examples/paper_spot_grid.json`

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
python -m app.main --config config/examples/paper_spot_grid.json
```

## Live mode safety warning

Live mode is intentionally guarded:

- `runtime.mode` must be `live`
- `runtime.arm_live_trading` must be `true`
- env var named by `exchange.credentials_env` must be present

If any validation/reconciliation/risk check fails, the engine fails closed and stops placing orders.

## Repository layout

- `config/strategy.schema.json`: schema `1.0.0`
- `src/domain/*`: exchange-agnostic enums/models/errors/ids
- `src/config/*`: loader + semantic validator + typed normalizer
- `src/exchange/*`: adapter interface, normalization rules, mock adapter
- `src/ledger/*`: balances, inventory (avg cost), pnl
- `src/strategy/*`: grid math/planner/engine/state machine
- `src/execution/*`: order manager, fill processor, reconciliation
- `src/risk/*`: rules, manager, kill switch
- `src/persistence/*`: sqlite journal and snapshots
- `tests/*`: unit and integration coverage for MVP flows

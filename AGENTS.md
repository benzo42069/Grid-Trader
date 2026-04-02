Agents Entry Guide: This repository implements a spot crypto grid trading engine with the following characteristics. Each component must be understood before contributing code.

Purpose: Automate a grid of limit orders for one trading symbol on one exchange. The strategy buys low and sells high within fixed bounds, capturing profit from small price swings.

Architecture: The code is modular:

config/: JSON schema and loader.
exchange/: Abstract ExchangeAdapter interface plus a mock implementation for tests.
strategy/: The GridStrategy engine that places orders and handles fills.
risk/: The RiskManager enforcing drawdown and stale-data limits.
state/: Persistence (StateStore) for snapshots/journals.
main.py: Orchestrates initialization, main loop, and shutdown.
tests/: Unit/integration tests.
Configuration: All parameters (exchange, symbol, grid bounds, order count, sizing, risk thresholds) come from a JSON config file. The schema (config/schema.json) strictly validates types, ranges, and required fields. No API keys or secrets are stored in this file; credentials are provided separately (see below).

State and Persistence:

The bot maintains in-memory state (open orders, inventory, PnL) and periodically writes a snapshot to local storage.
On startup or reconnection, it loads the last snapshot and reconciles with the live exchange state. This guarantees restart safety.
Order placement is idempotent: each order has a unique clientOrderId. This prevents duplication if retries occur.
Exchange Adapters:

Code interacts with exchanges only via the ExchangeAdapter interface. Real exchanges must be implemented separately.
The default adapter is a mock for unit testing; it does not execute real trades.
In live mode, the real adapter should handle rate limits, ticker subscriptions, and API errors. Do not embed any exchange-specific logic in the core strategy.
Risk & Safety Rules: Non-negotiable constraints are coded in risk/:

Exposure caps: e.g. maximum inventory imbalance, max open orders.
Drawdown limits: daily loss and peak-to-valley drawdown thresholds.
Data health: if market data or order updates stop (timeout), the bot must cancel all orders and halt.
Error handling: Unexpected API responses or exceptions trigger an emergency stop.
The engine must fail-safe: on any violation, cancel orders (or halt in simulation mode) rather than continue risky trading.
Trading Behavior (MVP):

Static neutral grid around a center price (no drift).
Post-only limit orders ensure maker fees and predictable fills. Only if explicitly enabled may taker orders execute (e.g. for manual emergency flatten).
All order sizes and spacing are configured, but by default use equal-interval spacing and equal-notional sizing.
No leveraged or perpetual positions in MVP; margin and funding are entirely out of scope.
No auto profit-taking: the bot closes positions only via the grid logic or emergency stop.
Build and Deployment:

Follow the phased build order (config → data models → exchange adapter → strategy → risk → persistence → main loop → tests) to incrementally verify correctness.
Use type checking (mypy or similar) and linting. Ensure the code is PEP8-compliant.
For local development, default to “paper” mode (mock exchange). Use environment flags or a dry-run config flag for live simulation vs. paper.
Testing:

Unit tests are required for all critical logic (config validation, grid math, risk triggers). Integration tests should simulate a sequence of fills and verify state transitions.
Do not skip testing: the coding agents must include tests as part of MVP.
Deferred/Planned Features:

Futures/perpetual support, multi-symbol orchestration, adaptive grid adjustment, and UI dashboards are outside MVP. They should not appear in the initial codebase.
Agents should explicitly avoid implementing any adaptive trading logic beyond what is specified.
Coding Style:

Prefer clarity and explicitness. Use descriptive names and clear function contracts.
Raise exceptions with informative messages on error conditions (catch these at the top level).
Log meaningful events (order placed, filled, stop triggered) at INFO level; use DEBUG for detailed tracing.
Ensure the code is modular: each class has one responsibility and minimal side effects.
Invariants to Preserve:

Total capital used should never exceed allocation.
Inventory + locked capital accounting must always balance.
Open orders in memory must match what is on the exchange (after each reconcile).
No trading occurs after risk manager signals a stop.
Refer back to this AGENTS.md frequently. It defines the non-negotiable rules and scope. If the code behaves outside these boundaries, treat it as a defect.

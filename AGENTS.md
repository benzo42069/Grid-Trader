# AGENTS.md

## Purpose

This repository contains a safety-first crypto grid trading engine.

The MVP is deliberately narrow:

- one process
- one strategy instance
- one exchange
- one spot symbol
- paper trading first
- live spot second
- static neutral grid only

This is not a portfolio manager, not a multi-symbol system, not a futures engine, and not a research playground in MVP.

The engine exists to do one job safely:

- load a strictly validated strategy configuration
- connect to one normalized spot exchange adapter
- reconcile state before trading
- place and manage a bounded static grid of limit orders
- process fills deterministically
- track balances, locked funds, inventory, fees, and realized PnL
- persist journaled state
- recover safely after restart or reconnect
- stop trading when uncertainty appears

If behavior is ambiguous, stale, unsafe, or inconsistent with exchange state, the system must fail closed.

---

## MVP Scope

### Included

- one process = one strategy instance
- one strategy instance = one exchange + one spot symbol
- static neutral grid
- arithmetic or geometric spacing
- limit orders only
- GTC only
- post-only default true
- quote-allocation sizing
- strict config/schema validation before startup
- paper trading mode
- live spot mode
- local SQLite persistence
- startup recovery and reconciliation
- reconnect reconciliation
- cancel-only emergency stop
- structured logging
- unit tests and integration tests

### Excluded

Do not add these to MVP:

- futures or perpetuals
- leverage or margin
- hedge mode
- reduce-only
- funding or liquidation logic
- multi-symbol orchestration
- multi-strategy portfolio allocation
- adaptive or trailing grids
- volatility-driven reconfiguration
- market orders as routine behavior
- automatic flattening
- UI/dashboard
- hot-reload of live config
- distributed workers or service decomposition
- external DB dependency
- full backtesting framework as a required subsystem

Deferred features must not complicate MVP code paths.

---

## Non-Negotiable Safety Rules

1. **Fail closed on uncertainty.**
   - Unknown exchange state, stale market data, stale private stream, reconciliation mismatch, duplicate client order ID detection, repeated rejects, or persistence failure must stop trading.
   - Stopping means:
     - block new orders
     - attempt cancel of managed open orders
     - persist stop reason and final snapshot
     - transition to `STOPPED`

2. **No live trading without passing all startup gates.**
   - schema validation
   - semantic validation
   - metadata/constraints load
   - precision and notional normalization
   - successful reconciliation
   - explicit live arming
   - credentials present in environment

3. **No silent retries that can duplicate orders.**
   - Every order intent must have a deterministic client order ID.
   - Retry logic must distinguish:
     - request definitely not sent
     - request definitely failed
     - request outcome ambiguous
   - If outcome is ambiguous, reconcile before any replacement attempt.

4. **No exchange-specific behavior in strategy logic.**
   - Exchange rules belong in adapters and constraints layers.
   - Strategy code only consumes normalized domain models.

5. **No unsafe normalization.**
   - If exchange normalization causes level collapse, min-notional failure, or material distortion of intended grid economics, reject config or halt safely.
   - Never silently “fix” a risky plan.

6. **No accounting shortcuts.**
   - Use Decimal everywhere for money-sensitive values.
   - Track:
     - free quote
     - locked quote
     - free base
     - locked base
     - realized pnl
     - fees
     - average cost basis for base inventory
   - Never spend or reserve beyond free balances.

7. **No continued operation with stale inputs.**
   - Market data freshness and private stream freshness are separate health checks.
   - Either timeout is sufficient to stop trading.

8. **No fill double-processing.**
   - Fills must be processed exactly once from the engine’s perspective.
   - Duplicate fill events must be detected and ignored safely.

---

## Final Locked Decisions

### Hard-Coded

These are authoritative for MVP and should not be changed casually:

- Python 3.11+
- one async process per strategy instance
- one symbol per process
- spot-only live MVP
- static neutral grid only
- limit orders only
- GTC only
- post-only default = true
- cancel-only emergency stop
- local SQLite for snapshots, journal, and managed-order mappings
- Decimal for prices, quantities, fees, balances, and pnl
- average cost basis inventory accounting
- strict startup reconciliation required
- strict fail-closed behavior on ambiguous order state
- no automatic flattening
- no live config mutation
- live mode requires explicit arm flag
- schema version = `1.0.0`

### Configurable

These belong in config and validation:

- exchange adapter name
- symbol
- spacing type
- lower and upper bounds
- level count
- anchor/reference price mode
- total quote allocation
- per-level sizing mode
- post-only toggle when exchange support allows it
- stale market/private thresholds
- drawdown and daily loss thresholds
- max inventory base
- max reject streak
- max reconciliation mismatches
- snapshot interval
- logging verbosity
- paper vs live mode

### Deferred

These may be added later, but must not leak into MVP logic:

- futures support
- leverage and liquidation math
- funding accounting
- adaptive bounds
- volatility gates
- multi-symbol orchestration
- portfolio allocator
- automatic flattening playbooks
- advanced execution tactics
- dashboards
- external persistence systems
- backtest/research suite

---

## Architectural Boundaries

### Config Layer

Responsible for:
- loading JSON
- validating against schema
- semantic validation
- applying safe defaults
- producing normalized typed config objects

Must reject:
- impossible bounds
- unsupported enum combinations
- live mode without required safety fields
- levels that cannot satisfy exchange constraints
- unsafe normalization outcomes

Must not:
- contain secrets
- place orders
- hide risky assumptions

### Domain Layer

Responsible for:
- enums
- typed models
- deterministic IDs
- domain events
- domain error classes

Must remain exchange-agnostic.

### Exchange Layer

Responsible for:
- REST/private API access
- symbol metadata and constraints
- normalized order/fill/account responses
- error classification
- market/private stream integration
- idempotent order submission plumbing

Must not:
- contain strategy logic
- leak raw payloads outside the adapter boundary

### Market Data Layer

Responsible for:
- best bid/ask updates
- timestamps
- freshness checks
- last-known market snapshot

Must not:
- place orders
- mutate strategy state directly

### Execution Layer

Responsible for:
- order intent submission
- cancel flow
- in-flight tracking
- duplicate action prevention
- reconciliation participation
- fill ingestion handoff

This is where idempotency discipline must be strict.

### Strategy Layer

Responsible for:
- grid level generation
- deciding which intended orders should exist
- reacting to fills with valid counter-order scheduling
- honoring bounds and exposure constraints
- interacting through normalized abstractions only

Must not:
- know exchange raw formats
- bypass risk or execution guards

### Risk Layer

Responsible for:
- pre-trade checks
- runtime health checks
- exposure checks
- drawdown/daily loss checks
- stale stream checks
- reject storm detection
- kill switch trigger

Risk is authoritative. If risk says stop, the system stops.

### Ledger Layer

Responsible for:
- balance accounting
- locked funds accounting
- inventory accounting
- realized pnl
- fee accumulation
- drift visibility

Ledger correctness matters more than optimization.

### Persistence Layer

Responsible for:
- event journal
- snapshots
- managed-order mapping persistence
- recovery load
- crash-safe writes

Persistence failures are fatal in live mode.

---

## Runtime State Machine

Use explicit states. Do not replace this with scattered booleans.

Required states:

- `BOOTSTRAP`
- `VALIDATING_CONFIG`
- `LOADING_METADATA`
- `RECONCILING`
- `ARMED_PAPER`
- `ARMED_LIVE`
- `PLACING_INITIAL_GRID`
- `RUNNING`
- `PAUSED_RISK`
- `STOPPING`
- `STOPPED`
- `ERROR`

Required transition rules:

- startup must pass through validation and reconciliation before any order placement
- live mode must not place orders until `ARMED_LIVE`
- paper mode must not skip the same core startup gates
- stale data, reject storm, or reconciliation ambiguity must trigger stop flow
- `STOPPING` attempts cancel-only cleanup, persists final state, then becomes `STOPPED`
- severe ambiguity may enter `ERROR` before `STOPPING`
- all transitions must be logged and journaled

---

## Config and Schema Rules

### Schema Principles

- nested schema, not flat config
- versioned with `schema_version`
- strict enums
- defaults only for low-risk fields
- required fields for anything affecting execution, risk, or capital
- no secrets in config

Required top-level sections:

- `meta`
- `runtime`
- `exchange`
- `market`
- `strategy`
- `risk`
- `persistence`
- `telemetry`

### Secrets

API secrets must never be stored in strategy config.

Use environment variables referenced by config. If live mode is requested and credentials are missing, fail at startup.

### JSON Comments

Do not invent JSON-with-comments formats.

Use:
- schema descriptions
- README documentation
- example configs

---

## Order and Fill Invariants

These invariants must always hold:

- every order intent has a deterministic client order ID
- no two active managed orders share the same client order ID
- every local open order has known state or is under reconciliation
- buy orders never reserve more quote than available free quote
- sell orders never reserve more base than available free base
- all submitted prices and quantities are normalized before submission
- fills are processed exactly once
- counter-order placement happens only after the fill is durably recorded or safely journaled
- no new orders are placed after kill switch activation

If an invariant breaks, stop trading and treat it as a defect.

---

## Recovery and Reconciliation Rules

This is one of the highest-risk areas.

Required behavior:

1. Load last persisted snapshot and journal.
2. Fetch current balances and open orders from exchange.
3. Compare local intended state vs exchange actual state.
4. Resolve only through explicit rules:
   - known locally and known remotely: sync and continue
   - known locally but absent remotely: verify via history when available
   - known remotely but unknown locally: quarantine as orphan, cancel if safely attributable, otherwise stop
   - ambiguous status: count mismatch and stop if threshold exceeded
5. Only after reconciliation may the engine place missing intended orders.

Rules:
- never assume missing open orders were canceled cleanly
- never place replacements until ambiguity is resolved
- reconciliation outcomes must be logged and journaled
- restart/reconnect behavior must be integration-tested

---

## Required Build Order

Agents must follow this order:

1. domain models and enums
2. config schema and loader
3. semantic validation and normalizer
4. exchange base interface and mock adapter
5. ledger/accounting primitives
6. grid math and planner
7. order manager and fill processor
8. reconciliation subsystem
9. risk manager and kill switch
10. persistence store
11. runtime state machine and bootstrap
12. paper-mode integration tests
13. optional live adapter wiring
14. live-mode safety tests

Do not start with live adapter work.

---

## Testing Expectations

### Unit

Minimum required:
- schema validation success/failure
- semantic validation edge cases
- arithmetic grid generation
- geometric grid generation
- tick/step/min-notional normalization
- client order ID determinism
- locked funds accounting
- realized pnl and fee accounting
- risk threshold triggers
- stale market/private stream triggers
- reconciliation decision logic

### Integration

Minimum required:
- paper startup and initial grid placement
- buy fill -> ledger update -> counter sell intent
- sell fill -> ledger update -> counter buy intent
- restart with snapshot recovery
- reject storm -> stop
- stale stream -> stop
- duplicate fill protection

### Before Any Live Attempt

Must verify manually:
- symbol metadata mapping
- actual exchange rounding and min-notional behavior
- post-only behavior
- cancel flow
- recovery after forced process kill
- logs and snapshots are sufficient for reconstruction

---

## Coding Style Expectations

- explicit typing throughout
- small composable classes and functions
- Decimal for monetary logic
- centralized enums and error classes
- no hidden globals
- no network calls in constructors
- no long mixed-responsibility functions
- no swallowed exceptions
- structured logs for order/fill/risk/reconcile/state events
- keep exchange payload translation isolated
- write tests alongside implementation, not after

---

## What Not To Change Casually

These are high-risk areas:

- client order ID scheme
- ledger accounting logic
- reconciliation rules
- runtime state transitions
- emergency stop behavior
- config schema fields affecting risk or capital
- exchange constraint normalization
- persistence format and recovery semantics

Any change here requires tests and explicit review.

---

## Guidance for Deferred Features

When adding deferred features later:

- extend through new modules, not MVP shortcuts
- do not contaminate spot code paths with futures assumptions
- do not weaken fail-closed behavior
- do not add adaptive logic until static-grid invariants are proven stable
- add new config sections with schema version updates
- document persistence or migration changes explicitly

---

## Final Instruction to Agents

This is a safety-first trading system.

Correctness, reconciliation, and controlled failure matter more than feature count.

When forced to choose, prefer:

1. safety
2. correctness
3. exchange realism
4. restart/recovery robustness
5. implementation simplicity
6. extensibility

If a behavior is uncertain, stop trading rather than guessing.

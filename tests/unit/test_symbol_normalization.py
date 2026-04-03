from config.loader import load_and_validate_config


def test_symbol_normalization_from_dash(tmp_path):
    cfg_path = tmp_path / "dash_symbol.json"
    cfg_path.write_text(
        """
{
  "meta": {"schema_version": "1.0.0"},
  "runtime": {"mode": "paper", "arm_live_trading": false},
  "exchange": {"name": "mock_spot", "credentials_env": "MOCK_CREDENTIALS"},
  "market": {"symbol": "xrp-usd", "price_source": "mock_ticker"},
  "strategy": {
    "grid_type": "static_neutral",
    "spacing_type": "arithmetic",
    "lower_price": "0.40",
    "upper_price": "0.80",
    "num_levels": 6,
    "anchor_price_mode": "midpoint",
    "total_quote_allocation": "600",
    "per_level_sizing_mode": "equal_quote",
    "post_only": true,
    "time_in_force": "GTC"
  },
  "risk": {
    "max_inventory_base": "1000",
    "max_drawdown_pct": "20",
    "max_daily_loss_quote": "300",
    "max_reject_streak": 3,
    "max_open_orders": 8,
    "stale_market_data_seconds": 20,
    "stale_private_stream_seconds": 20,
    "max_reconciliation_mismatches": 2
  },
  "persistence": {"sqlite_path": "./grid_trader.db", "snapshot_interval_seconds": 30},
  "telemetry": {"log_level": "INFO"}
}
""".strip()
    )
    cfg = load_and_validate_config(cfg_path, "config/strategy.schema.json", env={})
    assert cfg.market.symbol == "XRP/USD"
    assert cfg.market.venue_symbol == "XRP-USD"

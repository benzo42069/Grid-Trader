from decimal import Decimal

from app.bootstrap import bootstrap_engine
from domain.enums import EngineState, Side
from domain.models import FillEvent


def test_paper_startup_and_initial_grid(tmp_path):
    db = tmp_path / "test.db"
    cfg = "config/examples/paper_spot_grid.json"
    schema = "config/strategy.schema.json"

    engine = bootstrap_engine(cfg, schema, env={"MOCK_CREDENTIALS": "ok"})
    engine.cfg.persistence.sqlite_path = str(db)
    engine.bootstrap()
    assert engine.state.state == EngineState.RUNNING
    assert len(engine.adapter.fetch_open_orders(engine.cfg.market.symbol)) > 0


def test_buy_fill_counter_path(tmp_path):
    engine = bootstrap_engine("config/examples/paper_spot_grid.json", "config/strategy.schema.json", env={"MOCK_CREDENTIALS": "ok"})
    engine.bootstrap()
    first = engine.adapter.fetch_open_orders(engine.cfg.market.symbol)[0]
    fill = FillEvent("fill-1", engine.cfg.market.symbol, first.client_order_id, first.side, first.price, Decimal("0.001"), Decimal("0.01"))
    engine.adapter.inject_fill(fill)
    engine.on_private_updates()
    side = engine.schedule_counter_order(fill)
    assert side == (Side.SELL if fill.side == Side.BUY else Side.BUY)


def test_duplicate_fill_ignored(tmp_path):
    engine = bootstrap_engine("config/examples/paper_spot_grid.json", "config/strategy.schema.json", env={"MOCK_CREDENTIALS": "ok"})
    engine.bootstrap()
    first = engine.adapter.fetch_open_orders(engine.cfg.market.symbol)[0]
    fill = FillEvent("fill-dup", engine.cfg.market.symbol, first.client_order_id, first.side, first.price, Decimal("0.001"), Decimal("0.01"))
    assert engine.fill_processor.process(fill) is True
    assert engine.fill_processor.process(fill) is False


def test_reject_storm_stop():
    engine = bootstrap_engine("config/examples/paper_spot_grid.json", "config/strategy.schema.json", env={"MOCK_CREDENTIALS": "ok"})
    engine.bootstrap()
    for _ in range(engine.cfg.risk.max_reject_streak):
        reason = engine.risk.register_reject()
    assert reason is not None


def test_stale_stream_stop():
    engine = bootstrap_engine("config/examples/paper_spot_grid.json", "config/strategy.schema.json", env={"MOCK_CREDENTIALS": "ok"})
    engine.bootstrap()
    engine.market_data.cache.last = None
    engine.run_risk_checks()
    assert engine.state.state == EngineState.STOPPED

"""GEM Logic — Python port of the TradingView GEM divergence + confirmation strategy."""

from src.gem.analyzer import GEMAnalyzer
from src.gem.backtest import BacktestConfig, BacktestResult, run_gem_backtest, run_backtest_batch
from src.gem.config import GEMConfig
from src.gem.dashboard import TFDashboardState, compute_dashboard_series, compute_tf_dashboard
from src.gem.models import GEMAnalysis

__all__ = [
    "GEMAnalyzer",
    "BacktestConfig",
    "BacktestResult",
    "GEMConfig",
    "GEMAnalysis",
    "TFDashboardState",
    "compute_dashboard_series",
    "compute_tf_dashboard",
    "run_gem_backtest",
    "run_backtest_batch",
]

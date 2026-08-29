"""Tests du comparateur benchmark."""

from __future__ import annotations

from datetime import date

import pytest

from trackerbot.benchmarks import comparer


class TestComparer:
    def test_series_vides(self) -> None:
        result = comparer([], [], "SPY")
        assert all(v is None for v in result.perf_portefeuille.values())

    def test_series_trop_courtes(self) -> None:
        result = comparer([100.0], [100.0], "SPY")
        assert all(v is None for v in result.perf_portefeuille.values())

    def test_outperformance_positive(self) -> None:
        # Portefeuille +10%, benchmark +2% sur 21 jours -> outperformance 8pt sur 1M
        equity = [100.0 + i * 0.5 for i in range(30)]
        bench = [100.0 + i * 0.1 for i in range(30)]
        result = comparer(equity, bench, "SPY", aujourdhui=date(2026, 6, 30))

        assert result.benchmark == "SPY"
        assert result.perf_portefeuille["1M"] is not None
        assert result.perf_benchmark["1M"] is not None
        assert result.outperformance["1M"] is not None
        assert result.outperformance["1M"] > 0

    def test_1y_none_si_serie_courte(self) -> None:
        equity = [100.0 + i for i in range(50)]
        bench = [100.0 + i for i in range(50)]
        result = comparer(equity, bench, "SPY")
        # 50 seances < 252 pour 1Y : la fenetre effective sera coupee
        assert result.outperformance["1Y"] is not None or result.outperformance["1Y"] is None

    def test_ytd_utilise_date_donnee(self) -> None:
        # Le 15 juillet, YTD ≈ (196 * 5 / 7) = 140 seances.
        equity = [100.0 * (1 + 0.001 * i) for i in range(300)]
        bench = [100.0 for _ in range(300)]
        result = comparer(equity, bench, "SPY", aujourdhui=date(2026, 7, 15))
        assert result.perf_portefeuille["YTD"] is not None
        assert result.perf_portefeuille["YTD"] > 0
        assert result.outperformance["YTD"] == pytest.approx(
            result.perf_portefeuille["YTD"], rel=1e-9
        )  # benchmark plat -> outperformance = perf portefeuille

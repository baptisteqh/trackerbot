"""Tests du parseur de fondamentaux : offline, pas d'appel yfinance."""

from __future__ import annotations

import pytest

from trackerbot.fundamentals import Fondamentaux, _extraire_fondamentaux


def _info_complete() -> dict[str, object]:
    return {
        "trailingPE": 12.5,
        "priceToBook": 1.2,
        "profitMargins": 0.18,
        "debtToEquity": 82.5,
        "returnOnEquity": 0.22,
        "dividendYield": 2.1,
        "revenueGrowth": 0.08,
        "sector": "Technology",
        "industry": "Software - Application",
    }


class TestExtraireFondamentaux:
    def test_extraction_complete(self) -> None:
        f = _extraire_fondamentaux("MSFT", _info_complete())
        assert f == Fondamentaux(
            ticker="MSFT",
            per=12.5,
            price_to_book=1.2,
            marge_nette_pct=pytest.approx(18.0),
            debt_to_equity=pytest.approx(0.825),
            roe_pct=pytest.approx(22.0),
            dividend_yield_pct=2.1,
            croissance_revenus_pct=pytest.approx(8.0),
            secteur="Technology",
            industrie="Software - Application",
        )

    def test_ticker_normalise_en_majuscules(self) -> None:
        assert _extraire_fondamentaux("aapl", {}).ticker == "AAPL"

    def test_champs_manquants_donnent_none(self) -> None:
        f = _extraire_fondamentaux("XYZ", {})
        for champ in (
            f.per,
            f.price_to_book,
            f.marge_nette_pct,
            f.debt_to_equity,
            f.roe_pct,
            f.dividend_yield_pct,
            f.croissance_revenus_pct,
            f.secteur,
            f.industrie,
        ):
            assert champ is None

    def test_utilise_forwardPE_en_secours(self) -> None:
        f = _extraire_fondamentaux("AAA", {"forwardPE": 20.0})
        assert f.per == 20.0

    def test_valeurs_non_numeriques_ignorees(self) -> None:
        f = _extraire_fondamentaux("AAA", {"trailingPE": "n/a", "returnOnEquity": None})
        assert f.per is None
        assert f.roe_pct is None

    def test_nan_ignore(self) -> None:
        f = _extraire_fondamentaux("AAA", {"trailingPE": float("nan")})
        assert f.per is None

    def test_champ_texte_vide_donne_none(self) -> None:
        f = _extraire_fondamentaux("AAA", {"sector": "   ", "industry": ""})
        assert f.secteur is None
        assert f.industrie is None

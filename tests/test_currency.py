"""Tests inference de devise + agregation d'exposition par devise."""

from __future__ import annotations

from datetime import date

import pytest

from trackerbot.currency import (
    DEVISE_DEFAUT,
    ExpositionDevise,
    deviner_devise,
    exposition_par_devise,
)
from trackerbot.models import Cotation, Position
from trackerbot.report import construire_rapport
from trackerbot.signals import Seuils, evaluer_portefeuille


class TestDevinerDevise:
    def test_ticker_us_sans_suffixe_est_usd(self) -> None:
        assert deviner_devise("AAPL") == "USD"
        assert deviner_devise("MSFT") == "USD"

    def test_paris_est_euro(self) -> None:
        assert deviner_devise("MC.PA") == "EUR"
        assert deviner_devise("air.pa") == "EUR"  # case-insensitive

    def test_londres_est_gbp(self) -> None:
        assert deviner_devise("HSBA.L") == "GBP"

    def test_tokyo_est_jpy(self) -> None:
        assert deviner_devise("7203.T") == "JPY"

    def test_hong_kong_est_hkd(self) -> None:
        assert deviner_devise("9988.HK") == "HKD"

    def test_shanghai_est_cny(self) -> None:
        assert deviner_devise("600519.SS") == "CNY"

    def test_suffixe_inconnu_tombe_sur_defaut(self) -> None:
        assert deviner_devise("ABC.ZZ") == DEVISE_DEFAUT


class TestExpositionParDevise:
    def _rapport(self) -> object:
        positions = [
            Position(ticker="AAPL", quantite=10, prix_entree=100.0),
            Position(ticker="MC.PA", quantite=5, prix_entree=600.0),
            Position(ticker="HSBA.L", quantite=100, prix_entree=6.0),
        ]
        cotations = {
            "AAPL":   Cotation(ticker="AAPL",   prix=150.0, clotures=[150.0]),
            "MC.PA":  Cotation(ticker="MC.PA",  prix=700.0, clotures=[700.0]),
            "HSBA.L": Cotation(ticker="HSBA.L", prix=7.0,   clotures=[7.0]),
        }
        return construire_rapport(
            positions,
            cotations,
            evaluer_portefeuille(positions, cotations, Seuils()),
            aujourdhui=date(2026, 8, 29),
        )

    def test_agrege_par_devise_et_trie(self) -> None:
        rapport = self._rapport()  # type: ignore[assignment]
        result = exposition_par_devise(rapport.lignes)  # type: ignore[attr-defined]

        devises = [e.devise for e in result]
        assert devises == sorted(devises, key=lambda d: -next(
            e.poids_pct for e in result if e.devise == d
        ))
        assert set(devises) == {"USD", "EUR", "GBP"}

    def test_poids_sommes_a_100(self) -> None:
        rapport = self._rapport()  # type: ignore[assignment]
        result = exposition_par_devise(rapport.lignes)  # type: ignore[attr-defined]
        assert sum(e.poids_pct for e in result) == pytest.approx(100.0, abs=1e-6)

    def test_nb_positions_par_devise(self) -> None:
        rapport = self._rapport()  # type: ignore[assignment]
        result = exposition_par_devise(rapport.lignes)  # type: ignore[attr-defined]
        par_devise = {e.devise: e for e in result}
        assert par_devise["USD"].nb_positions == 1
        assert par_devise["EUR"].nb_positions == 1
        assert par_devise["GBP"].nb_positions == 1

    def test_portefeuille_vide(self) -> None:
        assert exposition_par_devise([]) == []

    def test_est_dataclass_immuable(self) -> None:
        e = ExpositionDevise(devise="USD", poids_pct=50.0, valeur=1000.0, nb_positions=3)
        with pytest.raises((AttributeError, Exception)):
            e.devise = "EUR"  # type: ignore[misc]

"""Tests des types du domaine : garantissent l'arithmetique des positions."""

from __future__ import annotations

import pytest

from trackerbot.models import Cotation, Niveau, Position, Signal


class TestPosition:
    def test_valeur_et_pnl_long(self) -> None:
        p = Position(ticker="AAPL", quantite=10, prix_entree=100.0)
        assert p.valeur(120.0) == pytest.approx(1200.0)
        assert p.gain_absolu(120.0) == pytest.approx(200.0)
        assert p.gain_pct(120.0) == pytest.approx(20.0)

    def test_pnl_short(self) -> None:
        p = Position(ticker="AAPL", quantite=10, prix_entree=100.0, est_long=False)
        assert p.gain_absolu(80.0) == pytest.approx(200.0)
        assert p.gain_pct(80.0) == pytest.approx(20.0)

    def test_quantite_invalide(self) -> None:
        with pytest.raises(ValueError):
            Position(ticker="A", quantite=0, prix_entree=1)

    def test_prix_invalide(self) -> None:
        with pytest.raises(ValueError):
            Position(ticker="A", quantite=1, prix_entree=0)

    def test_nom_par_defaut(self) -> None:
        p = Position(ticker="AAPL", quantite=1, prix_entree=1)
        assert p.nom == "AAPL"
        p2 = Position(ticker="AAPL", quantite=1, prix_entree=1, libelle="Apple")
        assert p2.nom == "Apple"


class TestCotation:
    def test_variation_jour(self) -> None:
        c = Cotation(ticker="X", prix=110.0, clotures=[100.0, 110.0])
        assert c.variation_jour_pct == pytest.approx(10.0)

    def test_variation_sans_historique(self) -> None:
        c = Cotation(ticker="X", prix=110.0, clotures=[110.0])
        assert c.variation_jour_pct is None


class TestSignal:
    def test_repr_utilise_niveau(self) -> None:
        s = Signal(ticker="X", niveau=Niveau.ALERTE, regle="r", message="m")
        assert "alerte" in str(s)

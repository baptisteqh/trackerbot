"""Tests des metriques portefeuille : Sharpe, drawdown, HHI, beta.

Toutes les series de reference sont construites en dur : aucun reseau,
aucun aleatoire, les valeurs attendues sont derivees analytiquement.
"""

from __future__ import annotations

import math

import pytest

from trackerbot.metrics import (
    JOURS_BOURSE,
    beta_vs_benchmark,
    calculer_metriques,
    hhi,
    max_drawdown_pct,
    rendement_annuel_pct,
    rendements_journaliers,
    serie_equity_portefeuille,
    sharpe_annualise,
    volatilite_annuelle_pct,
)
from trackerbot.models import Cotation, Position


class TestRendementsJournaliers:
    def test_deux_prix(self) -> None:
        assert rendements_journaliers([100.0, 110.0]) == pytest.approx([0.10])

    def test_serie_vide(self) -> None:
        assert rendements_journaliers([]) == []

    def test_ignore_prix_negatif_ou_nul(self) -> None:
        assert rendements_journaliers([100.0, 0.0, 50.0]) == pytest.approx([-1.0])


class TestSharpe:
    def test_serie_trop_courte(self) -> None:
        assert sharpe_annualise([0.01]) is None

    def test_variance_nulle(self) -> None:
        assert sharpe_annualise([0.001] * 10) is None

    def test_valeur_positive_quand_rendement_bat_taux_sans_risque(self) -> None:
        # rendement journalier constant a 0.1% + un bruit minuscule pour eviter variance nulle
        base = [0.001, 0.0011] * 30
        s = sharpe_annualise(base, taux_sans_risque_annuel=0.0)
        assert s is not None
        assert s > 0


class TestMaxDrawdown:
    def test_serie_vide(self) -> None:
        assert max_drawdown_pct([]) is None

    def test_serie_croissante(self) -> None:
        assert max_drawdown_pct([100.0, 110.0, 120.0]) == 0.0

    def test_drawdown_de_25_pourcent(self) -> None:
        # pic a 200, creux a 150
        assert max_drawdown_pct([100.0, 200.0, 150.0, 180.0]) == pytest.approx(25.0)

    def test_ignore_pic_non_positif(self) -> None:
        # equity qui commence sous zero : max_drawdown reste 0 tant que le pic n'est pas > 0
        assert max_drawdown_pct([-10.0, -5.0, -20.0]) == 0.0


class TestVolatiliteEtRendementAnnuels:
    def test_vol_zero_quand_serie_constante(self) -> None:
        assert volatilite_annuelle_pct([0.01, 0.01, 0.01]) == 0.0

    def test_rendement_annuel_lineaire(self) -> None:
        # moyenne 1% par jour * 252 = 252%
        r = rendement_annuel_pct([0.01] * 10)
        assert r == pytest.approx(0.01 * JOURS_BOURSE * 100.0)

    def test_rendement_serie_vide(self) -> None:
        assert rendement_annuel_pct([]) is None


class TestHhi:
    def test_serie_vide(self) -> None:
        assert hhi([]) is None

    def test_portefeuille_unique(self) -> None:
        assert hhi([100.0]) == 10000.0

    def test_portefeuille_equipondere(self) -> None:
        # 4 positions a 25% chacune : 4 * 625 = 2500
        assert hhi([25.0, 25.0, 25.0, 25.0]) == pytest.approx(2500.0)


class TestBeta:
    def test_serie_trop_courte(self) -> None:
        assert beta_vs_benchmark([0.01], [0.01]) is None

    def test_beta_egal_1_quand_series_identiques(self) -> None:
        rendements = [0.01, -0.02, 0.03, -0.01, 0.02]
        assert beta_vs_benchmark(rendements, rendements) == pytest.approx(1.0)

    def test_beta_egal_2_quand_amplitude_double(self) -> None:
        bench = [0.01, -0.02, 0.03, -0.01, 0.02]
        port = [2 * r for r in bench]
        assert beta_vs_benchmark(port, bench) == pytest.approx(2.0)

    def test_beta_variance_benchmark_nulle(self) -> None:
        assert beta_vs_benchmark([0.01, 0.02], [0.005, 0.005]) is None


class TestSerieEquity:
    def test_positions_vides(self) -> None:
        assert serie_equity_portefeuille([], {}) == []

    def test_valeur_egale_quantite_fois_prix(self) -> None:
        position = Position(ticker="AAA", quantite=2.0, prix_entree=50.0)
        cotation = Cotation(ticker="AAA", prix=110.0, clotures=[100.0, 105.0, 110.0])
        assert serie_equity_portefeuille([position], {"AAA": cotation}) == [200.0, 210.0, 220.0]

    def test_short_compte_en_negatif(self) -> None:
        p = Position(ticker="BBB", quantite=1.0, prix_entree=100.0, est_long=False)
        c = Cotation(ticker="BBB", prix=90.0, clotures=[100.0, 90.0])
        assert serie_equity_portefeuille([p], {"BBB": c}) == [-100.0, -90.0]

    def test_alignement_sur_la_fenetre_commune(self) -> None:
        p1 = Position(ticker="AAA", quantite=1.0, prix_entree=10.0)
        p2 = Position(ticker="BBB", quantite=1.0, prix_entree=10.0)
        c1 = Cotation(ticker="AAA", prix=13.0, clotures=[10.0, 11.0, 12.0, 13.0])
        c2 = Cotation(ticker="BBB", prix=22.0, clotures=[20.0, 22.0])
        # fenetre commune = 2 derniers points : (12+20, 13+22) = (32, 35)
        assert serie_equity_portefeuille([p1, p2], {"AAA": c1, "BBB": c2}) == [32.0, 35.0]


class TestCalculerMetriques:
    def test_metriques_de_base_calculables(self) -> None:
        position = Position(ticker="AAA", quantite=1.0, prix_entree=100.0)
        clotures = [100.0 + i for i in range(30)]  # monte lineairement
        cotation = Cotation(ticker="AAA", prix=clotures[-1], clotures=clotures)

        m = calculer_metriques([position], {"AAA": cotation}, poids_pct=[100.0])

        assert m.plus_grosse_position_pct == pytest.approx(100.0)
        assert m.hhi == pytest.approx(10000.0)
        assert m.max_drawdown_pct == pytest.approx(0.0)
        assert m.beta is None
        assert m.benchmark is None
        assert m.rendement_annuel_pct is not None
        assert m.rendement_annuel_pct > 0

    def test_beta_renseigne_quand_benchmark_fourni(self) -> None:
        position = Position(ticker="AAA", quantite=1.0, prix_entree=100.0)
        clotures = [100.0, 101.0, 102.0, 103.0, 104.0]
        cotation = Cotation(ticker="AAA", prix=104.0, clotures=clotures)
        # meme serie -> beta = 1
        benchmark = Cotation(ticker="SPY", prix=104.0, clotures=clotures)

        m = calculer_metriques(
            [position], {"AAA": cotation}, poids_pct=[100.0], cotation_benchmark=benchmark
        )

        assert m.beta is not None
        assert math.isclose(m.beta, 1.0, rel_tol=1e-9)
        assert m.benchmark == "SPY"

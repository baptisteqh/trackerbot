"""Tests du module diversification, offline."""

from __future__ import annotations

import pytest

from trackerbot.diversification import (
    SEUIL_CONCENTRATION_SECTEUR_PCT,
    calculer_diversification,
)
from trackerbot.fundamentals import Fondamentaux
from trackerbot.models import Cotation, Position
from trackerbot.report import LignePortefeuille


def _ligne(
    ticker: str,
    poids_pct: float,
    secteur: str | None = None,
    clotures: list[float] | None = None,
) -> LignePortefeuille:
    position = Position(ticker=ticker, quantite=1.0, prix_entree=100.0)
    cotation = Cotation(ticker=ticker, prix=100.0, clotures=clotures or []) if clotures else None
    fondamentaux = Fondamentaux(ticker=ticker, secteur=secteur) if secteur else None
    return LignePortefeuille(
        position=position,
        cotation=cotation,
        poids_pct=poids_pct,
        valeur_courante=1000.0,
        montant_investi=1000.0,
        gain_absolu=0.0,
        gain_pct=0.0,
        rsi_14=None,
        sma_20=None,
        sma_50=None,
        volatilite_20j_pct=None,
        fondamentaux=fondamentaux,
    )


class TestDiversification:
    def test_portefeuille_vide(self) -> None:
        result = calculer_diversification([])
        assert result.poids_par_secteur == {}
        assert result.positions_effectives is None

    def test_positions_effectives_equipondere(self) -> None:
        # 4 positions a 25% : N_eff = 1 / (4 * 0.25^2) = 1 / 0.25 = 4
        lignes = [_ligne(f"T{i}", 25.0) for i in range(4)]
        result = calculer_diversification(lignes)
        assert result.positions_effectives == pytest.approx(4.0)

    def test_positions_effectives_concentre(self) -> None:
        # 1 position dominante : N_eff << nombre de positions
        lignes = [
            _ligne("BIG", 80.0),
            _ligne("SMALL1", 10.0),
            _ligne("SMALL2", 10.0),
        ]
        result = calculer_diversification(lignes)
        assert result.positions_effectives is not None
        assert result.positions_effectives < 2.0

    def test_secteur_surconcentre(self) -> None:
        lignes = [
            _ligne("AAPL", 45.0, secteur="Technology"),
            _ligne("MSFT", 20.0, secteur="Technology"),
            _ligne("PG", 35.0, secteur="Consumer Staples"),
        ]
        result = calculer_diversification(lignes)
        assert result.plus_gros_secteur == "Technology"
        assert result.plus_gros_secteur_pct == pytest.approx(65.0)
        assert result.secteur_surconcentre  # 65% > seuil 40%
        assert result.plus_gros_secteur_pct >= SEUIL_CONCENTRATION_SECTEUR_PCT

    def test_secteur_unknown_quand_fondamentaux_absents(self) -> None:
        lignes = [_ligne("MYSTERY", 100.0)]
        result = calculer_diversification(lignes)
        assert "Unknown" in result.poids_par_secteur

    def test_correlation_moyenne_series_identiques(self) -> None:
        # Deux positions avec les memes clotures : correlation = 1
        clotures = [100.0 + i for i in range(20)]  # monte lineairement
        lignes = [
            _ligne("A", 50.0, secteur="Tech", clotures=clotures),
            _ligne("B", 50.0, secteur="Fin", clotures=clotures),
        ]
        result = calculer_diversification(lignes)
        assert result.correlation_moyenne == pytest.approx(1.0)
        assert len(result.paires_correlees) == 1
        assert result.paires_correlees[0].correlation == pytest.approx(1.0)

    def test_paires_correlees_ignore_petites_positions(self) -> None:
        # Deux positions correlees mais < 5% chacune : pas dans les alertes.
        clotures = [100.0 + i for i in range(20)]
        lignes = [
            _ligne("A", 3.0, clotures=clotures),
            _ligne("B", 3.0, clotures=clotures),
            _ligne("C", 94.0, clotures=[100.0 + i * 0.5 for i in range(20)]),
        ]
        result = calculer_diversification(lignes)
        for paire in result.paires_correlees:
            assert paire.ticker_a != "A" or paire.ticker_b != "B"

    def test_ratio_diversification_positions_identiques(self) -> None:
        # Deux positions parfaitement correlees : DR = 1 (pas de gain).
        # On simule des rendements bruites petits pour eviter variance nulle.
        clotures = [100 + (i % 2) * 0.5 for i in range(20)]
        lignes = [
            _ligne("A", 50.0, clotures=clotures),
            _ligne("B", 50.0, clotures=clotures),
        ]
        result = calculer_diversification(lignes)
        assert result.ratio_diversification is not None
        assert 0.9 <= result.ratio_diversification <= 1.1

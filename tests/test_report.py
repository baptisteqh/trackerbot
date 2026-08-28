"""Tests du rapport : agregation deterministe, sans reseau."""

from __future__ import annotations

from datetime import date

from trackerbot.models import Cotation, Niveau, Position, Signal
from trackerbot.report import construire_rapport, formater_rapport


def _p(ticker: str, prix_entree: float, quantite: float = 10) -> Position:
    return Position(ticker=ticker, quantite=quantite, prix_entree=prix_entree)


def test_rapport_calcule_pnl_et_poids() -> None:
    positions = [_p("AAPL", 100.0), _p("MSFT", 200.0)]
    cotations = {
        "AAPL": Cotation(ticker="AAPL", prix=110.0, clotures=[100.0, 110.0]),
        "MSFT": Cotation(ticker="MSFT", prix=180.0, clotures=[200.0, 180.0]),
    }
    rapport = construire_rapport(positions, cotations, aujourdhui=date(2026, 1, 1))

    assert rapport.montant_investi == 3000.0
    assert rapport.valeur_courante == 2900.0
    assert rapport.gain_absolu == -100.0
    assert rapport.nombre_positions == 2

    poids = {ligne.ticker: ligne.poids_pct for ligne in rapport.lignes}
    total_poids = sum(poids.values())
    assert abs(total_poids - 100.0) < 1e-6
    assert not rapport.tickers_manquants


def test_rapport_signal_present_dans_rendu() -> None:
    positions = [_p("AAPL", 100.0)]
    cotations = {"AAPL": Cotation(ticker="AAPL", prix=110.0)}
    signaux = [
        Signal(ticker="AAPL", niveau=Niveau.ALERTE, regle="stop_loss", message="stop touche")
    ]
    rapport = construire_rapport(positions, cotations, signaux)
    rendu = formater_rapport(rapport)

    assert "AAPL" in rendu
    assert "stop touche" in rendu
    assert "alerte" in rendu


def test_rapport_signale_les_tickers_manquants() -> None:
    positions = [_p("AAPL", 100.0), _p("XYZ", 50.0)]
    cotations = {"AAPL": Cotation(ticker="AAPL", prix=110.0)}
    rapport = construire_rapport(positions, cotations)
    assert rapport.tickers_manquants == ["XYZ"]
    assert "XYZ" in formater_rapport(rapport)


def test_rapport_sans_signaux_a_un_message_explicite() -> None:
    rapport = construire_rapport([_p("AAPL", 100.0)], {"AAPL": Cotation(ticker="AAPL", prix=100.0)})
    assert "Aucun signal" in formater_rapport(rapport)

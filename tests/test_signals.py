"""Tests des regles de surveillance."""

from __future__ import annotations

from trackerbot.models import Cotation, Niveau, Position
from trackerbot.signals import (
    Seuils,
    evaluer,
    evaluer_portefeuille,
    regle_repli,
    regle_rsi,
    regle_stop_loss,
    regle_take_profit,
    regle_variation_jour,
)


def _position(**k: object) -> Position:
    base = dict(ticker="AAPL", quantite=10.0, prix_entree=100.0)
    base.update(k)
    return Position(**base)  # type: ignore[arg-type]


def test_stop_loss_franchi() -> None:
    position = _position(stop_loss=90.0)
    cotation = Cotation(ticker="AAPL", prix=85.0, clotures=[100.0, 85.0])
    signal = regle_stop_loss(position, cotation, Seuils())
    assert signal is not None
    assert signal.niveau is Niveau.ALERTE


def test_stop_loss_proche() -> None:
    position = _position(stop_loss=99.0)
    cotation = Cotation(ticker="AAPL", prix=100.0, clotures=[100.0])
    signal = regle_stop_loss(position, cotation, Seuils(approche_stop_pct=3.0))
    assert signal is not None
    assert signal.niveau is Niveau.ATTENTION


def test_stop_loss_absent() -> None:
    position = _position()
    cotation = Cotation(ticker="AAPL", prix=100.0)
    assert regle_stop_loss(position, cotation, Seuils()) is None


def test_take_profit_atteint_long() -> None:
    position = _position(take_profit=120.0)
    cotation = Cotation(ticker="AAPL", prix=125.0)
    signal = regle_take_profit(position, cotation, Seuils())
    assert signal is not None
    assert signal.niveau is Niveau.ALERTE


def test_repli_alerte() -> None:
    clotures = [100.0] * 30 + [70.0]
    cotation = Cotation(ticker="X", prix=70.0, clotures=clotures)
    signal = regle_repli(_position(), cotation, Seuils(repli_alerte_pct=20.0))
    assert signal is not None
    assert signal.niveau is Niveau.ALERTE


def test_rsi_surachat() -> None:
    valeurs = [float(x) for x in range(1, 30)]
    cotation = Cotation(ticker="X", prix=valeurs[-1], clotures=valeurs)
    signal = regle_rsi(_position(), cotation, Seuils())
    assert signal is not None
    assert "surachat" in signal.regle


def test_variation_jour_ignoree_si_faible() -> None:
    cotation = Cotation(ticker="X", prix=101.0, clotures=[100.0, 101.0])
    assert regle_variation_jour(_position(), cotation, Seuils()) is None


def test_variation_jour_declenchee() -> None:
    cotation = Cotation(ticker="X", prix=110.0, clotures=[100.0, 110.0])
    signal = regle_variation_jour(_position(), cotation, Seuils(variation_jour_pct=5.0))
    assert signal is not None


def test_evaluer_trie_par_gravite() -> None:
    position = _position(stop_loss=90.0)
    cotation = Cotation(ticker="AAPL", prix=85.0, clotures=[float(x) for x in range(1, 30)])
    signaux = evaluer(position, cotation, Seuils())
    niveaux = [s.niveau for s in signaux]
    ordre = {Niveau.ALERTE: 0, Niveau.ATTENTION: 1, Niveau.INFO: 2}
    assert niveaux == sorted(niveaux, key=lambda n: ordre[n])


def test_evaluer_portefeuille_ignore_ticker_sans_cotation() -> None:
    p1 = _position(ticker="AAPL")
    p2 = _position(ticker="MSFT")
    cotations = {"AAPL": Cotation(ticker="AAPL", prix=100.0)}
    signaux = evaluer_portefeuille([p1, p2], cotations)
    assert all(s.ticker == "AAPL" for s in signaux)

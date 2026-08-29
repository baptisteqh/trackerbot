"""Tests des regles de surveillance."""

from __future__ import annotations

from trackerbot.models import Cotation, Niveau, Position
from trackerbot.signals import (
    Seuils,
    evaluer,
    evaluer_portefeuille,
    regle_bollinger,
    regle_macd,
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


def test_macd_croisement_haussier() -> None:
    # Longue baisse (histogramme MACD negatif) puis rebond franc :
    # au 2eme point de rebond, l'histogramme bascule negatif -> positif.
    clotures = [100 - i for i in range(50)] + [50 + i * 5 for i in range(2)]
    position = _position(ticker="AAPL")
    cotation = Cotation(ticker="AAPL", prix=clotures[-1], clotures=clotures)
    signal = regle_macd(position, cotation, Seuils())
    assert signal is not None
    assert signal.regle == "macd_croisement_haussier"


def test_macd_pas_de_signal_sans_historique() -> None:
    position = _position()
    cotation = Cotation(ticker="AAPL", prix=100.0, clotures=[100.0, 101.0])
    assert regle_macd(position, cotation, Seuils()) is None


def test_bollinger_prix_hors_bande_haute() -> None:
    # 20 clotures autour de 100, puis un pic tres au-dessus.
    clotures = [100.0 + (i % 3) * 0.1 for i in range(20)] + [130.0]
    position = _position()
    cotation = Cotation(ticker="AAPL", prix=130.0, clotures=clotures)
    signal = regle_bollinger(position, cotation, Seuils())
    assert signal is not None
    assert signal.regle == "bollinger_haute"


def test_bollinger_prix_hors_bande_basse() -> None:
    clotures = [100.0 + (i % 3) * 0.1 for i in range(20)] + [70.0]
    position = _position()
    cotation = Cotation(ticker="AAPL", prix=70.0, clotures=clotures)
    signal = regle_bollinger(position, cotation, Seuils())
    assert signal is not None
    assert signal.regle == "bollinger_basse"


def test_bollinger_prix_dans_les_bandes() -> None:
    clotures = [100.0 + (i % 3) * 0.5 for i in range(20)] + [100.5]
    position = _position()
    cotation = Cotation(ticker="AAPL", prix=100.5, clotures=clotures)
    assert regle_bollinger(position, cotation, Seuils()) is None

"""Tests de la normalisation des reponses eToro (parseur pur, sans reseau)."""

from __future__ import annotations

from trackerbot.sources.etoro import positions_depuis_reponse


def test_normalisation_position_avec_units() -> None:
    charge = {
        "positions": [
            {
                "instrumentID": 1001,
                "instrumentName": "Apple",
                "ticker": "AAPL",
                "units": 5,
                "openRate": 100.0,
                "stopLossRate": 90.0,
                "takeProfitRate": 130.0,
                "isBuy": True,
            }
        ]
    }
    positions = positions_depuis_reponse(charge)
    assert len(positions) == 1
    p = positions[0]
    assert p.ticker == "AAPL"
    assert p.quantite == 5.0
    assert p.stop_loss == 90.0
    assert p.take_profit == 130.0
    assert p.est_long is True
    assert p.source == "etoro"


def test_normalisation_calcule_quantite_depuis_montant() -> None:
    charge = {
        "clientPortfolio": {
            "positions": [
                {
                    "ticker": "MSFT",
                    "openRate": 200.0,
                    "investedAmount": 1000.0,
                    "isBuy": False,
                }
            ]
        }
    }
    positions = positions_depuis_reponse(charge)
    assert positions[0].quantite == 5.0
    assert positions[0].est_long is False


def test_normalisation_ignore_positions_invalides() -> None:
    charge = {"positions": [{"ticker": "XYZ"}]}
    assert positions_depuis_reponse(charge) == []


def test_normalisation_positions_non_liste() -> None:
    assert positions_depuis_reponse({"positions": "nope"}) == []

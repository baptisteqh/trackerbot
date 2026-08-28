"""Recuperation des cours, isolee derriere une seule fonction.

yfinance est gratuit et sans cle, mais c'est un client non officiel de
Yahoo Finance : il casse de temps en temps. Tout le reste du bot ne
connait que `cotations()`, donc changer de fournisseur ne touchera que ce
fichier.
"""

from __future__ import annotations

from .models import Cotation


def cotations(tickers: list[str], jours: int = 260) -> dict[str, Cotation]:
    """Cours actuel et historique de cloture pour chaque ticker.

    Les tickers introuvables sont simplement absents du resultat : une
    ligne exotique du portefeuille ne doit pas faire tomber le rapport.
    """
    if not tickers:
        return {}

    import yfinance  # importe tard : il tire pandas, inutile pour les tests

    uniques = sorted({t.strip().upper() for t in tickers if t.strip()})
    resultat: dict[str, Cotation] = {}

    for ticker in uniques:
        try:
            historique = yfinance.Ticker(ticker).history(period=f"{jours}d", interval="1d")
        except Exception:  # noqa: BLE001 - un ticker cassé ne doit pas tout arreter
            continue
        if historique is None or historique.empty:
            continue

        clotures = [float(v) for v in historique["Close"].dropna().tolist()]
        if not clotures:
            continue

        resultat[ticker] = Cotation(
            ticker=ticker,
            prix=clotures[-1],
            clotures=clotures,
            devise=str(getattr(historique, "attrs", {}).get("currency", "USD")),
        )
    return resultat

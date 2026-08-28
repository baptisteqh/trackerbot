"""Fondamentaux d'entreprise, isoles derriere une seule fonction reseau.

Meme pattern que `market.py` : yfinance importe tard, chaque ticker est
tente independamment, un echec ponctuel ne fait pas tomber le rapport.
Aucun secret n'est necessaire : Yahoo est public.

Les champs retournes sont volontairement minimalistes ; ce sont ceux dont
la valorisation (`valuation.py`) a besoin. Ajouter un champ ici implique
un test unitaire dans test_fundamentals.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Fondamentaux:
    """Instantane des fondamentaux d'une entreprise, tel que Yahoo les expose."""

    ticker: str
    per: float | None = None
    price_to_book: float | None = None
    marge_nette_pct: float | None = None
    debt_to_equity: float | None = None
    roe_pct: float | None = None
    dividend_yield_pct: float | None = None
    croissance_revenus_pct: float | None = None
    secteur: str | None = None
    industrie: str | None = None


def fondamentaux(tickers: list[str]) -> dict[str, Fondamentaux]:
    """Fondamentaux Yahoo pour chaque ticker.

    Tickers introuvables ou en erreur sont simplement absents du resultat.
    Aucun retry, aucun cache : le job est declenche a la main par
    l'utilisateur qui peut relancer.
    """
    if not tickers:
        return {}

    import yfinance  # tardif : evite pandas au demarrage

    uniques = sorted({t.strip().upper() for t in tickers if t.strip()})
    resultat: dict[str, Fondamentaux] = {}

    for ticker in uniques:
        try:
            info = yfinance.Ticker(ticker).info
        except Exception:  # noqa: BLE001 - un ticker cassé ne doit pas tout arreter
            continue
        if not isinstance(info, dict) or not info:
            continue
        resultat[ticker] = _extraire_fondamentaux(ticker, info)

    return resultat


def _extraire_fondamentaux(ticker: str, info: dict[str, Any]) -> Fondamentaux:
    """Convertit un dict Yahoo brut en objet Fondamentaux.

    Isole pour etre testable sans reseau : suffit de passer un dict.
    """
    return Fondamentaux(
        ticker=ticker.upper(),
        per=_flottant(info.get("trailingPE") or info.get("forwardPE")),
        price_to_book=_flottant(info.get("priceToBook")),
        marge_nette_pct=_ratio_en_pct(info.get("profitMargins")),
        debt_to_equity=_debt_to_equity(info.get("debtToEquity")),
        roe_pct=_ratio_en_pct(info.get("returnOnEquity")),
        dividend_yield_pct=_dividend_yield_en_pct(info.get("dividendYield")),
        croissance_revenus_pct=_ratio_en_pct(info.get("revenueGrowth")),
        secteur=_texte(info.get("sector")),
        industrie=_texte(info.get("industry")),
    )


def _flottant(valeur: Any) -> float | None:
    if valeur is None:
        return None
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        return None
    return None if v != v else v  # NaN check sans importer math


def _ratio_en_pct(valeur: Any) -> float | None:
    """Yahoo renvoie un ratio (0.15 pour 15 %), on convertit en pourcentage."""
    v = _flottant(valeur)
    return None if v is None else v * 100.0


def _debt_to_equity(valeur: Any) -> float | None:
    """Yahoo renvoie debtToEquity en pourcentage (ex: 82.5 pour 0.825), on ramene au ratio."""
    v = _flottant(valeur)
    return None if v is None else v / 100.0


def _dividend_yield_en_pct(valeur: Any) -> float | None:
    """Yahoo renvoie dividendYield deja en pourcentage sur les versions recentes."""
    return _flottant(valeur)


def _texte(valeur: Any) -> str | None:
    if valeur is None:
        return None
    texte = str(valeur).strip()
    return texte or None

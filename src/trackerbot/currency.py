"""Inference de la devise d'une action a partir du suffixe Yahoo Finance.

C'est une heuristique volontairement conservative : quand on ne sait pas,
on classe en 'USD' car la majorite des tickers Yahoo sans suffixe cotent
au NYSE / NASDAQ. Les tickers avec suffixe suivent une table publique
(https://finance.yahoo.com/lookup) qu'on encode ici.

Pure fonction : rien de reseau, aucune dependance.
"""

from __future__ import annotations

from dataclasses import dataclass

from .report import LignePortefeuille

# Suffixe Yahoo -> devise ISO. Table non exhaustive, couvre l'Europe,
# Asie majeure, Amerique du Nord et Oceanie. Editable sans casser le reste.
DEVISE_PAR_SUFFIXE: dict[str, str] = {
    # Zone euro
    ".PA": "EUR",   # Paris
    ".AS": "EUR",   # Amsterdam
    ".BR": "EUR",   # Bruxelles
    ".DE": "EUR",   # Xetra
    ".F":  "EUR",   # Francfort
    ".MI": "EUR",   # Milan
    ".MC": "EUR",   # Madrid
    ".LS": "EUR",   # Lisbonne
    ".IR": "EUR",   # Dublin
    ".VI": "EUR",   # Vienne
    ".HE": "EUR",   # Helsinki
    # UK
    ".L":  "GBP",
    ".IL": "GBP",
    # Suisse
    ".SW": "CHF",
    # Scandinavie hors EUR
    ".ST": "SEK",   # Stockholm
    ".OL": "NOK",   # Oslo
    ".CO": "DKK",   # Copenhague
    # Ameriques
    ".TO": "CAD",   # Toronto
    ".V":  "CAD",   # Venture (Canada)
    ".MX": "MXN",   # Mexico
    ".SA": "BRL",   # Sao Paulo
    # Asie
    ".T":  "JPY",   # Tokyo
    ".HK": "HKD",
    ".SS": "CNY",   # Shanghai
    ".SZ": "CNY",   # Shenzhen
    ".KS": "KRW",   # Seoul
    ".KQ": "KRW",   # KOSDAQ
    ".TW": "TWD",   # Taipei
    ".NS": "INR",   # NSE
    ".BO": "INR",   # BSE
    ".SI": "SGD",   # Singapour
    # Oceanie
    ".AX": "AUD",   # Sydney
    ".NZ": "NZD",   # Wellington
}

DEVISE_DEFAUT = "USD"


@dataclass(frozen=True)
class ExpositionDevise:
    """Une devise, le poids en % du portefeuille et la valeur brute."""

    devise: str
    poids_pct: float
    valeur: float
    nb_positions: int


def deviner_devise(ticker: str) -> str:
    """Renvoie la devise ISO probable pour un ticker Yahoo.

    Ex. `MC.PA` -> `EUR`, `AAPL` -> `USD`, `9988.HK` -> `HKD`.
    On matche sur le suffixe le plus long (les tickers avec point
    n'ayant qu'un seul suffixe en pratique, la table est plate).
    """
    haut = ticker.upper()
    for suffixe, devise in DEVISE_PAR_SUFFIXE.items():
        if haut.endswith(suffixe):
            return devise
    return DEVISE_DEFAUT


def exposition_par_devise(lignes: list[LignePortefeuille]) -> list[ExpositionDevise]:
    """Agrege les lignes par devise, triees par poids decroissant.

    Les lignes sans cotation (valeur_courante nulle) sont ignorees.
    """
    totaux: dict[str, tuple[float, int]] = {}
    for ligne in lignes:
        if not ligne.cotee:
            continue
        valeur = ligne.valeur_courante
        if valeur <= 0:
            continue
        devise = deviner_devise(ligne.position.ticker)
        montant, nb = totaux.get(devise, (0.0, 0))
        totaux[devise] = (montant + valeur, nb + 1)

    total_general = sum(m for m, _ in totaux.values())
    if total_general <= 0:
        return []

    resultat = [
        ExpositionDevise(
            devise=devise,
            poids_pct=(montant / total_general) * 100.0,
            valeur=montant,
            nb_positions=nb,
        )
        for devise, (montant, nb) in totaux.items()
    ]
    resultat.sort(key=lambda e: e.poids_pct, reverse=True)
    return resultat

"""Indicateurs techniques, en fonctions pures sur des listes de flottants.

Aucune dependance a pandas ni au reseau : c'est ce qui rend cette couche
testable a la main, et c'est la seule partie du bot dont les resultats
doivent etre exacts au chiffre pres.

Les series sont ordonnees du plus ancien au plus recent.
"""

from __future__ import annotations


def sma(valeurs: list[float], periode: int) -> float | None:
    """Moyenne mobile simple sur les `periode` dernieres valeurs."""
    if periode <= 0:
        raise ValueError("periode doit etre strictement positive")
    if len(valeurs) < periode:
        return None
    return sum(valeurs[-periode:]) / periode


def rsi(valeurs: list[float], periode: int = 14) -> float | None:
    """RSI de Wilder, avec lissage exponentiel apres la moyenne initiale.

    Renvoie None tant qu'il n'y a pas `periode` variations, soit
    `periode + 1` cloture. 100 quand aucune baisse n'a ete observee.
    """
    if periode <= 0:
        raise ValueError("periode doit etre strictement positive")
    if len(valeurs) < periode + 1:
        return None

    variations = [b - a for a, b in zip(valeurs[:-1], valeurs[1:], strict=True)]
    hausses = [max(v, 0.0) for v in variations]
    baisses = [max(-v, 0.0) for v in variations]

    moyenne_hausse = sum(hausses[:periode]) / periode
    moyenne_baisse = sum(baisses[:periode]) / periode

    for h, b in zip(hausses[periode:], baisses[periode:], strict=True):
        moyenne_hausse = (moyenne_hausse * (periode - 1) + h) / periode
        moyenne_baisse = (moyenne_baisse * (periode - 1) + b) / periode

    if moyenne_baisse == 0:
        return 100.0
    force = moyenne_hausse / moyenne_baisse
    return 100.0 - (100.0 / (1.0 + force))


def plus_haut(valeurs: list[float], fenetre: int | None = None) -> float | None:
    """Plus haut de cloture sur la fenetre, ou sur toute la serie si None."""
    serie = valeurs if fenetre is None else valeurs[-fenetre:]
    return max(serie) if serie else None


def repli_depuis_plus_haut_pct(valeurs: list[float], fenetre: int | None = None) -> float | None:
    """Recul du dernier prix par rapport au plus haut, en pourcentage positif."""
    if not valeurs:
        return None
    sommet = plus_haut(valeurs, fenetre)
    if sommet is None or sommet == 0:
        return None
    recul = (sommet - valeurs[-1]) / sommet * 100.0
    return max(recul, 0.0)


def croisement(rapide: list[float], lent: list[float]) -> str | None:
    """Detecte un croisement entre deux series alignees sur les memes dates.

    Renvoie 'haussier', 'baissier', ou None si rien ne s'est croise au
    dernier point. Les deux series doivent avoir au moins deux valeurs.
    """
    if len(rapide) < 2 or len(lent) < 2:
        return None
    avant_rapide, apres_rapide = rapide[-2], rapide[-1]
    avant_lent, apres_lent = lent[-2], lent[-1]

    if avant_rapide <= avant_lent and apres_rapide > apres_lent:
        return "haussier"
    if avant_rapide >= avant_lent and apres_rapide < apres_lent:
        return "baissier"
    return None


def serie_sma(valeurs: list[float], periode: int) -> list[float]:
    """Serie complete des moyennes mobiles, une valeur par point calculable."""
    if periode <= 0:
        raise ValueError("periode doit etre strictement positive")
    if len(valeurs) < periode:
        return []
    return [
        sum(valeurs[i : i + periode]) / periode
        for i in range(len(valeurs) - periode + 1)
    ]


def volatilite_pct(valeurs: list[float], fenetre: int = 20) -> float | None:
    """Ecart type des rendements journaliers sur la fenetre, en pourcentage."""
    if len(valeurs) < fenetre + 1:
        return None
    recents = valeurs[-(fenetre + 1) :]
    rendements = [
        (b - a) / a for a, b in zip(recents[:-1], recents[1:], strict=True) if a != 0
    ]
    if len(rendements) < 2:
        return None
    moyenne = sum(rendements) / len(rendements)
    variance = sum((r - moyenne) ** 2 for r in rendements) / (len(rendements) - 1)
    return float(variance**0.5 * 100.0)

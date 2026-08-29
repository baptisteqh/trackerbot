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


def roc(valeurs: list[float], periode: int) -> float | None:
    """Rate of Change : variation en pourcentage sur `periode` seances.

    Signal de momentum simple. Positif = tendance haussiere sur la fenetre.
    """
    if periode <= 0:
        raise ValueError("periode doit etre strictement positive")
    if len(valeurs) < periode + 1:
        return None
    reference = valeurs[-periode - 1]
    if reference <= 0:
        return None
    return (valeurs[-1] - reference) / reference * 100.0


def ema(valeurs: list[float], periode: int) -> list[float]:
    """Moyenne mobile exponentielle. Serie complete, meme longueur que l'entree."""
    if periode <= 0:
        raise ValueError("periode doit etre strictement positive")
    if not valeurs:
        return []
    alpha = 2.0 / (periode + 1)
    resultat = [valeurs[0]]
    for v in valeurs[1:]:
        resultat.append(alpha * v + (1 - alpha) * resultat[-1])
    return resultat


def macd(
    valeurs: list[float],
    rapide: int = 12,
    lente: int = 26,
    signal: int = 9,
) -> tuple[float, float, float] | None:
    """MACD (12, 26, 9). Renvoie (ligne_macd, ligne_signal, histogramme).

    Convention Appel : ligne_macd = EMA_rapide - EMA_lente, ligne_signal
    = EMA(ligne_macd, signal), histogramme = ligne_macd - ligne_signal.
    Positive-histogramme = momentum haussier.
    """
    if rapide >= lente:
        raise ValueError("rapide doit etre < lente")
    if len(valeurs) < lente + signal:
        return None
    ema_rapide = ema(valeurs, rapide)
    ema_lente = ema(valeurs, lente)
    ligne_macd = [
        rapide_val - lente_val
        for rapide_val, lente_val in zip(ema_rapide, ema_lente, strict=True)
    ]
    ligne_signal = ema(ligne_macd, signal)
    hist = ligne_macd[-1] - ligne_signal[-1]
    return ligne_macd[-1], ligne_signal[-1], hist


def bollinger_bands(
    valeurs: list[float],
    periode: int = 20,
    k: float = 2.0,
) -> tuple[float, float, float] | None:
    """Bandes de Bollinger : (basse, moyenne, haute) = SMA ± k * ecart-type.

    Un prix au-dessus de la bande haute ou sous la bande basse est
    considere comme "stretch" — proba de retour vers la moyenne accrue.
    """
    if periode <= 0:
        raise ValueError("periode doit etre strictement positive")
    if k <= 0:
        raise ValueError("k doit etre strictement positif")
    if len(valeurs) < periode:
        return None
    recents = valeurs[-periode:]
    moyenne = sum(recents) / periode
    variance = sum((v - moyenne) ** 2 for v in recents) / periode
    ecart_type = variance**0.5
    return moyenne - k * ecart_type, moyenne, moyenne + k * ecart_type


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

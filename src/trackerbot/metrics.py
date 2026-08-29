"""Metriques de portefeuille : risque, concentration, exposition au marche.

Fonctions pures sur des listes de flottants ou des cotations deja
recuperees. Aucun acces reseau. Les series de prix sont ordonnees du
plus ancien au plus recent.

Convention : 252 seances par an, taux sans risque annuel en decimal
(0.04 pour 4 %).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import Cotation, Position

JOURS_BOURSE = 252


@dataclass(frozen=True)
class MetriquesPortefeuille:
    """Ce qu'un tableau de bord type Delta afficherait en tete de page."""

    sharpe: float | None
    sortino: float | None
    max_drawdown_pct: float | None
    volatilite_annuelle_pct: float | None
    rendement_annuel_pct: float | None
    hhi: float | None
    plus_grosse_position_pct: float | None
    beta: float | None
    benchmark: str | None


def _moyenne_variance(valeurs: list[float]) -> tuple[float, float] | None:
    """Moyenne et variance non biaisee. None si moins de 2 points."""
    n = len(valeurs)
    if n < 2:
        return None
    moyenne = sum(valeurs) / n
    variance = sum((v - moyenne) ** 2 for v in valeurs) / (n - 1)
    return moyenne, variance


def rendements_journaliers(clotures: list[float]) -> list[float]:
    """Rendements arithmetiques d'une serie de prix, ignore les prix nuls ou negatifs."""
    return [(b - a) / a for a, b in zip(clotures[:-1], clotures[1:], strict=True) if a > 0]


def serie_equity_portefeuille(
    positions: list[Position],
    cotations: dict[str, Cotation],
) -> list[float]:
    """Courbe de valeur reconstituee, alignee sur la fenetre commune la plus recente.

    Les positions longues comptent en positif, les shorts en negatif. Les
    positions sans cotation sont ignorees : cette metrique ne parle que
    de ce qu'elle a mesure.
    """
    series: list[tuple[float, list[float]]] = []
    for position in positions:
        cotation = cotations.get(position.ticker)
        if cotation is None or not cotation.clotures:
            continue
        signe = 1.0 if position.est_long else -1.0
        series.append((signe * position.quantite, cotation.clotures))

    if not series:
        return []
    fenetre = min(len(clotures) for _, clotures in series)
    if fenetre == 0:
        return []
    return [
        sum(quantite * clotures[-fenetre + i] for quantite, clotures in series)
        for i in range(fenetre)
    ]


def sharpe_annualise(
    rendements: list[float],
    taux_sans_risque_annuel: float = 0.04,
) -> float | None:
    """Ratio de Sharpe annualise. None si variance nulle ou serie trop courte."""
    stats = _moyenne_variance(rendements)
    if stats is None:
        return None
    moyenne, variance = stats
    if variance == 0:
        return None
    exces_journalier = moyenne - taux_sans_risque_annuel / JOURS_BOURSE
    return exces_journalier / math.sqrt(variance) * math.sqrt(JOURS_BOURSE)


def sortino_annualise(
    rendements: list[float],
    taux_sans_risque_annuel: float = 0.04,
) -> float | None:
    """Ratio de Sortino annualise : Sharpe qui ne penalise que la volatilite baissiere.

    On calcule l'ecart-type des rendements strictement negatifs (downside
    deviation), pas de la volatilite totale. Renvoie None si moins de 2
    rendements ou aucun rendement baissier (rien a penaliser).
    """
    if len(rendements) < 2:
        return None
    exces_moyen = sum(rendements) / len(rendements) - taux_sans_risque_annuel / JOURS_BOURSE
    baisses = [r for r in rendements if r < 0]
    if len(baisses) < 2:
        return None
    variance_baisse = sum(b * b for b in baisses) / len(baisses)
    if variance_baisse == 0:
        return None
    return exces_moyen / math.sqrt(variance_baisse) * math.sqrt(JOURS_BOURSE)


def max_drawdown_pct(serie: list[float]) -> float | None:
    """Plus fort recul sommet -> creux, en pourcentage positif.

    Ignore les sommets non positifs : un equity qui traverse zero n'a
    pas de drawdown relatif interpretable.
    """
    if not serie:
        return None
    pic = serie[0]
    pire = 0.0
    for valeur in serie:
        if valeur > pic:
            pic = valeur
        if pic > 0:
            pire = max(pire, (pic - valeur) / pic * 100.0)
    return pire


def volatilite_annuelle_pct(rendements: list[float]) -> float | None:
    """Ecart-type annualise des rendements journaliers, en pourcentage."""
    stats = _moyenne_variance(rendements)
    if stats is None:
        return None
    _, variance = stats
    return math.sqrt(variance) * math.sqrt(JOURS_BOURSE) * 100.0


def rendement_annuel_pct(rendements: list[float]) -> float | None:
    """Rendement moyen annualise (approximation lineaire, pas compose)."""
    if not rendements:
        return None
    return sum(rendements) / len(rendements) * JOURS_BOURSE * 100.0


def hhi(poids_pct: list[float]) -> float | None:
    """Herfindahl-Hirschman sur des poids en % (echelle 0 a 10 000)."""
    return sum(p * p for p in poids_pct) if poids_pct else None


def beta_vs_benchmark(
    rendements_portefeuille: list[float],
    rendements_benchmark: list[float],
) -> float | None:
    """cov(port, bench) / var(bench), aligne sur la fenetre commune la plus recente."""
    taille = min(len(rendements_portefeuille), len(rendements_benchmark))
    if taille < 2:
        return None
    p = rendements_portefeuille[-taille:]
    b = rendements_benchmark[-taille:]
    moyenne_b = sum(b) / taille
    variance_b = sum((bi - moyenne_b) ** 2 for bi in b)
    if variance_b == 0:
        return None
    moyenne_p = sum(p) / taille
    covariance = sum((pi - moyenne_p) * (bi - moyenne_b) for pi, bi in zip(p, b, strict=True))
    return covariance / variance_b


def calculer_metriques(
    positions: list[Position],
    cotations: dict[str, Cotation],
    poids_pct: list[float],
    cotation_benchmark: Cotation | None = None,
    taux_sans_risque_annuel: float = 0.04,
) -> MetriquesPortefeuille:
    """Rassemble toutes les metriques dans un objet unique."""
    equity = serie_equity_portefeuille(positions, cotations)
    rendements = rendements_journaliers(equity)

    beta: float | None = None
    benchmark: str | None = None
    if cotation_benchmark is not None and cotation_benchmark.clotures:
        beta = beta_vs_benchmark(rendements, rendements_journaliers(cotation_benchmark.clotures))
        benchmark = cotation_benchmark.ticker

    return MetriquesPortefeuille(
        sharpe=sharpe_annualise(rendements, taux_sans_risque_annuel),
        sortino=sortino_annualise(rendements, taux_sans_risque_annuel),
        max_drawdown_pct=max_drawdown_pct(equity),
        volatilite_annuelle_pct=volatilite_annuelle_pct(rendements),
        rendement_annuel_pct=rendement_annuel_pct(rendements),
        hhi=hhi(poids_pct),
        plus_grosse_position_pct=max(poids_pct) if poids_pct else None,
        beta=beta,
        benchmark=benchmark,
    )

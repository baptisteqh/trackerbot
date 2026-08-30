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
    calmar: float | None
    max_drawdown_pct: float | None
    volatilite_annuelle_pct: float | None
    rendement_annuel_pct: float | None
    var_95_pct: float | None
    hhi: float | None
    plus_grosse_position_pct: float | None
    beta: float | None
    alpha_annuel_pct: float | None
    information_ratio: float | None
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


def calmar_ratio(
    rendement_annuel_pct_valeur: float | None,
    max_dd_pct_valeur: float | None,
) -> float | None:
    """Calmar = rendement annuel / |Max Drawdown|. None si MDD nul ou inconnu.

    Standard hedge fund pour comparer perf a douleur maximale subie.
    Attention : les deux entrees sont deja en % (echelle 0-100).
    """
    if rendement_annuel_pct_valeur is None or max_dd_pct_valeur is None:
        return None
    if max_dd_pct_valeur <= 0:
        return None
    return rendement_annuel_pct_valeur / max_dd_pct_valeur


def value_at_risk_historique_pct(
    rendements: list[float],
    confiance: float = 0.95,
) -> float | None:
    """VaR historique en pourcentage positif de perte 1 jour au niveau donne.

    Approche empirique : on prend le quantile (1 - confiance) des rendements
    (typiquement 5 %eme percentile pour VaR 95). C'est la perte que 5 % des
    seances historiques ont depassee. Renvoie None si moins de 20 rendements
    (trop peu pour un quantile empirique fiable), ou si la queue est
    positive (aucune perte historique = VaR 0 par convention).
    """
    if not 0 < confiance < 1:
        raise ValueError("confiance doit etre dans (0, 1)")
    if len(rendements) < 20:
        return None
    tries = sorted(rendements)
    # Quantile inferieur : indice = floor((1 - confiance) * n).
    indice = int((1 - confiance) * len(tries))
    quantile = tries[indice]
    return abs(quantile) * 100.0 if quantile < 0 else 0.0


def alpha_jensen_annuel_pct(
    rendements_portefeuille: list[float],
    rendements_benchmark: list[float],
    beta: float | None,
    taux_sans_risque_annuel: float = 0.04,
) -> float | None:
    """Alpha de Jensen annualise, en %. None si beta inconnu ou serie trop courte.

    alpha_journalier = mean(rp) - (rf_jour + beta * (mean(rb) - rf_jour))
    Annualise par x 252 * 100. Positif = valeur ajoutee au-dela du pur beta.
    """
    if beta is None:
        return None
    taille = min(len(rendements_portefeuille), len(rendements_benchmark))
    if taille < 2:
        return None
    rp = rendements_portefeuille[-taille:]
    rb = rendements_benchmark[-taille:]
    rf_jour = taux_sans_risque_annuel / JOURS_BOURSE
    exces_port = sum(rp) / taille - rf_jour
    exces_bench = sum(rb) / taille - rf_jour
    alpha_jour = exces_port - beta * exces_bench
    return alpha_jour * JOURS_BOURSE * 100.0


def information_ratio(
    rendements_portefeuille: list[float],
    rendements_benchmark: list[float],
) -> float | None:
    """IR annualise = moyenne(rp - rb) / ecart-type(rp - rb) * sqrt(252).

    Mesure la constance de l'ecart de performance vs benchmark.
    None si serie trop courte ou tracking error nul.
    """
    taille = min(len(rendements_portefeuille), len(rendements_benchmark))
    if taille < 2:
        return None
    rp = rendements_portefeuille[-taille:]
    rb = rendements_benchmark[-taille:]
    exces = [p - b for p, b in zip(rp, rb, strict=True)]
    stats = _moyenne_variance(exces)
    if stats is None:
        return None
    moyenne, variance = stats
    if variance == 0:
        return None
    return moyenne / math.sqrt(variance) * math.sqrt(JOURS_BOURSE)


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
    alpha: float | None = None
    info_ratio: float | None = None
    if cotation_benchmark is not None and cotation_benchmark.clotures:
        rendements_b = rendements_journaliers(cotation_benchmark.clotures)
        beta = beta_vs_benchmark(rendements, rendements_b)
        alpha = alpha_jensen_annuel_pct(rendements, rendements_b, beta, taux_sans_risque_annuel)
        info_ratio = information_ratio(rendements, rendements_b)
        benchmark = cotation_benchmark.ticker

    rendement_val = rendement_annuel_pct(rendements)
    mdd_val = max_drawdown_pct(equity)

    return MetriquesPortefeuille(
        sharpe=sharpe_annualise(rendements, taux_sans_risque_annuel),
        sortino=sortino_annualise(rendements, taux_sans_risque_annuel),
        calmar=calmar_ratio(rendement_val, mdd_val),
        max_drawdown_pct=mdd_val,
        volatilite_annuelle_pct=volatilite_annuelle_pct(rendements),
        rendement_annuel_pct=rendement_val,
        var_95_pct=value_at_risk_historique_pct(rendements, 0.95),
        hhi=hhi(poids_pct),
        plus_grosse_position_pct=max(poids_pct) if poids_pct else None,
        beta=beta,
        alpha_annuel_pct=alpha,
        information_ratio=info_ratio,
        benchmark=benchmark,
    )

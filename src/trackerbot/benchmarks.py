"""Comparaison portefeuille vs benchmark sur horizons standards.

Simple : sur la fenetre commune la plus recente, on prend la performance
relative du portefeuille contre le benchmark sur 1M / 3M / YTD / 1Y. On
renvoie None sur chaque fenetre trop courte plutot que d'inventer.

Ce module est cote agent trader jeune : "est-ce que je bats le marche
sur les 3 derniers mois ? oui / non / combien ?" — pas plus complique.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

FENETRES_JOURS = {
    "1M": 21,   # 21 seances de bourse
    "3M": 63,
    "YTD": None,  # calcule dynamiquement selon la date du jour
    "1Y": 252,
}


@dataclass(frozen=True)
class ComparaisonBenchmark:
    """Perf portefeuille et benchmark alignes sur les memes fenetres."""

    benchmark: str
    perf_portefeuille: dict[str, float | None] = field(default_factory=dict)
    perf_benchmark: dict[str, float | None] = field(default_factory=dict)
    outperformance: dict[str, float | None] = field(default_factory=dict)


def comparer(
    equity: list[float],
    benchmark: list[float],
    ticker_benchmark: str,
    aujourdhui: date | None = None,
) -> ComparaisonBenchmark:
    """Calcule perf portefeuille et benchmark alignes par fenetre.

    Les deux series doivent etre alignees temporellement (meme index de
    derniere seance). On considere que chaque point vaut une seance.
    """
    if not equity or not benchmark:
        return ComparaisonBenchmark(benchmark=ticker_benchmark)

    taille_commune = min(len(equity), len(benchmark))
    if taille_commune < 2:
        return ComparaisonBenchmark(benchmark=ticker_benchmark)

    equity_alignee = equity[-taille_commune:]
    bench_alignee = benchmark[-taille_commune:]

    perf_p: dict[str, float | None] = {}
    perf_b: dict[str, float | None] = {}
    out: dict[str, float | None] = {}

    for fenetre, jours in FENETRES_JOURS.items():
        n = _fenetre_effective(jours, taille_commune, fenetre, aujourdhui)
        if n is None or n < 2:
            perf_p[fenetre] = perf_b[fenetre] = out[fenetre] = None
            continue
        rp = _rendement_total_pct(equity_alignee[-n:])
        rb = _rendement_total_pct(bench_alignee[-n:])
        perf_p[fenetre] = rp
        perf_b[fenetre] = rb
        out[fenetre] = (rp - rb) if rp is not None and rb is not None else None

    return ComparaisonBenchmark(
        benchmark=ticker_benchmark,
        perf_portefeuille=perf_p,
        perf_benchmark=perf_b,
        outperformance=out,
    )


def _fenetre_effective(
    jours: int | None,
    taille_commune: int,
    label: str,
    aujourdhui: date | None,
) -> int | None:
    """Approximation : YTD = seances depuis le 1er janvier de l'annee courante."""
    if jours is not None:
        return min(jours, taille_commune)
    if label != "YTD":
        return None
    now = aujourdhui or datetime.now().date()
    jour_annee = (now - date(now.year, 1, 1)).days
    seances_ytd = int(jour_annee * 5 / 7)  # approximation 5 jours ouvres sur 7
    return min(max(seances_ytd, 2), taille_commune)


def _rendement_total_pct(serie: list[float]) -> float | None:
    """Rendement cumule (fin - debut) / debut * 100."""
    if len(serie) < 2 or serie[0] <= 0:
        return None
    return (serie[-1] - serie[0]) / serie[0] * 100.0

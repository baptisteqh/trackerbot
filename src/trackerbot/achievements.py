"""Badges gamifies pour rendre le suivi de portefeuille motivant.

Chaque badge est une fonction pure de (rapport, diversification,
comparaison benchmark). Une regle : le seuil doit etre atteint pour
que le badge soit `unlocked=True`. Sinon on renvoie un badge locked
avec la phrase de progression pour que l'UI puisse le montrer en gris.

Ne pas ajouter de badge "sneaky" (unlocked par hasard sur un jour) :
chaque badge doit refleter un vrai comportement d'investissement.
"""

from __future__ import annotations

from dataclasses import dataclass

from .benchmarks import ComparaisonBenchmark
from .diversification import Diversification
from .report import Rapport


@dataclass(frozen=True)
class Badge:
    id: str
    label: str
    description: str
    unlocked: bool
    detail: str | None = None


def evaluer_badges(
    rapport: Rapport,
    diversification: Diversification | None = None,
    comparaison: ComparaisonBenchmark | None = None,
) -> list[Badge]:
    """Renvoie la liste complete des badges (unlocked + locked, dans l'ordre)."""
    badges = [
        _first_position(rapport),
        _positive_pnl(rapport),
        _double_digit_gainer(rapport),
        _risk_manager(rapport),
        _value_hunter(rapport),
        _loss_cutter(rapport),
        _survived_drawdown(rapport),
        _momentum_ready(rapport),
        _diversified(rapport, diversification),
        _beat_the_market(comparaison),
    ]
    return badges


# ---------- Badges individuels ---------- #


def _first_position(rapport: Rapport) -> Badge:
    n = rapport.nombre_positions
    return Badge(
        id="first_position",
        label="First position",
        description="Own at least one position.",
        unlocked=n >= 1,
        detail=f"{n} position{'s' if n > 1 else ''}",
    )


def _positive_pnl(rapport: Rapport) -> Badge:
    pnl = rapport.gain_absolu
    return Badge(
        id="positive_pnl",
        label="In the green",
        description="Total unrealized PnL is positive.",
        unlocked=pnl > 0,
        detail=f"{pnl:+,.2f}",
    )


def _double_digit_gainer(rapport: Rapport) -> Badge:
    pct = rapport.gain_pct
    return Badge(
        id="double_digit_gainer",
        label="Double-digit gainer",
        description="Total return >= +10%.",
        unlocked=pct >= 10,
        detail=f"{pct:+.1f}%",
    )


def _risk_manager(rapport: Rapport) -> Badge:
    sharpe = rapport.metriques.sharpe if rapport.metriques else None
    unlocked = sharpe is not None and sharpe >= 1.0
    return Badge(
        id="risk_manager",
        label="Risk manager",
        description="Sharpe ratio above 1.0 — return justifies risk.",
        unlocked=unlocked,
        detail=f"Sharpe {sharpe:.2f}" if sharpe is not None else "Not enough history yet",
    )


def _value_hunter(rapport: Rapport) -> Badge:
    pers = [
        ligne.fondamentaux.per
        for ligne in rapport.lignes
        if ligne.fondamentaux and ligne.fondamentaux.per and ligne.fondamentaux.per > 0
    ]
    if not pers:
        return Badge(
            id="value_hunter",
            label="Value hunter",
            description="Average portfolio PER below 15.",
            unlocked=False,
            detail="Add --fondamentaux to check",
        )
    moyenne = sum(pers) / len(pers)
    return Badge(
        id="value_hunter",
        label="Value hunter",
        description="Average portfolio PER below 15.",
        unlocked=moyenne < 15,
        detail=f"Avg PER {moyenne:.1f}",
    )


def _loss_cutter(rapport: Rapport) -> Badge:
    if not rapport.lignes:
        return Badge(
            id="loss_cutter",
            label="Loss cutter",
            description="Stop-loss set on every position.",
            unlocked=False,
            detail="No positions yet",
        )
    couvertes = sum(1 for ligne in rapport.lignes if ligne.position.stop_loss)
    ratio = couvertes / rapport.nombre_positions
    return Badge(
        id="loss_cutter",
        label="Loss cutter",
        description="Stop-loss set on every position.",
        unlocked=ratio == 1.0,
        detail=f"{couvertes}/{rapport.nombre_positions} with stop-loss",
    )


def _survived_drawdown(rapport: Rapport) -> Badge:
    dd = rapport.metriques.max_drawdown_pct if rapport.metriques else None
    unlocked = dd is not None and dd >= 10.0 and rapport.gain_absolu > 0
    return Badge(
        id="survived_drawdown",
        label="Survived a drawdown",
        description="Recovered from a >=10% peak-to-trough decline.",
        unlocked=unlocked,
        detail=(
            f"MaxDD {dd:.1f}%"
            if dd is not None
            else "Not enough history yet"
        ),
    )


def _momentum_ready(rapport: Rapport) -> Badge:
    positions_haussieres = sum(
        1
        for ligne in rapport.lignes
        if ligne.sma_20 is not None
        and ligne.sma_50 is not None
        and ligne.sma_20 > ligne.sma_50
    )
    return Badge(
        id="momentum_ready",
        label="Momentum ready",
        description="At least half of your positions have SMA20 above SMA50.",
        unlocked=(
            rapport.nombre_positions > 0
            and positions_haussieres * 2 >= rapport.nombre_positions
        ),
        detail=f"{positions_haussieres}/{rapport.nombre_positions} bullish crossover",
    )


def _diversified(
    rapport: Rapport, diversification: Diversification | None
) -> Badge:
    n_eff = diversification.positions_effectives if diversification else None
    hhi_pos = rapport.metriques.hhi if rapport.metriques else None
    unlocked = (
        rapport.nombre_positions >= 5
        and hhi_pos is not None
        and hhi_pos <= 2500
    )
    if n_eff is not None:
        detail = f"N_eff {n_eff:.1f}"
    elif hhi_pos is not None:
        detail = f"HHI {hhi_pos:.0f}"
    else:
        detail = "Add more positions"
    return Badge(
        id="diversified",
        label="Diversified",
        description="At least 5 positions with HHI <= 2500 (well-spread).",
        unlocked=unlocked,
        detail=detail,
    )


def _beat_the_market(comparaison: ComparaisonBenchmark | None) -> Badge:
    if comparaison is None:
        return Badge(
            id="beat_the_market",
            label="Beat the market (3M)",
            description="Outperform the benchmark over the last 3 months.",
            unlocked=False,
            detail="Benchmark not configured",
        )
    delta = comparaison.outperformance.get("3M")
    return Badge(
        id="beat_the_market",
        label=f"Beat {comparaison.benchmark} (3M)",
        description=f"Outperform {comparaison.benchmark} over the last 3 months.",
        unlocked=delta is not None and delta > 0,
        detail=(
            f"{delta:+.2f} pts vs {comparaison.benchmark}"
            if delta is not None
            else "Not enough history yet"
        ),
    )

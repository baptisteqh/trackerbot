"""Serialisation du Rapport pour le dashboard, en stdlib uniquement.

L'API HTTP (`api.py`) et la CLI (`cli.py`) doivent produire exactement le
meme JSON : c'est ce qui garantit que le cache ecrit par la CLI et lu
par `GET /rapport` a la meme forme que ce que `POST /refresh` calcule.

Aucune dependance a FastAPI ici : le CLI seul (sans l'extra `[api]`)
doit pouvoir sauvegarder ce payload.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from .achievements import evaluer_badges
from .benchmarks import comparer
from .diversification import calculer_diversification
from .fundamentals import Fondamentaux
from .metrics import serie_equity_portefeuille
from .models import Cotation, Position
from .report import Rapport
from .storage import Deltas


def payload_pour_dashboard(
    rapport: Rapport,
    positions: list[Position],
    cotations: dict[str, Cotation],
    cotation_benchmark: Cotation | None,
    deltas: Deltas,
) -> dict[str, Any]:
    """Construit le dict JSON attendu par le dashboard."""
    equity_data = _equity_series_avec_benchmark(positions, cotations, cotation_benchmark)
    diversification = calculer_diversification(rapport.lignes)
    comparaison = None
    if cotation_benchmark and equity_data["values"] and equity_data["benchmark"]:
        comparaison = comparer(
            equity_data["values"],
            equity_data["benchmark"],
            cotation_benchmark.ticker,
            rapport.genere_le,
        )
    badges = evaluer_badges(rapport, diversification, comparaison)

    donnees: dict[str, Any] = _en_dict(rapport)
    donnees["equity_series"] = equity_data
    donnees["deltas"] = _en_dict(deltas)
    donnees["diversification"] = _en_dict(diversification)
    donnees["comparaison_benchmark"] = _en_dict(comparaison) if comparaison else None
    donnees["badges"] = _en_dict(badges)
    return donnees


def _equity_series_avec_benchmark(
    positions: list[Position],
    cotations: dict[str, Cotation],
    cotation_benchmark: Cotation | None,
) -> dict[str, Any]:
    """values + benchmark aligne sur la fenetre commune, normalise a la base."""
    values = serie_equity_portefeuille(positions, cotations)
    benchmark: list[float] | None = None
    if cotation_benchmark is not None and values and cotation_benchmark.clotures:
        taille = min(len(values), len(cotation_benchmark.clotures))
        if taille >= 1:
            base_bench = cotation_benchmark.clotures[-taille]
            base_port = values[-taille]
            if base_bench > 0 and base_port > 0:
                benchmark = [
                    cotation_benchmark.clotures[-taille + i] / base_bench * base_port
                    for i in range(taille)
                ]
    return {"values": values, "benchmark": benchmark}


def _en_dict(objet: Any) -> Any:
    """Convertit recursivement dataclasses/date/enum en primitives JSON-serialisables."""
    if is_dataclass(objet) and not isinstance(objet, type):
        return {cle: _en_dict(val) for cle, val in asdict(objet).items()}
    if isinstance(objet, dict):
        return {cle: _en_dict(val) for cle, val in objet.items()}
    if isinstance(objet, list | tuple):
        return [_en_dict(item) for item in objet]
    if isinstance(objet, datetime):
        return objet.isoformat()
    if isinstance(objet, date):
        return objet.isoformat()
    if isinstance(objet, Enum):
        return objet.value
    return objet


# Types re-exportes pour que CLI et API n'aient qu'une import a faire.
__all__ = ["payload_pour_dashboard", "Fondamentaux"]

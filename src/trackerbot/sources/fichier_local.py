"""Portefeuille tenu a la main dans un YAML local.

Sert de repli quand aucune cle eToro n'est configuree, et de format de
travail pour tester des scenarios sans toucher au compte reel. Le fichier
vit dans data/, que .gitignore exclut : il ne part jamais sur GitHub.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from ..models import Position


class SourceFichier:
    nom = "fichier local"

    def __init__(self, chemin: Path) -> None:
        self.chemin = chemin

    def positions(self) -> list[Position]:
        if not self.chemin.exists():
            raise FileNotFoundError(
                f"Portefeuille introuvable : {self.chemin}. "
                "Copier portfolio.example.yaml vers ce chemin pour demarrer."
            )
        contenu = yaml.safe_load(self.chemin.read_text(encoding="utf-8")) or {}
        return positions_depuis_dict(contenu)


def positions_depuis_dict(contenu: dict[str, Any]) -> list[Position]:
    """Convertit la structure YAML en positions, avec des erreurs explicites."""
    brutes = contenu.get("positions")
    if brutes is None:
        raise ValueError("Le fichier doit contenir une cle 'positions'.")
    if not isinstance(brutes, list):
        raise ValueError("'positions' doit etre une liste.")

    resultat: list[Position] = []
    for index, brute in enumerate(brutes, start=1):
        if not isinstance(brute, dict):
            raise ValueError(f"Position {index} : entree invalide, un bloc cle/valeur est attendu.")
        manquants = {"ticker", "quantite", "prix_entree"} - brute.keys()
        if manquants:
            champs = ", ".join(sorted(manquants))
            raise ValueError(f"Position {index} : champs manquants ({champs}).")

        ouverte_le = brute.get("ouverte_le")
        if isinstance(ouverte_le, str):
            ouverte_le = date.fromisoformat(ouverte_le)

        resultat.append(
            Position(
                ticker=str(brute["ticker"]).strip().upper(),
                quantite=float(brute["quantite"]),
                prix_entree=float(brute["prix_entree"]),
                est_long=bool(brute.get("est_long", True)),
                stop_loss=_flottant_optionnel(brute.get("stop_loss")),
                take_profit=_flottant_optionnel(brute.get("take_profit")),
                ouverte_le=ouverte_le,
                libelle=brute.get("libelle"),
                source="local",
            )
        )
    return resultat


def _flottant_optionnel(valeur: Any) -> float | None:
    return None if valeur is None else float(valeur)

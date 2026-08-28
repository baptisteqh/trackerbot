"""Contrat commun aux sources de portefeuille."""

from __future__ import annotations

from typing import Protocol

from ..models import Position


class SourcePortefeuille(Protocol):
    """Tout ce que le bot demande a une source : rendre des positions."""

    nom: str

    def positions(self) -> list[Position]:
        """Positions ouvertes, normalisees dans le modele du bot."""
        ...

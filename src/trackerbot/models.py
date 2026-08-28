"""Types du domaine.

Volontairement pauvres en logique : les regles vivent dans signals.py,
les acces reseau dans sources/ et market.py. Ces objets se construisent
a la main dans un test sans toucher au reseau.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class Niveau(StrEnum):
    """Gravite d'un signal, du plus discret au plus urgent."""

    INFO = "info"
    ATTENTION = "attention"
    ALERTE = "alerte"


@dataclass(frozen=True)
class Position:
    """Une ligne du portefeuille, telle que lue chez le courtier ou en local."""

    ticker: str
    quantite: float
    prix_entree: float
    est_long: bool = True
    stop_loss: float | None = None
    take_profit: float | None = None
    ouverte_le: date | None = None
    libelle: str | None = None
    source: str = "local"

    def __post_init__(self) -> None:
        if self.quantite <= 0:
            raise ValueError(f"{self.ticker} : quantite doit etre strictement positive")
        if self.prix_entree <= 0:
            raise ValueError(f"{self.ticker} : prix_entree doit etre strictement positif")

    @property
    def nom(self) -> str:
        return self.libelle or self.ticker

    def valeur(self, prix: float) -> float:
        return self.quantite * prix

    def montant_investi(self) -> float:
        return self.quantite * self.prix_entree

    def gain_pct(self, prix: float) -> float:
        """Rendement en pourcentage, signe selon le sens de la position."""
        brut = (prix - self.prix_entree) / self.prix_entree * 100.0
        return brut if self.est_long else -brut

    def gain_absolu(self, prix: float) -> float:
        brut = (prix - self.prix_entree) * self.quantite
        return brut if self.est_long else -brut


@dataclass(frozen=True)
class Cotation:
    """Prix courant et historique de cloture, du plus ancien au plus recent."""

    ticker: str
    prix: float
    clotures: list[float] = field(default_factory=list)
    devise: str = "USD"

    @property
    def cloture_precedente(self) -> float | None:
        return self.clotures[-2] if len(self.clotures) >= 2 else None

    @property
    def variation_jour_pct(self) -> float | None:
        veille = self.cloture_precedente
        if veille is None or veille == 0:
            return None
        return (self.prix - veille) / veille * 100.0


@dataclass(frozen=True)
class Signal:
    """Une observation datee sur une position. Jamais un ordre a passer."""

    ticker: str
    niveau: Niveau
    regle: str
    message: str

    def __str__(self) -> str:
        return f"[{self.niveau.value}] {self.ticker} : {self.message}"

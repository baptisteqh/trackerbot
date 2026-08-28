"""Rapport de portefeuille : agrege positions, cotations et signaux.

Ce module ne fait aucun appel reseau. Il recoit des positions, des
cotations et, optionnellement, des signaux et une veille de marche, puis
construit une representation neutre du portefeuille (poids, PnL latente,
volatilite) ainsi qu'un rendu texte adapte a la console et a Telegram.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .indicators import rsi, sma, volatilite_pct
from .models import Cotation, Niveau, Position, Signal
from .research import Veille


@dataclass(frozen=True)
class LignePortefeuille:
    """Une position enrichie des metriques calculees a partir de sa cotation."""

    position: Position
    cotation: Cotation | None
    poids_pct: float
    valeur_courante: float
    montant_investi: float
    gain_absolu: float
    gain_pct: float
    rsi_14: float | None
    sma_20: float | None
    sma_50: float | None
    volatilite_20j_pct: float | None

    @property
    def ticker(self) -> str:
        return self.position.ticker

    @property
    def cotee(self) -> bool:
        return self.cotation is not None


@dataclass(frozen=True)
class Rapport:
    """Etat instantane du portefeuille, pret a etre imprime ou envoye."""

    genere_le: date
    lignes: list[LignePortefeuille]
    signaux: list[Signal]
    veille: Veille | None = None
    tickers_manquants: list[str] = field(default_factory=list)

    @property
    def montant_investi(self) -> float:
        return sum(ligne.montant_investi for ligne in self.lignes)

    @property
    def valeur_courante(self) -> float:
        return sum(ligne.valeur_courante for ligne in self.lignes)

    @property
    def gain_absolu(self) -> float:
        return self.valeur_courante - self.montant_investi

    @property
    def gain_pct(self) -> float:
        base = self.montant_investi
        return 0.0 if base == 0 else (self.gain_absolu / base) * 100.0

    @property
    def nombre_positions(self) -> int:
        return len(self.lignes)

    def signaux_par_niveau(self, niveau: Niveau) -> list[Signal]:
        return [s for s in self.signaux if s.niveau is niveau]


def construire_rapport(
    positions: list[Position],
    cotations: dict[str, Cotation],
    signaux: list[Signal] | None = None,
    veille: Veille | None = None,
    aujourdhui: date | None = None,
) -> Rapport:
    """Rassemble tout dans un objet Rapport sans effet de bord."""
    valeurs = _valeurs_courantes(positions, cotations)
    total = sum(valeurs.values()) or 0.0
    lignes: list[LignePortefeuille] = []

    for position in positions:
        cotation = cotations.get(position.ticker)
        valeur = valeurs.get(position.ticker, 0.0)
        poids = 0.0 if total == 0 else (valeur / total) * 100.0
        prix_reference = cotation.prix if cotation is not None else position.prix_entree
        clotures = cotation.clotures if cotation is not None else []

        lignes.append(
            LignePortefeuille(
                position=position,
                cotation=cotation,
                poids_pct=poids,
                valeur_courante=valeur,
                montant_investi=position.montant_investi(),
                gain_absolu=position.gain_absolu(prix_reference),
                gain_pct=position.gain_pct(prix_reference),
                rsi_14=rsi(clotures, 14),
                sma_20=sma(clotures, 20),
                sma_50=sma(clotures, 50),
                volatilite_20j_pct=volatilite_pct(clotures, 20),
            )
        )

    manquants = sorted(
        {p.ticker for p in positions if cotations.get(p.ticker) is None}
    )
    return Rapport(
        genere_le=aujourdhui or date.today(),
        lignes=lignes,
        signaux=signaux or [],
        veille=veille,
        tickers_manquants=manquants,
    )


def _valeurs_courantes(
    positions: list[Position], cotations: dict[str, Cotation]
) -> dict[str, float]:
    valeurs: dict[str, float] = {}
    for position in positions:
        cotation = cotations.get(position.ticker)
        prix = cotation.prix if cotation is not None else position.prix_entree
        valeurs[position.ticker] = position.valeur(prix)
    return valeurs


def formater_rapport(rapport: Rapport) -> str:
    """Rendu texte compact du rapport, lisible en console comme sur Telegram."""
    lignes: list[str] = []
    lignes.append(f"Portefeuille au {rapport.genere_le.isoformat()}")
    lignes.append(
        f"Investi {rapport.montant_investi:.2f} | "
        f"Valeur {rapport.valeur_courante:.2f} | "
        f"PnL {rapport.gain_absolu:+.2f} ({rapport.gain_pct:+.2f} %)"
    )
    lignes.append(f"{rapport.nombre_positions} position(s)")

    if rapport.tickers_manquants:
        manquants = ", ".join(rapport.tickers_manquants)
        lignes.append(f"Cotations manquantes : {manquants}")

    lignes.append("")
    lignes.append("Positions :")
    for ligne in sorted(rapport.lignes, key=lambda x: x.poids_pct, reverse=True):
        lignes.append(_formater_ligne(ligne))

    lignes.append("")
    if rapport.signaux:
        lignes.append("Signaux :")
        for signal in rapport.signaux:
            lignes.append(f"  {signal}")
    else:
        lignes.append("Aucun signal declenche.")

    if rapport.veille is not None:
        lignes.append("")
        lignes.append("Veille de marche :")
        lignes.append(rapport.veille.texte)
        if rapport.veille.sources:
            lignes.append("Sources :")
            for source in rapport.veille.sources:
                lignes.append(f"  - {source}")

    return "\n".join(lignes)


def _formater_ligne(ligne: LignePortefeuille) -> str:
    sens = "L" if ligne.position.est_long else "S"
    prix = ligne.cotation.prix if ligne.cotation is not None else ligne.position.prix_entree
    marqueur = "" if ligne.cotee else " (cotation manquante)"
    rsi_val = f"{ligne.rsi_14:.0f}" if ligne.rsi_14 is not None else "-"
    vol_val = (
        f"{ligne.volatilite_20j_pct:.1f}%" if ligne.volatilite_20j_pct is not None else "-"
    )
    return (
        f"  {ligne.ticker} [{sens}] {ligne.position.quantite:g} @ "
        f"{ligne.position.prix_entree:.2f} -> {prix:.2f}{marqueur} | "
        f"poids {ligne.poids_pct:.1f}% | PnL {ligne.gain_absolu:+.2f} "
        f"({ligne.gain_pct:+.2f}%) | RSI {rsi_val} | vol20 {vol_val}"
    )

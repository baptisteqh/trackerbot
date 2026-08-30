"""Rapport de portefeuille : agrege positions, cotations et signaux.

Ce module ne fait aucun appel reseau. Il recoit des positions, des
cotations et, optionnellement, des signaux et une veille de marche, puis
construit une representation neutre du portefeuille (poids, PnL latente,
volatilite) ainsi qu'un rendu texte adapte a la console et a Telegram.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .fundamentals import Fondamentaux
from .indicators import rsi, sma, volatilite_pct
from .metrics import MetriquesPortefeuille, calculer_metriques
from .models import Cotation, Niveau, Position, Signal
from .research import Veille
from .valuation import ScoreValorisation, scorer


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
    fondamentaux: Fondamentaux | None = None
    score_valorisation: ScoreValorisation | None = None

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
    metriques: MetriquesPortefeuille | None = None

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
    cotation_benchmark: Cotation | None = None,
    fondamentaux: dict[str, Fondamentaux] | None = None,
) -> Rapport:
    """Rassemble tout dans un objet Rapport sans effet de bord."""
    valeurs = _valeurs_courantes(positions, cotations)
    total = sum(valeurs.values()) or 0.0
    fonds = fondamentaux or {}
    lignes: list[LignePortefeuille] = []

    for position in positions:
        cotation = cotations.get(position.ticker)
        valeur = valeurs.get(position.ticker, 0.0)
        poids = 0.0 if total == 0 else (valeur / total) * 100.0
        prix_reference = cotation.prix if cotation is not None else position.prix_entree
        clotures = cotation.clotures if cotation is not None else []
        fond = fonds.get(position.ticker)

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
                fondamentaux=fond,
                score_valorisation=scorer(fond) if fond is not None else None,
            )
        )

    manquants = sorted(
        {p.ticker for p in positions if cotations.get(p.ticker) is None}
    )
    metriques = calculer_metriques(
        positions,
        cotations,
        [ligne.poids_pct for ligne in lignes],
        cotation_benchmark=cotation_benchmark,
    )
    return Rapport(
        genere_le=aujourdhui or date.today(),
        lignes=lignes,
        signaux=signaux or [],
        veille=veille,
        tickers_manquants=manquants,
        metriques=metriques,
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

    if rapport.metriques is not None:
        bloc = _formater_metriques(rapport.metriques)
        if bloc:
            lignes.append("")
            lignes.extend(bloc)

    lignes.append("")
    lignes.append("Positions :")
    for ligne in sorted(rapport.lignes, key=lambda x: x.poids_pct, reverse=True):
        lignes.append(_formater_ligne(ligne))

    bloc_valorisation = _formater_valorisations(rapport.lignes)
    if bloc_valorisation:
        lignes.append("")
        lignes.extend(bloc_valorisation)

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


def _formater_metriques(m: MetriquesPortefeuille) -> list[str]:
    """Rendu compact ; on n'affiche que ce qui est mesurable."""
    risque = _joindre(
        _optionnel("Sharpe", m.sharpe, "{:.2f}"),
        _optionnel("Sortino", m.sortino, "{:.2f}"),
        _optionnel("Calmar", m.calmar, "{:.2f}"),
        _optionnel("Vol", m.volatilite_annuelle_pct, "{:.1f}%"),
        _optionnel("Rdmt", m.rendement_annuel_pct, "{:+.1f}%"),
        _optionnel("MaxDD", m.max_drawdown_pct, "{:.1f}%"),
        _optionnel("VaR95", m.var_95_pct, "{:.1f}%"),
    )
    concentration = _joindre(
        _optionnel("HHI", m.hhi, "{:.0f}"),
        _optionnel("plus grosse", m.plus_grosse_position_pct, "{:.1f}%"),
    )
    marche = _joindre(
        (
            f"Beta vs {m.benchmark} : {m.beta:.2f}"
            if m.beta is not None and m.benchmark is not None
            else None
        ),
        _optionnel("Alpha", m.alpha_annuel_pct, "{:+.1f}%"),
        _optionnel("IR", m.information_ratio, "{:.2f}"),
    )
    corps = [ligne for ligne in (risque, concentration, marche) if ligne]
    return ["Metriques :", *(f"  {ligne}" for ligne in corps)] if corps else []


def _optionnel(libelle: str, valeur: float | None, fmt: str) -> str | None:
    return f"{libelle} {fmt.format(valeur)}" if valeur is not None else None


def _joindre(*parts: str | None) -> str:
    return " | ".join(p for p in parts if p)


def _formater_valorisations(lignes: list[LignePortefeuille]) -> list[str]:
    """Une ligne par ticker qui a un score, sinon rien du tout."""
    avec_score = [
        ligne for ligne in lignes if ligne.score_valorisation is not None
    ]
    if not avec_score:
        return []
    avec_score.sort(
        key=lambda ligne: ligne.score_valorisation.score if ligne.score_valorisation else 0,
        reverse=True,
    )
    return [
        "Valorisation :",
        *(f"  {_formater_valorisation(ligne)}" for ligne in avec_score),
    ]


def _formater_valorisation(ligne: LignePortefeuille) -> str:
    score = ligne.score_valorisation
    fond = ligne.fondamentaux
    assert score is not None and fond is not None  # garanti par le filtre appelant
    parts = _joindre(
        _optionnel("PER", fond.per, "{:.1f}"),
        _optionnel("PB", fond.price_to_book, "{:.1f}"),
        _optionnel("marge", fond.marge_nette_pct, "{:.1f}%"),
        _optionnel("D/E", fond.debt_to_equity, "{:.2f}"),
        _optionnel("ROE", fond.roe_pct, "{:.1f}%"),
    )
    return f"{ligne.ticker} score {score.score}/{score.maximum} | {parts}" if parts else (
        f"{ligne.ticker} score {score.score}/{score.maximum}"
    )


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

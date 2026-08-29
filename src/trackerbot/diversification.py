"""Analyse de diversification portefeuille.

On calcule ici les indicateurs qu'un jeune investisseur devrait regarder
avant de faire "yolo" sur 3 tech mega-caps :

- Exposition par secteur (agregee depuis les fondamentaux Yahoo).
- Positions effectives `N_eff = 1 / sum(w_i^2)` — dit combien de
  positions vraiment independantes tu as. Un portefeuille de 20 lignes
  ou 4 pesent 80 % a un N_eff proche de 4, pas 20.
- Ratio de diversification `DR = sum(w_i * sigma_i) / sigma_portefeuille`.
  > 1 signifie que la diversification reduit vraiment la volatilite ;
  proche de 1 signifie que tes positions bougent ensemble et que ta
  diversification est illusoire.
- Matrice de correlation par paires : moyenne pondere pour un indicateur
  synthetique, plus une liste des paires trop correlees.

Fonctions pures sur des LignePortefeuille. Aucun reseau, aucun IO.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .metrics import rendements_journaliers
from .report import LignePortefeuille

SEUIL_CONCENTRATION_SECTEUR_PCT = 40.0
SEUIL_CORRELATION_ELEVEE = 0.85
SEUIL_POSITION_SIGNIFICATIVE_PCT = 5.0  # au-dessous, on ignore pour les alertes de correlation


@dataclass(frozen=True)
class PaireCorrelation:
    ticker_a: str
    ticker_b: str
    correlation: float


@dataclass(frozen=True)
class Diversification:
    """Instantane de la diversification portefeuille."""

    poids_par_secteur: dict[str, float] = field(default_factory=dict)
    hhi_secteurs: float | None = None
    plus_gros_secteur: str | None = None
    plus_gros_secteur_pct: float | None = None
    positions_effectives: float | None = None
    ratio_diversification: float | None = None
    correlation_moyenne: float | None = None
    paires_correlees: tuple[PaireCorrelation, ...] = ()

    @property
    def secteur_surconcentre(self) -> bool:
        return (
            self.plus_gros_secteur_pct is not None
            and self.plus_gros_secteur_pct >= SEUIL_CONCENTRATION_SECTEUR_PCT
        )


def calculer_diversification(lignes: list[LignePortefeuille]) -> Diversification:
    """Rassemble tous les indicateurs de diversification dans un seul objet."""
    if not lignes:
        return Diversification()

    poids_secteurs = _poids_par_secteur(lignes)
    hhi = sum(p * p for p in poids_secteurs.values()) if poids_secteurs else None
    plus_gros = max(poids_secteurs.items(), key=lambda kv: kv[1]) if poids_secteurs else None

    n_eff = _positions_effectives(lignes)
    dr = _ratio_diversification(lignes)
    corr_moy, paires = _correlations(lignes)

    return Diversification(
        poids_par_secteur=poids_secteurs,
        hhi_secteurs=hhi,
        plus_gros_secteur=plus_gros[0] if plus_gros else None,
        plus_gros_secteur_pct=plus_gros[1] if plus_gros else None,
        positions_effectives=n_eff,
        ratio_diversification=dr,
        correlation_moyenne=corr_moy,
        paires_correlees=paires,
    )


def _poids_par_secteur(lignes: list[LignePortefeuille]) -> dict[str, float]:
    """Somme des poids_pct par secteur (fondamentaux). 'Unknown' quand absent."""
    totaux: dict[str, float] = {}
    for ligne in lignes:
        if ligne.poids_pct <= 0:
            continue
        secteur = (ligne.fondamentaux.secteur if ligne.fondamentaux else None) or "Unknown"
        totaux[secteur] = totaux.get(secteur, 0.0) + ligne.poids_pct
    return dict(sorted(totaux.items(), key=lambda kv: kv[1], reverse=True))


def _positions_effectives(lignes: list[LignePortefeuille]) -> float | None:
    """N_eff = 1 / sum(w_i^2) avec w_i en fraction (pas en pourcentage)."""
    fractions = [ligne.poids_pct / 100.0 for ligne in lignes if ligne.poids_pct > 0]
    if not fractions:
        return None
    somme_carres = sum(f * f for f in fractions)
    return 1.0 / somme_carres if somme_carres > 0 else None


def _ratio_diversification(lignes: list[LignePortefeuille]) -> float | None:
    """DR = sum(w_i * sigma_i) / sigma_portefeuille sur les rendements journaliers.

    Renvoie None quand au moins une position n'a pas de vol calculable ou
    que la fenetre commune est trop courte pour agreger.
    """
    cotations = [(ligne, ligne.cotation) for ligne in lignes if ligne.cotation]
    if len(cotations) < 2:
        return None

    fenetre = min(len(c.clotures) for _, c in cotations)
    if fenetre < 3:
        return None

    somme_ponderee: float = 0.0
    fractions: list[tuple[float, list[float]]] = []
    for ligne, cotation in cotations:
        clotures_alignees = cotation.clotures[-fenetre:]
        rendements = rendements_journaliers(clotures_alignees)
        vol = _ecart_type(rendements)
        if vol is None:
            return None
        w = ligne.poids_pct / 100.0
        somme_ponderee += w * vol
        fractions.append((w, clotures_alignees))

    equity = _combiner(fractions)
    vol_portefeuille = _ecart_type(rendements_journaliers(equity))
    if vol_portefeuille is None or vol_portefeuille == 0:
        return None
    return somme_ponderee / vol_portefeuille


def _correlations(
    lignes: list[LignePortefeuille],
) -> tuple[float | None, tuple[PaireCorrelation, ...]]:
    """Moyenne des correlations pondere par w_i*w_j + paires jugees elevees."""
    cotations = [
        (ligne.position.ticker, ligne.poids_pct, ligne.cotation)
        for ligne in lignes
        if ligne.cotation and ligne.cotation.clotures
    ]
    if len(cotations) < 2:
        return None, ()

    fenetre = min(len(c.clotures) for _, _, c in cotations)
    if fenetre < 3:
        return None, ()

    rendements: dict[str, list[float]] = {}
    for ticker, _, cotation in cotations:
        rendements[ticker] = rendements_journaliers(cotation.clotures[-fenetre:])

    total_poids = 0.0
    somme_ponderee = 0.0
    paires: list[PaireCorrelation] = []
    poids_par_ticker = {ticker: w for ticker, w, _ in cotations}

    tickers = list(rendements.keys())
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            a, b = tickers[i], tickers[j]
            rho = _correlation(rendements[a], rendements[b])
            if rho is None:
                continue
            w_ab = (poids_par_ticker[a] * poids_par_ticker[b]) / 10000.0
            somme_ponderee += rho * w_ab
            total_poids += w_ab
            if (
                abs(rho) >= SEUIL_CORRELATION_ELEVEE
                and poids_par_ticker[a] >= SEUIL_POSITION_SIGNIFICATIVE_PCT
                and poids_par_ticker[b] >= SEUIL_POSITION_SIGNIFICATIVE_PCT
            ):
                paires.append(PaireCorrelation(ticker_a=a, ticker_b=b, correlation=rho))

    moyenne = somme_ponderee / total_poids if total_poids > 0 else None
    paires.sort(key=lambda p: abs(p.correlation), reverse=True)
    return moyenne, tuple(paires)


def _combiner(fractions: list[tuple[float, list[float]]]) -> list[float]:
    """Combine des series de meme longueur en une equity ponderee (base 100)."""
    longueur = len(fractions[0][1])
    combine: list[float] = []
    for i in range(longueur):
        valeur = 0.0
        for w, closes in fractions:
            valeur += w * closes[i]
        combine.append(valeur)
    return combine


def _ecart_type(valeurs: list[float]) -> float | None:
    if len(valeurs) < 2:
        return None
    moyenne = sum(valeurs) / len(valeurs)
    variance = sum((v - moyenne) ** 2 for v in valeurs) / (len(valeurs) - 1)
    return math.sqrt(variance)


def _correlation(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    num = sum((av - ma) * (bv - mb) for av, bv in zip(a, b, strict=True))
    denom_a = math.sqrt(sum((av - ma) ** 2 for av in a))
    denom_b = math.sqrt(sum((bv - mb) ** 2 for bv in b))
    if denom_a == 0 or denom_b == 0:
        return None
    return num / (denom_a * denom_b)

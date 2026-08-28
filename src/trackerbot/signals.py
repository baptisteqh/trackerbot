"""Regles de surveillance appliquees a une position.

Chaque regle est une fonction pure : une position, sa cotation, des
seuils, et rien d'autre. C'est ce qui permet de les tester sans reseau
et de les modifier sans casser le reste.

Un signal decrit ce qui s'est produit sur le marche. Il ne dit jamais
d'acheter ou de vendre, et le bot ne passe aucun ordre.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .indicators import (
    croisement,
    repli_depuis_plus_haut_pct,
    rsi,
    serie_sma,
)
from .models import Cotation, Niveau, Position, Signal


@dataclass(frozen=True)
class Seuils:
    """Parametres des regles. Modifiables sans toucher au code des regles."""

    approche_stop_pct: float = 3.0
    repli_attention_pct: float = 10.0
    repli_alerte_pct: float = 20.0
    fenetre_repli: int = 90
    rsi_periode: int = 14
    rsi_surachat: float = 70.0
    rsi_survente: float = 30.0
    sma_rapide: int = 20
    sma_lente: int = 50
    variation_jour_pct: float = 5.0
    gain_notable_pct: float = 25.0
    perte_notable_pct: float = 15.0


Regle = Callable[[Position, Cotation, Seuils], Signal | None]


def regle_stop_loss(position: Position, cotation: Cotation, seuils: Seuils) -> Signal | None:
    """Stop touche, ou prix arrive a portee du stop."""
    if position.stop_loss is None:
        return None
    prix, stop = cotation.prix, position.stop_loss

    touche = prix <= stop if position.est_long else prix >= stop
    if touche:
        return Signal(
            ticker=position.ticker,
            niveau=Niveau.ALERTE,
            regle="stop_loss",
            message=f"stop a {stop:.2f} franchi, le prix est a {prix:.2f}",
        )

    distance_pct = abs(prix - stop) / prix * 100.0
    if distance_pct <= seuils.approche_stop_pct:
        return Signal(
            ticker=position.ticker,
            niveau=Niveau.ATTENTION,
            regle="stop_loss_approche",
            message=f"a {distance_pct:.1f} % du stop ({stop:.2f})",
        )
    return None


def regle_take_profit(position: Position, cotation: Cotation, seuils: Seuils) -> Signal | None:
    """Objectif de prix atteint."""
    if position.take_profit is None:
        return None
    cible = position.take_profit
    atteint = cotation.prix >= cible if position.est_long else cotation.prix <= cible
    if not atteint:
        return None
    return Signal(
        ticker=position.ticker,
        niveau=Niveau.ALERTE,
        regle="take_profit",
        message=f"objectif de {cible:.2f} atteint, prix a {cotation.prix:.2f}",
    )


def regle_repli(position: Position, cotation: Cotation, seuils: Seuils) -> Signal | None:
    """Recul marque depuis le plus haut recent."""
    repli = repli_depuis_plus_haut_pct(cotation.clotures, seuils.fenetre_repli)
    if repli is None:
        return None
    if repli >= seuils.repli_alerte_pct:
        niveau = Niveau.ALERTE
    elif repli >= seuils.repli_attention_pct:
        niveau = Niveau.ATTENTION
    else:
        return None
    return Signal(
        ticker=position.ticker,
        niveau=niveau,
        regle="repli",
        message=(
            f"{repli:.1f} % sous le plus haut des {seuils.fenetre_repli} dernieres seances"
        ),
    )


def regle_rsi(position: Position, cotation: Cotation, seuils: Seuils) -> Signal | None:
    """Zones de surachat et de survente."""
    valeur = rsi(cotation.clotures, seuils.rsi_periode)
    if valeur is None:
        return None
    if valeur >= seuils.rsi_surachat:
        return Signal(
            ticker=position.ticker,
            niveau=Niveau.INFO,
            regle="rsi_surachat",
            message=f"RSI a {valeur:.0f}, zone de surachat",
        )
    if valeur <= seuils.rsi_survente:
        return Signal(
            ticker=position.ticker,
            niveau=Niveau.INFO,
            regle="rsi_survente",
            message=f"RSI a {valeur:.0f}, zone de survente",
        )
    return None


def regle_croisement_moyennes(
    position: Position, cotation: Cotation, seuils: Seuils
) -> Signal | None:
    """Croisement des moyennes mobiles rapide et lente."""
    rapide = serie_sma(cotation.clotures, seuils.sma_rapide)
    lente = serie_sma(cotation.clotures, seuils.sma_lente)
    if not rapide or not lente:
        return None
    # Aligner les deux series sur leurs dates communes, les plus recentes.
    taille = min(len(rapide), len(lente))
    sens = croisement(rapide[-taille:], lente[-taille:])
    if sens is None:
        return None
    libelle = "au-dessus de" if sens == "haussier" else "sous"
    return Signal(
        ticker=position.ticker,
        niveau=Niveau.ATTENTION,
        regle=f"croisement_{sens}",
        message=(
            f"la moyenne {seuils.sma_rapide} jours est passee {libelle} "
            f"la moyenne {seuils.sma_lente} jours"
        ),
    )


def regle_variation_jour(
    position: Position, cotation: Cotation, seuils: Seuils
) -> Signal | None:
    """Mouvement brutal sur une seule seance."""
    variation = cotation.variation_jour_pct
    if variation is None or abs(variation) < seuils.variation_jour_pct:
        return None
    sens = "hausse" if variation > 0 else "baisse"
    return Signal(
        ticker=position.ticker,
        niveau=Niveau.ATTENTION,
        regle="variation_jour",
        message=f"{sens} de {abs(variation):.1f} % sur la seance",
    )


def regle_performance(position: Position, cotation: Cotation, seuils: Seuils) -> Signal | None:
    """Gain ou perte latente sortant de l'ordinaire."""
    gain = position.gain_pct(cotation.prix)
    if gain >= seuils.gain_notable_pct:
        return Signal(
            ticker=position.ticker,
            niveau=Niveau.INFO,
            regle="gain_notable",
            message=f"gain latent de {gain:.1f} %",
        )
    if gain <= -seuils.perte_notable_pct:
        return Signal(
            ticker=position.ticker,
            niveau=Niveau.ATTENTION,
            regle="perte_notable",
            message=f"perte latente de {abs(gain):.1f} %",
        )
    return None


REGLES: tuple[Regle, ...] = (
    regle_stop_loss,
    regle_take_profit,
    regle_repli,
    regle_variation_jour,
    regle_croisement_moyennes,
    regle_rsi,
    regle_performance,
)

_ORDRE = {Niveau.ALERTE: 0, Niveau.ATTENTION: 1, Niveau.INFO: 2}


def evaluer(
    position: Position,
    cotation: Cotation,
    seuils: Seuils | None = None,
    regles: tuple[Regle, ...] = REGLES,
) -> list[Signal]:
    """Applique toutes les regles a une position, du plus grave au moins grave."""
    parametres = seuils or Seuils()
    trouves = [signal for regle in regles if (signal := regle(position, cotation, parametres))]
    return sorted(trouves, key=lambda s: _ORDRE[s.niveau])


def evaluer_portefeuille(
    positions: list[Position],
    cotations: dict[str, Cotation],
    seuils: Seuils | None = None,
) -> list[Signal]:
    """Evalue chaque position dont la cotation est connue."""
    resultats: list[Signal] = []
    for position in positions:
        cotation = cotations.get(position.ticker)
        if cotation is None:
            continue
        resultats.extend(evaluer(position, cotation, seuils))
    return sorted(resultats, key=lambda s: _ORDRE[s.niveau])

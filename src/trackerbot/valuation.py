"""Score de valorisation type Graham/Buffett-lite.

Pure : recoit un `Fondamentaux`, renvoie un `ScoreValorisation`. Aucune
donnee historique, aucun reseau. Sept criteres binaires, un point par
critere rempli. Sept criteres et pas neuf comme Piotroski parce que ce
dernier a besoin de l'historique de plusieurs annees, que Yahoo ne
donne pas toujours proprement via `.info`.

Les seuils sont expliques dans le dataclass Seuils, faciles a ajuster
sans toucher au reste du code (comme signals.Seuils).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .fundamentals import Fondamentaux


@dataclass(frozen=True)
class SeuilsValorisation:
    """Seuils du scoring. Modifiables sans changer les regles."""

    per_max: float = 15.0  # PER faible -> action pas chere
    pb_max: float = 1.5  # PB < 1.5 = valeur proche des fonds propres
    marge_nette_min_pct: float = 10.0
    debt_to_equity_max: float = 1.0
    roe_min_pct: float = 10.0
    croissance_revenus_min_pct: float = 5.0
    # Le dividende n'a pas de seuil : le simple fait d'en verser un compte.


@dataclass(frozen=True)
class ScoreValorisation:
    """Score et detail des criteres remplis. Max 7."""

    ticker: str
    score: int
    criteres_remplis: tuple[str, ...] = field(default_factory=tuple)
    criteres_manquants: tuple[str, ...] = field(default_factory=tuple)
    inconnus: tuple[str, ...] = field(default_factory=tuple)

    @property
    def maximum(self) -> int:
        return 7

    @property
    def score_sur_donnees_connues(self) -> float | None:
        """Score ramene aux seuls criteres testables (utile si Yahoo ment ou manque)."""
        connus = self.maximum - len(self.inconnus)
        return None if connus == 0 else self.score / connus * self.maximum


def scorer(
    fondamentaux: Fondamentaux, seuils: SeuilsValorisation | None = None
) -> ScoreValorisation:
    """Renvoie le score et le detail par critere."""
    s = seuils or SeuilsValorisation()
    remplis: list[str] = []
    manquants: list[str] = []
    inconnus: list[str] = []

    for nom, verdict in _criteres(fondamentaux, s):
        if verdict is None:
            inconnus.append(nom)
        elif verdict:
            remplis.append(nom)
        else:
            manquants.append(nom)

    return ScoreValorisation(
        ticker=fondamentaux.ticker,
        score=len(remplis),
        criteres_remplis=tuple(remplis),
        criteres_manquants=tuple(manquants),
        inconnus=tuple(inconnus),
    )


def _criteres(f: Fondamentaux, s: SeuilsValorisation) -> list[tuple[str, bool | None]]:
    """Liste des criteres : (nom, verdict). None quand la donnee manque."""
    return [
        ("per_faible", _test_max(f.per, s.per_max, strict_positif=True)),
        ("pb_faible", _test_max(f.price_to_book, s.pb_max, strict_positif=True)),
        ("marge_nette_correcte", _test_min(f.marge_nette_pct, s.marge_nette_min_pct)),
        ("dette_maitrisee", _test_max(f.debt_to_equity, s.debt_to_equity_max)),
        ("roe_correct", _test_min(f.roe_pct, s.roe_min_pct)),
        ("croissance_positive", _test_min(f.croissance_revenus_pct, s.croissance_revenus_min_pct)),
        ("verse_dividende", None if f.dividend_yield_pct is None else f.dividend_yield_pct > 0),
    ]


def _test_min(valeur: float | None, seuil: float) -> bool | None:
    """Vrai quand la valeur atteint le seuil. None si valeur inconnue."""
    return None if valeur is None else valeur >= seuil


def _test_max(
    valeur: float | None, seuil: float, strict_positif: bool = False
) -> bool | None:
    """Vrai quand la valeur reste sous le seuil.

    Pour PER et PB on exige aussi valeur > 0 : un PER negatif ne
    signifie pas "pas cher" mais "perd de l'argent".
    """
    if valeur is None:
        return None
    if strict_positif and valeur <= 0:
        return False
    return valeur <= seuil

"""Tests du scoring de valorisation, offline et deterministes."""

from __future__ import annotations

import pytest

from trackerbot.fundamentals import Fondamentaux
from trackerbot.valuation import SeuilsValorisation, scorer


def _fondamentaux_ideaux() -> Fondamentaux:
    """Cas parfait : tous les criteres remplis."""
    return Fondamentaux(
        ticker="AAA",
        per=10.0,
        price_to_book=1.0,
        marge_nette_pct=20.0,
        debt_to_equity=0.5,
        roe_pct=15.0,
        dividend_yield_pct=2.0,
        croissance_revenus_pct=10.0,
    )


class TestScorer:
    def test_score_maximum_quand_tout_est_ideal(self) -> None:
        score = scorer(_fondamentaux_ideaux())
        assert score.score == 7
        assert score.maximum == 7
        assert not score.criteres_manquants
        assert not score.inconnus

    def test_score_zero_sur_valeurs_medioctes(self) -> None:
        f = Fondamentaux(
            ticker="AAA",
            per=40.0,  # trop cher
            price_to_book=5.0,
            marge_nette_pct=2.0,
            debt_to_equity=3.0,
            roe_pct=3.0,
            dividend_yield_pct=0.0,  # pas de dividende
            croissance_revenus_pct=-2.0,  # decroissance
        )
        assert scorer(f).score == 0

    def test_per_negatif_ne_compte_pas_comme_pas_cher(self) -> None:
        # Piege classique : PER negatif = entreprise qui perd de l'argent, pas une bonne affaire.
        f = Fondamentaux(ticker="AAA", per=-5.0, price_to_book=1.0)
        result = scorer(f)
        assert "per_faible" in result.criteres_manquants
        assert "pb_faible" in result.criteres_remplis

    def test_champs_none_finissent_dans_inconnus(self) -> None:
        # Uniquement PER connu (et bon) : score = 1, 6 criteres inconnus.
        f = Fondamentaux(ticker="AAA", per=10.0)
        result = scorer(f)
        assert result.score == 1
        assert result.criteres_remplis == ("per_faible",)
        assert len(result.inconnus) == 6

    def test_score_sur_donnees_connues(self) -> None:
        # 1 critere connu (PER) et rempli sur 7 criteres possibles.
        f = Fondamentaux(ticker="AAA", per=10.0)
        result = scorer(f)
        # 1 rempli / 1 connu * 7 = 7.0
        assert result.score_sur_donnees_connues == pytest.approx(7.0)

    def test_score_sur_donnees_connues_none_quand_rien(self) -> None:
        result = scorer(Fondamentaux(ticker="AAA"))
        assert result.score_sur_donnees_connues is None

    def test_seuils_personnalises(self) -> None:
        # Meme fondamentaux mais on serre les seuils : le PER de 10 passe encore,
        # le PB de 1.0 aussi, mais la marge nette de 20% ne suffit plus a 30%.
        seuils = SeuilsValorisation(marge_nette_min_pct=30.0)
        result = scorer(_fondamentaux_ideaux(), seuils)
        assert "marge_nette_correcte" in result.criteres_manquants
        assert result.score == 6

    def test_dividende_a_zero_compte_comme_absent(self) -> None:
        f = Fondamentaux(ticker="AAA", dividend_yield_pct=0.0)
        result = scorer(f)
        assert "verse_dividende" in result.criteres_manquants

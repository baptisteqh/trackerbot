"""Tests des indicateurs techniques : ce sont les seuls chiffres exacts du bot."""

from __future__ import annotations

import pytest

from trackerbot.indicators import (
    croisement,
    plus_haut,
    repli_depuis_plus_haut_pct,
    rsi,
    serie_sma,
    sma,
    volatilite_pct,
)


class TestSma:
    def test_moyenne_sur_toute_la_fenetre(self) -> None:
        assert sma([1, 2, 3, 4, 5], 5) == 3.0

    def test_derniere_fenetre_uniquement(self) -> None:
        assert sma([1, 2, 3, 4, 5], 3) == pytest.approx(4.0)

    def test_serie_trop_courte_renvoie_none(self) -> None:
        assert sma([1, 2], 5) is None

    def test_periode_invalide(self) -> None:
        with pytest.raises(ValueError):
            sma([1, 2, 3], 0)


class TestRsi:
    def test_hausse_stricte_donne_100(self) -> None:
        valeur = rsi([float(x) for x in range(1, 20)], periode=14)
        assert valeur == 100.0

    def test_stagnation_donne_environ_50(self) -> None:
        valeurs = [10.0, 11.0, 10.0, 11.0] * 5
        resultat = rsi(valeurs, periode=14)
        assert resultat is not None
        assert 45.0 <= resultat <= 55.0

    def test_serie_trop_courte(self) -> None:
        assert rsi([1.0, 2.0], periode=14) is None


class TestPlusHautEtRepli:
    def test_plus_haut(self) -> None:
        assert plus_haut([1, 5, 3, 4], None) == 5

    def test_repli_positif(self) -> None:
        recul = repli_depuis_plus_haut_pct([100.0, 120.0, 90.0])
        assert recul == pytest.approx(25.0)

    def test_repli_zero_quand_au_plus_haut(self) -> None:
        assert repli_depuis_plus_haut_pct([100.0, 120.0, 120.0]) == 0.0


class TestCroisement:
    def test_haussier(self) -> None:
        assert croisement([1, 3], [2, 2]) == "haussier"

    def test_baissier(self) -> None:
        assert croisement([3, 1], [2, 2]) == "baissier"

    def test_aucun_croisement(self) -> None:
        assert croisement([1, 2], [3, 4]) is None


class TestVolatilite:
    def test_serie_trop_courte(self) -> None:
        assert volatilite_pct([1.0, 2.0, 3.0], fenetre=20) is None

    def test_valeur_calculable(self) -> None:
        valeurs = [100.0 + i * (1 if i % 2 == 0 else -1) for i in range(30)]
        v = volatilite_pct(valeurs, fenetre=20)
        assert v is not None
        assert v > 0


class TestSerieSma:
    def test_taille_attendue(self) -> None:
        serie = serie_sma([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        assert serie == pytest.approx([2.0, 3.0, 4.0])

    def test_serie_trop_courte(self) -> None:
        assert serie_sma([1.0, 2.0], 3) == []

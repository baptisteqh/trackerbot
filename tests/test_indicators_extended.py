"""Tests des indicateurs etendus : ROC, EMA, MACD, Bollinger."""

from __future__ import annotations

import pytest

from trackerbot.indicators import bollinger_bands, ema, macd, roc


class TestRoc:
    def test_serie_trop_courte(self) -> None:
        assert roc([100.0, 105.0], 10) is None

    def test_calcul_simple(self) -> None:
        # 100 -> 110 sur 10 seances : ROC = 10%
        valeurs = [100.0 + i for i in range(11)]  # 100..110
        assert roc(valeurs, 10) == pytest.approx(10.0)

    def test_periode_invalide(self) -> None:
        with pytest.raises(ValueError):
            roc([1, 2, 3], 0)


class TestEma:
    def test_serie_constante_egale_a_la_constante(self) -> None:
        assert ema([50.0, 50.0, 50.0, 50.0], 3) == pytest.approx([50.0] * 4)

    def test_serie_vide(self) -> None:
        assert ema([], 5) == []


class TestMacd:
    def test_serie_trop_courte(self) -> None:
        assert macd([100.0] * 30) is None

    def test_serie_croissante_produit_histogramme_positif(self) -> None:
        valeurs = [100.0 + i * 0.5 for i in range(60)]
        result = macd(valeurs)
        assert result is not None
        _, _, hist = result
        assert hist >= 0

    def test_rapide_doit_etre_inferieur_a_lente(self) -> None:
        with pytest.raises(ValueError):
            macd([1.0] * 60, rapide=30, lente=20)


class TestBollinger:
    def test_serie_trop_courte(self) -> None:
        assert bollinger_bands([100.0] * 10, periode=20) is None

    def test_serie_constante_bandes_confondues(self) -> None:
        result = bollinger_bands([50.0] * 25, periode=20)
        assert result is not None
        basse, moyenne, haute = result
        assert basse == moyenne == haute == pytest.approx(50.0)

    def test_bandes_encadrent_la_moyenne(self) -> None:
        valeurs = [100.0 + (i % 5) for i in range(25)]  # oscille
        result = bollinger_bands(valeurs, periode=20, k=2.0)
        assert result is not None
        basse, moyenne, haute = result
        assert basse < moyenne < haute

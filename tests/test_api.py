"""Tests de l'API HTTP : monkeypatch de yfinance et eToro pour rester offline."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trackerbot import api
from trackerbot.fundamentals import Fondamentaux
from trackerbot.models import Cotation, Position


@pytest.fixture
def portefeuille() -> list[Position]:
    # AAA porte une date d'ouverture : garde-fou contre la regression date -> JSON.
    return [
        Position(
            ticker="AAA", quantite=10, prix_entree=100.0, ouverte_le=date(2024, 11, 4)
        ),
        Position(ticker="BBB", quantite=5, prix_entree=200.0),
    ]


@pytest.fixture
def cotations() -> dict[str, Cotation]:
    return {
        "AAA": Cotation(ticker="AAA", prix=110.0, clotures=[100.0, 105.0, 110.0]),
        "BBB": Cotation(ticker="BBB", prix=190.0, clotures=[200.0, 195.0, 190.0]),
        "SPY": Cotation(ticker="SPY", prix=500.0, clotures=[490.0, 495.0, 500.0]),
    }


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    portefeuille: list[Position],
    cotations: dict[str, Cotation],
) -> Iterator[TestClient]:
    """Injecte des sources fausses : aucun reseau, aucun fichier a monter."""
    monkeypatch.setattr(api, "positions_loader", lambda: portefeuille)
    monkeypatch.setattr(
        api,
        "cotations_fetcher",
        lambda tickers: {t: cotations[t] for t in tickers if t in cotations},
    )
    monkeypatch.setattr(
        api,
        "fondamentaux_fetcher",
        lambda tickers: {
            "AAA": Fondamentaux(ticker="AAA", per=12.0, price_to_book=1.4, marge_nette_pct=15.0),
        },
    )
    # Historique isole du disque : jamais d'ecriture dans data/ pendant les tests.
    monkeypatch.setattr(api, "CHEMIN_HISTORIQUE_DEFAUT", tmp_path / "history.db")
    with TestClient(api.create_app()) as tc:
        yield tc


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRapport:
    def test_shape_de_base(self, client: TestClient) -> None:
        response = client.get("/rapport?benchmark=SPY&fondamentaux=false")
        assert response.status_code == 200
        data = response.json()

        # Champs de haut niveau attendus par le dashboard.
        assert set(data) >= {
            "genere_le",
            "lignes",
            "signaux",
            "veille",
            "tickers_manquants",
            "metriques",
            "equity_series",
            "deltas",
        }
        assert isinstance(data["equity_series"], list)
        assert set(data["deltas"]) >= {"pnl_1d_abs", "pnl_1d_pct", "pnl_7d_abs", "pnl_30d_abs"}
        # date serialisee en ISO string.
        assert isinstance(data["genere_le"], str)
        assert len(data["genere_le"]) == 10  # yyyy-mm-dd

    def test_lignes_portent_les_metriques_par_position(self, client: TestClient) -> None:
        data = client.get("/rapport?fondamentaux=false").json()
        assert len(data["lignes"]) == 2
        premiere = data["lignes"][0]
        assert {"position", "poids_pct", "valeur_courante", "gain_absolu"} <= set(premiere)
        # Fondamentaux et score doivent etre None quand non demandes.
        assert premiere["fondamentaux"] is None
        assert premiere["score_valorisation"] is None

    def test_fondamentaux_actifs_quand_demandes(self, client: TestClient) -> None:
        data = client.get("/rapport?fondamentaux=true").json()
        ligne_aaa = next(
            ligne for ligne in data["lignes"] if ligne["position"]["ticker"] == "AAA"
        )
        assert ligne_aaa["fondamentaux"] is not None
        assert ligne_aaa["fondamentaux"]["per"] == 12.0
        assert ligne_aaa["score_valorisation"] is not None
        assert isinstance(ligne_aaa["score_valorisation"]["score"], int)

    def test_metriques_avec_beta_quand_benchmark_disponible(self, client: TestClient) -> None:
        data = client.get("/rapport?benchmark=SPY").json()
        metriques = data["metriques"]
        assert metriques["benchmark"] == "SPY"
        assert isinstance(metriques["beta"], (float, int, type(None)))

    def test_benchmark_vide_desactive_le_beta(self, client: TestClient) -> None:
        data = client.get("/rapport?benchmark=").json()
        assert data["metriques"]["beta"] is None
        assert data["metriques"]["benchmark"] is None


class TestCors:
    def test_origine_dashboard_autorisee(self, client: TestClient) -> None:
        response = client.get(
            "/rapport?fondamentaux=false",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_origine_inconnue_pas_de_header(self, client: TestClient) -> None:
        response = client.get(
            "/rapport?fondamentaux=false",
            headers={"Origin": "http://evil.example.com"},
        )
        # Sans header CORS explicite, le navigateur bloquera cote client.
        assert response.headers.get("access-control-allow-origin") is None


class TestErreurs:
    def test_500_si_positions_loader_leve(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        cotations: dict[str, Cotation],
    ) -> None:
        def raise_(): raise RuntimeError("plus de portefeuille")
        monkeypatch.setattr(api, "positions_loader", raise_)
        monkeypatch.setattr(api, "cotations_fetcher", lambda t: {})
        monkeypatch.setattr(api, "CHEMIN_HISTORIQUE_DEFAUT", tmp_path / "history.db")
        with TestClient(api.create_app()) as tc:
            response = tc.get("/rapport")
            assert response.status_code == 500
            assert "plus de portefeuille" in response.json()["detail"]

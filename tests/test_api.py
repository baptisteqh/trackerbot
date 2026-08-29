"""Tests de l'API HTTP : lecture du cache, POST /refresh, defense CSRF.

Toutes les sources reseau sont monkeypatchees. Les tests hostiles
(CSRF sans token, Origin spoofe, rate exceeded) verifient les niveaux
3, 4, 5 de la defense en profondeur decrite dans api.py.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trackerbot import api
from trackerbot.models import Cotation, Position

ORIGINE_OK = "http://localhost:3000"
ORIGINE_KO = "http://evil.example.com"


@pytest.fixture
def portefeuille() -> list[Position]:
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
    """Injecte des sources fausses et isole disque + cache dans tmp_path."""
    monkeypatch.setattr(api, "positions_loader", lambda: portefeuille)
    monkeypatch.setattr(
        api,
        "cotations_fetcher",
        lambda tickers: {t: cotations[t] for t in tickers if t in cotations},
    )
    monkeypatch.setattr(api, "CHEMIN_HISTORIQUE_DEFAUT", tmp_path / "history.db")
    monkeypatch.setattr(api, "CHEMIN_CACHE_RAPPORT", tmp_path / "latest_rapport.json")
    with TestClient(api.create_app()) as tc:
        yield tc


def _refresh_headers(client: TestClient) -> dict[str, str]:
    """Recupere le CSRF et fabrique les headers pour un POST /refresh valide."""
    csrf = client.get("/csrf", headers={"Origin": ORIGINE_OK}).json()
    return {
        "Origin": ORIGINE_OK,
        "Content-Type": "application/json",
        api.HEADER_CSRF: csrf["token"],
    }


class TestHealth:
    def test_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestGetRapportCacheOnly:
    def test_503_quand_cache_vide(self, client: TestClient) -> None:
        response = client.get("/rapport")
        assert response.status_code == 503
        assert "cache" in response.json()["detail"]

    def test_lit_le_cache_apres_refresh(self, client: TestClient) -> None:
        client.post("/refresh", json={"scope": "quotes"}, headers=_refresh_headers(client))
        response = client.get("/rapport")
        assert response.status_code == 200
        data = response.json()
        assert set(data) >= {
            "genere_le", "lignes", "signaux", "veille", "metriques",
            "equity_series", "deltas",
        }
        assert isinstance(data["equity_series"], dict)
        assert "values" in data["equity_series"]
        assert "benchmark" in data["equity_series"]


class TestPostRefreshDefenseEnProfondeur:
    def test_403_sans_origin(self, client: TestClient) -> None:
        # `<img>` / `<script>` : pas d'Origin -> rejete niveau 3.
        response = client.post(
            "/refresh",
            json={"scope": "quotes"},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 403
        assert "origine" in response.json()["detail"]

    def test_403_origin_non_whitelistee(self, client: TestClient) -> None:
        response = client.post(
            "/refresh",
            json={"scope": "quotes"},
            headers={"Origin": ORIGINE_KO, "Content-Type": "application/json"},
        )
        assert response.status_code == 403

    def test_403_sans_csrf_meme_avec_bonne_origin(self, client: TestClient) -> None:
        # Origin OK mais aucun token CSRF -> rejete niveau 4.
        response = client.post(
            "/refresh",
            json={"scope": "quotes"},
            headers={"Origin": ORIGINE_OK, "Content-Type": "application/json"},
        )
        assert response.status_code == 403
        assert "csrf" in response.json()["detail"]

    def test_403_csrf_mismatch(self, client: TestClient) -> None:
        # On recupere un token puis on envoie un token different -> rejete.
        client.get("/csrf", headers={"Origin": ORIGINE_OK})
        response = client.post(
            "/refresh",
            json={"scope": "quotes"},
            headers={
                "Origin": ORIGINE_OK,
                "Content-Type": "application/json",
                api.HEADER_CSRF: "not-the-real-token",
            },
        )
        assert response.status_code == 403

    def test_200_avec_origin_et_csrf_valides(self, client: TestClient) -> None:
        response = client.post(
            "/refresh", json={"scope": "quotes"}, headers=_refresh_headers(client)
        )
        assert response.status_code == 200
        data = response.json()
        assert "lignes" in data
        assert len(data["lignes"]) == 2

    def test_422_scope_inconnu(self, client: TestClient) -> None:
        response = client.post(
            "/refresh", json={"scope": "invalide"}, headers=_refresh_headers(client)
        )
        assert response.status_code == 422

    def test_429_quand_rate_limit_veille(self, client: TestClient) -> None:
        headers = _refresh_headers(client)
        # veille : 4 par minute. Le 5eme doit passer en 429.
        for _ in range(4):
            response = client.post("/refresh", json={"scope": "veille"}, headers=headers)
            assert response.status_code == 200, response.text
        blocked = client.post("/refresh", json={"scope": "veille"}, headers=headers)
        assert blocked.status_code == 429


class TestPayloadShape:
    def test_equity_series_expose_benchmark_normalise(self, client: TestClient) -> None:
        client.post("/refresh", json={"scope": "quotes"}, headers=_refresh_headers(client))
        data = client.get("/rapport").json()
        series = data["equity_series"]
        assert series["benchmark"] is not None
        assert len(series["benchmark"]) == len(series["values"])
        # Normalisation : premier point du benchmark = premier point du portefeuille.
        assert series["benchmark"][0] == pytest.approx(series["values"][0])

    def test_deltas_champs_exposes(self, client: TestClient) -> None:
        client.post("/refresh", json={"scope": "quotes"}, headers=_refresh_headers(client))
        data = client.get("/rapport").json()
        assert set(data["deltas"]) == {
            "pnl_1d_abs", "pnl_1d_pct",
            "pnl_7d_abs", "pnl_7d_pct",
            "pnl_30d_abs", "pnl_30d_pct",
        }


class TestErreurs:
    def test_500_si_positions_loader_leve_pendant_refresh(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        def raise_() -> list[Position]:
            raise RuntimeError("plus de portefeuille")

        monkeypatch.setattr(api, "positions_loader", raise_)
        monkeypatch.setattr(api, "cotations_fetcher", lambda t: {})
        monkeypatch.setattr(api, "CHEMIN_HISTORIQUE_DEFAUT", tmp_path / "history.db")
        monkeypatch.setattr(api, "CHEMIN_CACHE_RAPPORT", tmp_path / "cache.json")
        with TestClient(api.create_app()) as tc:
            headers = _refresh_headers(tc)
            response = tc.post("/refresh", json={"scope": "quotes"}, headers=headers)
            assert response.status_code == 500
            assert "plus de portefeuille" in response.json()["detail"]

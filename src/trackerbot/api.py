"""API HTTP locale pour le dashboard.

Modele de menace : ce serveur est **strictement local**. Il ecoute sur
127.0.0.1 par defaut, jamais 0.0.0.0. Il ne demande pas d'authentification
parce qu'il n'expose que ce que le CLI expose deja, et parce que sortir
du 127.0.0.1 impliquerait de re-penser toute la question des cles (eToro,
Perplexity, Telegram) qui vivent aujourd'hui en clair dans `.env`.

Rendu : le seul endpoint (`GET /rapport`) renvoie exactement l'objet
`Rapport` construit par `report.construire_rapport`, serialise en JSON.
Le dashboard Next.js consomme cette forme. Ajouter un endpoint implique
d'ajouter un test dans test_api.py.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import ROOT, charger_config
from .fundamentals import Fondamentaux
from .fundamentals import fondamentaux as _fondamentaux_defaut
from .market import cotations as _cotations_defaut
from .metrics import serie_equity_portefeuille
from .models import Cotation, Position
from .report import Rapport, construire_rapport
from .signals import Seuils, evaluer_portefeuille
from .storage import deltas as _deltas
from .storage import sauvegarder as _sauvegarder

# Origines autorisees : le dev server Next.js uniquement.
_ORIGINES_AUTORISEES = ("http://localhost:3000", "http://127.0.0.1:3000")

# Historique par defaut : co-localise avec le portefeuille dans data/. Ignore par git.
CHEMIN_HISTORIQUE_DEFAUT = ROOT / "data" / "history.db"


def _charger_positions_defaut() -> list[Position]:
    """Import tardif : la CLI et l'API partagent la meme logique de source."""
    from .cli import _choisir_source

    return _choisir_source(charger_config()).positions()


# Fonctions references : les tests remplacent ces attributs pour eviter yfinance et eToro.
positions_loader: Callable[[], list[Position]] = _charger_positions_defaut
cotations_fetcher: Callable[[list[str]], dict[str, Cotation]] = _cotations_defaut
fondamentaux_fetcher: Callable[[list[str]], dict[str, Fondamentaux]] = _fondamentaux_defaut


def create_app() -> FastAPI:
    """Construit l'app FastAPI. Fonction plutot que module-level pour tests propres."""
    app = FastAPI(title="trackerbot", version="0.1.0", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_ORIGINES_AUTORISEES),
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/rapport")
    def rapport(benchmark: str | None = "SPY", fondamentaux: bool = False) -> JSONResponse:
        try:
            positions = positions_loader()
        except Exception as erreur:  # noqa: BLE001 - on renvoie l'erreur au client
            raise HTTPException(status_code=500, detail=f"lecture portefeuille : {erreur}") \
                from erreur

        tickers = [p.ticker for p in positions]
        cotations = cotations_fetcher(tickers) if tickers else {}
        cotation_benchmark = _cotation_benchmark(benchmark)
        fonds = fondamentaux_fetcher(tickers) if fondamentaux and tickers else None
        signaux = evaluer_portefeuille(positions, cotations, Seuils())

        rap = construire_rapport(
            positions,
            cotations,
            signaux,
            cotation_benchmark=cotation_benchmark,
            fondamentaux=fonds,
        )

        # Historique : on ne sauvegarde que quand les prix sont reels (sinon
        # on ecrirait le PnL d'aujourd'hui base sur les prix d'entree).
        if cotations:
            _sauvegarder(rap, CHEMIN_HISTORIQUE_DEFAUT)

        payload = _serialiser_rapport(rap)
        payload["equity_series"] = serie_equity_portefeuille(positions, cotations)
        payload["deltas"] = jsonable_encoder(_deltas(rap, CHEMIN_HISTORIQUE_DEFAUT))
        return JSONResponse(payload)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _cotation_benchmark(ticker: str | None) -> Cotation | None:
    if not ticker:
        return None
    normalise = ticker.strip().upper()
    return cotations_fetcher([normalise]).get(normalise) if normalise else None


def _serialiser_rapport(rapport: Rapport) -> dict[str, Any]:
    """FastAPI gere date, Path et StrEnum ; asdict n'aurait pas suffi."""
    donnees: dict[str, Any] = jsonable_encoder(rapport)
    return donnees


# App par defaut pour uvicorn : `uvicorn trackerbot.api:app`.
app = create_app()

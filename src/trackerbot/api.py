"""API HTTP locale pour le dashboard.

Modele de menace : ce serveur est **strictement local**. Il ecoute sur
127.0.0.1 par defaut, jamais 0.0.0.0. Il ne demande pas d'authentification
au sens compte utilisateur, mais il applique une defense en profondeur
qui neutralise les attaques CSRF classiques depuis n'importe quel site
visite dans le navigateur :

1. Bind 127.0.0.1 uniquement (defense niveau reseau).
2. CORS restreint a `http://localhost:3000` et `http://127.0.0.1:3000`.
3. Verification server-side de `Origin` sur toute requete qui modifie
   quelque chose : les balises `<img>`, `<script>` ou `<link>` ne
   transmettent pas d'Origin, donc elles sont rejetees d'office.
4. Double-submit CSRF : `GET /csrf` pose un cookie `xsrf-token`, le
   dashboard le renvoie dans le header `X-XSRF-Token` sur `POST /refresh`.
   Un site tiers ne peut ni lire ni fixer ce cookie sur notre origine.
5. Rate limit en memoire par scope : `quotes` 60/min, `veille` et
   `fundamentals` 4/min pour proteger le quota Perplexity et yfinance
   meme si les niveaux 3 et 4 tombent.
6. `GET /rapport` est **idempotent** : il lit uniquement le dernier
   rapport en cache (`data/latest_rapport.json`), aucun appel reseau.
   L'attaque CSRF via `<img>` echouerait de toute facon a declencher
   quoi que ce soit d'onereux.

Rendu : deux endpoints, `GET /rapport` (cache) et `POST /refresh`
(mutation). Ajouter un endpoint implique d'ajouter un test dans
test_api.py.
"""

from __future__ import annotations

import secrets
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import ROOT, charger_config
from .fundamentals import Fondamentaux
from .fundamentals import fondamentaux as _fondamentaux_defaut
from .market import cotations as _cotations_defaut
from .models import Cotation, Position
from .payload import payload_pour_dashboard
from .report import construire_rapport
from .signals import Seuils, evaluer_portefeuille
from .storage import (
    charger_rapport_complet,
    sauvegarder_rapport_complet,
)
from .storage import (
    deltas as _deltas,
)
from .storage import (
    sauvegarder as _sauvegarder,
)

# Origines autorisees : le dev server Next.js uniquement.
ORIGINES_AUTORISEES = frozenset(
    {"http://localhost:3000", "http://127.0.0.1:3000"}
)

# Historique et cache : co-localises avec le portefeuille dans data/. Ignore par git.
CHEMIN_HISTORIQUE_DEFAUT = ROOT / "data" / "history.db"
CHEMIN_CACHE_RAPPORT = ROOT / "data" / "latest_rapport.json"

# Nom du cookie et du header CSRF (double-submit).
COOKIE_CSRF = "xsrf-token"
HEADER_CSRF = "X-XSRF-Token"

# Rate limit par scope, exprime en (nombre max, fenetre en secondes).
LIMITES_RATE: dict[str, tuple[int, float]] = {
    "quotes": (60, 60.0),
    "veille": (4, 60.0),
    "fundamentals": (4, 60.0),
    "all": (4, 60.0),
}

# Scopes valides pour POST /refresh.
SCOPES_VALIDES = frozenset(LIMITES_RATE.keys())


def _charger_positions_defaut() -> list[Position]:
    """Import tardif : la CLI et l'API partagent la meme logique de source."""
    from .cli import _choisir_source

    return _choisir_source(charger_config()).positions()


# Fonctions references : les tests remplacent ces attributs pour eviter yfinance et eToro.
positions_loader: Callable[[], list[Position]] = _charger_positions_defaut
cotations_fetcher: Callable[[list[str]], dict[str, Cotation]] = _cotations_defaut
fondamentaux_fetcher: Callable[[list[str]], dict[str, Fondamentaux]] = _fondamentaux_defaut


class DemandeRefresh(BaseModel):
    """Corps attendu par POST /refresh."""

    scope: str = "quotes"


def create_app() -> FastAPI:
    """Construit l'app FastAPI. Fonction plutot que module-level pour tests propres."""
    app = FastAPI(title="trackerbot", version="0.1.0", docs_url=None, redoc_url=None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ORIGINES_AUTORISEES),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # Rate limiter simple, isole par app (une deque de timestamps par scope).
    horodatages: dict[str, deque[float]] = {scope: deque() for scope in SCOPES_VALIDES}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/csrf")
    def csrf(response: Response) -> dict[str, str]:
        """Pose un cookie CSRF et renvoie le token en clair pour double-submit."""
        token = secrets.token_urlsafe(32)
        response.set_cookie(
            key=COOKIE_CSRF,
            value=token,
            max_age=3600,
            path="/",
            secure=False,       # 127.0.0.1 est en http, secure=True le viderait
            httponly=False,     # le JS du dashboard doit pouvoir le lire
            samesite="strict",  # pas d'envoi cross-site
        )
        return {"token": token}

    @app.get("/rapport")
    def rapport() -> JSONResponse:
        """Lecture pure : renvoie le dernier rapport reussi ou 503 si vide."""
        cache = charger_rapport_complet(CHEMIN_CACHE_RAPPORT)
        if cache is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "aucun rapport en cache : lancer `trackerbot status` "
                    "ou POST /refresh d'abord."
                ),
            )
        return JSONResponse(cache)

    @app.post("/refresh")
    def refresh(
        request: Request,
        demande: DemandeRefresh,
        x_xsrf_token: str | None = Header(default=None, alias=HEADER_CSRF),
    ) -> JSONResponse:
        _exiger_origine_locale(request)
        _exiger_csrf_valide(request, x_xsrf_token)
        _exiger_rate_limit_libre(demande.scope, horodatages)

        try:
            positions = positions_loader()
        except Exception as erreur:  # noqa: BLE001 - on renvoie l'erreur au client
            raise HTTPException(
                status_code=500, detail=f"lecture portefeuille : {erreur}"
            ) from erreur

        payload = _calculer_rapport(positions, demande.scope)
        sauvegarder_rapport_complet(payload, CHEMIN_CACHE_RAPPORT)
        return JSONResponse(payload)

    return app


# ---------- Verifications de securite ---------- #


def _exiger_origine_locale(request: Request) -> None:
    """Rejette toute requete sans Origin ou avec Origin non whitelistee."""
    origine = request.headers.get("origin")
    if origine not in ORIGINES_AUTORISEES:
        raise HTTPException(status_code=403, detail="origine refusee")


def _exiger_csrf_valide(request: Request, header_token: str | None) -> None:
    """Double-submit : le token du header doit egaler celui du cookie."""
    cookie_token = request.cookies.get(COOKIE_CSRF)
    if not cookie_token or not header_token or not secrets.compare_digest(
        cookie_token, header_token
    ):
        raise HTTPException(status_code=403, detail="csrf invalide")


def _exiger_rate_limit_libre(
    scope: str, horodatages: dict[str, deque[float]]
) -> None:
    if scope not in SCOPES_VALIDES:
        raise HTTPException(status_code=422, detail=f"scope inconnu : {scope!r}")
    limite, fenetre = LIMITES_RATE[scope]
    maintenant = time.monotonic()
    file = horodatages[scope]
    while file and maintenant - file[0] > fenetre:
        file.popleft()
    if len(file) >= limite:
        raise HTTPException(status_code=429, detail=f"trop d'appels {scope}")
    file.append(maintenant)


# ---------- Calcul et serialisation du rapport ---------- #


def _calculer_rapport(positions: list[Position], scope: str) -> dict[str, Any]:
    """Recompute complet.

    Note : la granularite fine par scope (ne pas refetch la veille si
    scope=quotes) viendra dans une iteration ulterieure, quand `veille`
    sera cablee. En V1, quel que soit le scope, on refait le tour complet.
    Le rate limiter reste par scope pour proteger les quotas.
    """
    del scope  # accepte, non utilise pour l'instant
    tickers = [p.ticker for p in positions]
    cotations = cotations_fetcher(tickers) if tickers else {}
    cotation_benchmark = _cotation_benchmark("SPY")
    fonds: dict[str, Fondamentaux] | None = None  # opt-in via UI plus tard

    signaux = evaluer_portefeuille(positions, cotations, Seuils())
    rap = construire_rapport(
        positions,
        cotations,
        signaux,
        cotation_benchmark=cotation_benchmark,
        fondamentaux=fonds,
    )

    if cotations:
        _sauvegarder(rap, CHEMIN_HISTORIQUE_DEFAUT)

    return payload_pour_dashboard(
        rap,
        positions,
        cotations,
        cotation_benchmark,
        _deltas(rap, CHEMIN_HISTORIQUE_DEFAUT),
    )


def _cotation_benchmark(ticker: str | None) -> Cotation | None:
    if not ticker:
        return None
    normalise = ticker.strip().upper()
    return cotations_fetcher([normalise]).get(normalise) if normalise else None


# App par defaut pour uvicorn : `uvicorn trackerbot.api:app`.
app = create_app()

"""Client eToro, strictement en lecture.

Deux choix assumes, et ils sont lies a la securite plutot qu'au confort :

1. Aucune methode d'ecriture n'existe ici. Pas de passage d'ordre, pas de
   modification de stop. Ce qui n'est pas implemente ne peut pas etre
   declenche par un bug, une regle mal ecrite ou une reponse d'API mal lue.
2. Les cles ne sont lues que depuis l'environnement, jamais ecrites en
   log ni serialisees. Utiliser des cles au scope de lecture seule.

Reference : https://api-portal.etoro.com
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from ..models import Position

BASE_URL = "https://public-api.etoro.com"

_CHEMINS = {
    "real": "/api/v1/trading/info/portfolio",
    "demo": "/api/v1/trading/info/demo/portfolio",
}


class ErreurEtoro(RuntimeError):
    """Echec d'appel a l'API eToro, message deja lisible par un humain."""


class ClientEtoro:
    nom = "eToro"

    def __init__(
        self,
        api_key: str,
        user_key: str,
        environnement: str = "demo",
        timeout: float = 15.0,
        base_url: str = BASE_URL,
    ) -> None:
        if environnement not in _CHEMINS:
            raise ValueError(f"environnement inconnu : {environnement!r}")
        self._api_key = api_key
        self._user_key = user_key
        self.environnement = environnement
        self._timeout = timeout
        self._base_url = base_url

    def _entetes(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "x-user-key": self._user_key,
            "x-request-id": str(uuid.uuid4()),
            "accept": "application/json",
        }

    def portefeuille_brut(self) -> dict[str, Any]:
        url = f"{self._base_url}{_CHEMINS[self.environnement]}"
        try:
            reponse = httpx.get(url, headers=self._entetes(), timeout=self._timeout)
        except httpx.HTTPError as erreur:
            raise ErreurEtoro(f"eToro injoignable : {erreur}") from erreur

        if reponse.status_code == 401:
            raise ErreurEtoro(
                "eToro refuse les cles (401). Verifier ETORO_API_KEY, ETORO_USER_KEY "
                "et que le compte est bien verifie."
            )
        if reponse.status_code == 429:
            raise ErreurEtoro("eToro limite les appels (429). Reessayer plus tard.")
        if reponse.status_code >= 400:
            raise ErreurEtoro(f"eToro repond {reponse.status_code} : {reponse.text[:200]}")

        donnees: dict[str, Any] = reponse.json()
        return donnees

    def positions(self) -> list[Position]:
        return positions_depuis_reponse(self.portefeuille_brut())


def positions_depuis_reponse(charge: dict[str, Any]) -> list[Position]:
    """Normalise la reponse portefeuille d'eToro vers le modele du bot.

    La forme exacte varie selon l'endpoint et la version : les positions
    sont soit a la racine, soit sous clientPortfolio. Les instruments sont
    identifies par instrumentID, un entier qu'il faut resoudre en ticker
    via la table de correspondance des instruments.
    """
    conteneur = charge.get("clientPortfolio", charge)
    brutes = conteneur.get("positions", [])
    if not isinstance(brutes, list):
        return []

    positions: list[Position] = []
    for brute in brutes:
        ticker = (
            brute.get("ticker")
            or brute.get("symbolFull")
            or brute.get("instrumentName")
            or str(brute.get("instrumentID", "")).strip()
        )
        if not ticker:
            continue

        prix_entree = _flottant(brute.get("openRate"))
        montant = _flottant(brute.get("investedAmount") or brute.get("amount"))
        quantite = _flottant(brute.get("units"))
        if quantite is None and montant and prix_entree:
            quantite = montant / prix_entree
        if not prix_entree or not quantite:
            continue

        positions.append(
            Position(
                ticker=str(ticker).upper(),
                quantite=quantite,
                prix_entree=prix_entree,
                est_long=bool(brute.get("isBuy", True)),
                stop_loss=_flottant(brute.get("stopLossRate")) or None,
                take_profit=_flottant(brute.get("takeProfitRate")) or None,
                libelle=brute.get("instrumentName"),
                source="etoro",
            )
        )
    return positions


def _flottant(valeur: Any) -> float | None:
    if valeur is None:
        return None
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return None

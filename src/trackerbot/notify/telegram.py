"""Envoi Telegram, sortant uniquement.

Le bot appelle l'API Telegram, jamais l'inverse : pas de webhook, pas de
port ouvert, aucune surface joignable depuis internet. C'est la propriete
qui rend le depot publiable sans exposer la machine qui l'execute.

Le destinataire est fixe par TELEGRAM_CHAT_ID. Le bot ne repond a
personne d'autre puisqu'il n'ecoute pas.
"""

from __future__ import annotations

import httpx

LIMITE_TELEGRAM = 4096


class ErreurTelegram(RuntimeError):
    """Echec d'envoi, message deja lisible."""


def decouper(texte: str, limite: int = LIMITE_TELEGRAM) -> list[str]:
    """Coupe un message trop long aux sauts de ligne plutot qu'au milieu d'un mot."""
    if len(texte) <= limite:
        return [texte]

    morceaux: list[str] = []
    courant = ""
    for ligne in texte.splitlines(keepends=True):
        if len(courant) + len(ligne) > limite:
            if courant:
                morceaux.append(courant.rstrip())
                courant = ""
            while len(ligne) > limite:
                morceaux.append(ligne[:limite])
                ligne = ligne[limite:]
        courant += ligne
    if courant.strip():
        morceaux.append(courant.rstrip())
    return morceaux


def envoyer(token: str, chat_id: str, texte: str, timeout: float = 20.0) -> int:
    """Envoie le message, decoupe si besoin. Renvoie le nombre de messages envoyes."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    morceaux = decouper(texte)
    for morceau in morceaux:
        try:
            reponse = httpx.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": morceau,
                    "disable_web_page_preview": True,
                },
                timeout=timeout,
            )
        except httpx.HTTPError as erreur:
            raise ErreurTelegram(f"Telegram injoignable : {erreur}") from erreur
        if reponse.status_code >= 400:
            raise ErreurTelegram(
                f"Telegram repond {reponse.status_code} : {reponse.text[:200]}"
            )
    return len(morceaux)

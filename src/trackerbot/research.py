"""Veille de marche quotidienne via l'API Perplexity.

Le bot demande une synthese sourcee sur les valeurs detenues. Le prompt
interdit explicitement les recommandations d'achat ou de vente : ce qui
est attendu, ce sont des faits dates et leurs sources, pas un avis.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

API_URL = "https://api.perplexity.ai/chat/completions"
MODELE = "sonar"

INSTRUCTION = (
    "Tu es un analyste de marche. Tu resumes des faits verifiables et dates, "
    "avec leurs sources. Tu n'emets jamais de recommandation d'achat ou de "
    "vente, jamais de prevision de prix. Tu ecris en francais, sans emoji. "
    "Si une information n'est pas etablie, tu le dis."
)


@dataclass(frozen=True)
class Veille:
    texte: str
    sources: list[str]


def veille_du_jour(
    api_key: str,
    tickers: list[str],
    timeout: float = 60.0,
) -> Veille:
    """Synthese des nouvelles marquantes sur les valeurs suivies."""
    liste = ", ".join(sorted(set(tickers))) or "les grands indices actions"
    question = (
        f"Quelles informations de marche des dernieres 24 heures concernent {liste} ? "
        "Pour chaque valeur, deux phrases au maximum : le fait, et sa source. "
        "Ignore les valeurs sans actualite notable. Termine par une ligne sur le "
        "contexte macro du jour qui touche les actions et ETF."
    )

    reponse = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
        json={
            "model": MODELE,
            "messages": [
                {"role": "system", "content": INSTRUCTION},
                {"role": "user", "content": question},
            ],
            "search_recency_filter": "day",
        },
        timeout=timeout,
    )
    reponse.raise_for_status()
    charge = reponse.json()

    texte = charge["choices"][0]["message"]["content"].strip()
    sources = [str(c) for c in charge.get("citations", [])]
    return Veille(texte=texte, sources=sources)

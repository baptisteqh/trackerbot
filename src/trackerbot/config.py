"""Configuration lue depuis l'environnement.

Aucun secret ne vit dans le depot. Tout passe par des variables
d'environnement, chargees au besoin depuis un fichier .env local que
.gitignore exclut. Le depot public ne contient que .env.example.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_ENVIRONNEMENTS = frozenset({"demo", "real"})


def charger_dotenv(chemin: Path) -> None:
    """Injecte les paires cle=valeur d'un .env sans ecraser l'environnement reel."""
    if not chemin.exists():
        return
    for ligne_brute in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne_brute.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    etoro_api_key: str | None
    etoro_user_key: str | None
    etoro_environment: str
    perplexity_api_key: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    portfolio_file: Path

    @property
    def etoro_disponible(self) -> bool:
        return bool(self.etoro_api_key and self.etoro_user_key)

    @property
    def telegram_disponible(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def perplexity_disponible(self) -> bool:
        return bool(self.perplexity_api_key)


def _propre(nom: str) -> str | None:
    valeur = os.getenv(nom, "").strip()
    return valeur or None


def charger_config(fichier_env: Path | None = None) -> Config:
    charger_dotenv(fichier_env or ROOT / ".env")

    environnement = (os.getenv("ETORO_ENVIRONMENT") or "demo").strip().lower()
    if environnement not in _ENVIRONNEMENTS:
        raise ValueError(
            f"ETORO_ENVIRONMENT vaut {environnement!r}, attendu 'demo' ou 'real'."
        )

    fichier = os.getenv("PORTFOLIO_FILE") or "data/portfolio.yaml"
    chemin_portefeuille = Path(fichier)
    if not chemin_portefeuille.is_absolute():
        chemin_portefeuille = ROOT / chemin_portefeuille

    return Config(
        etoro_api_key=_propre("ETORO_API_KEY"),
        etoro_user_key=_propre("ETORO_USER_KEY"),
        etoro_environment=environnement,
        perplexity_api_key=_propre("PERPLEXITY_API_KEY"),
        telegram_bot_token=_propre("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_propre("TELEGRAM_CHAT_ID"),
        portfolio_file=chemin_portefeuille,
    )

"""Persistance locale des rapports : historique SQLite et cache complet.

Deux artefacts, deux roles :

1. `history.db` (SQLite) : un snapshot scalaire par jour pour calculer
   les deltas 1j/7j/30j. Upsert par jour, aucune duplication.
2. `latest_rapport.json` : la representation complete et serialisee du
   dernier rapport reussi. C'est cette copie que l'API `GET /rapport`
   sert au dashboard, ce qui rend le GET **strictement idempotent et
   sans effet reseau** (indispensable pour se proteger des CSRF via
   `<img>` ou `<script>` qui pourraient sinon declencher des appels
   yfinance ou Perplexity depuis n'importe quel site visite).

La base et le JSON vivent dans `data/`, deja ignore par `.gitignore`.
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .report import Rapport

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    prise_le          TEXT PRIMARY KEY,   -- ISO YYYY-MM-DD, une ligne par jour
    valeur_courante   REAL NOT NULL,
    gain_absolu       REAL NOT NULL,
    montant_investi   REAL NOT NULL,
    nombre_positions  INTEGER NOT NULL
);
"""


@dataclass(frozen=True)
class Deltas:
    """Variations du portefeuille sur trois horizons.

    Chaque champ est None quand l'historique ne remonte pas jusque-la ou
    quand la base de reference est nulle.
    """

    pnl_1d_abs: float | None = None
    pnl_1d_pct: float | None = None
    pnl_7d_abs: float | None = None
    pnl_7d_pct: float | None = None
    pnl_30d_abs: float | None = None
    pnl_30d_pct: float | None = None


HORIZONS_JOURS = (1, 7, 30)


def sauvegarder(rapport: Rapport, chemin_db: Path) -> None:
    """Enregistre un snapshot pour la date du rapport. Idempotent par jour."""
    _assurer_repertoire(chemin_db)
    with _connexion(chemin_db) as conn:
        conn.execute(
            """
            INSERT INTO snapshots (
                prise_le, valeur_courante, gain_absolu, montant_investi, nombre_positions
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(prise_le) DO UPDATE SET
                valeur_courante = excluded.valeur_courante,
                gain_absolu = excluded.gain_absolu,
                montant_investi = excluded.montant_investi,
                nombre_positions = excluded.nombre_positions
            """,
            (
                rapport.genere_le.isoformat(),
                rapport.valeur_courante,
                rapport.gain_absolu,
                rapport.montant_investi,
                rapport.nombre_positions,
            ),
        )


def deltas(rapport_actuel: Rapport, chemin_db: Path) -> Deltas:
    """Compare le rapport actuel aux snapshots des horizons standards."""
    if not chemin_db.exists():
        return Deltas()
    valeur_actuelle = rapport_actuel.valeur_courante
    aujourdhui = rapport_actuel.genere_le
    resultat: dict[str, float | None] = {}

    with _connexion(chemin_db) as conn:
        for horizon in HORIZONS_JOURS:
            ref = _valeur_au_plus_pres(conn, aujourdhui - timedelta(days=horizon))
            abs_key = f"pnl_{horizon}d_abs"
            pct_key = f"pnl_{horizon}d_pct"
            if ref is None:
                resultat[abs_key] = None
                resultat[pct_key] = None
                continue
            abs_delta = valeur_actuelle - ref
            resultat[abs_key] = abs_delta
            resultat[pct_key] = (abs_delta / ref * 100.0) if ref != 0 else None

    return Deltas(**resultat)


def _valeur_au_plus_pres(conn: sqlite3.Connection, cible: date) -> float | None:
    """Snapshot le plus proche de la date cible sans depasser (le passe, pas le futur)."""
    row = conn.execute(
        """
        SELECT valeur_courante FROM snapshots
        WHERE prise_le <= ?
        ORDER BY prise_le DESC
        LIMIT 1
        """,
        (cible.isoformat(),),
    ).fetchone()
    return None if row is None else float(row[0])


def _connexion(chemin_db: Path) -> sqlite3.Connection:
    """Une connexion, schema garanti. Autocommit implicite via context manager."""
    conn = sqlite3.connect(chemin_db)
    conn.execute("PRAGMA journal_mode=WAL")  # concurrence CLI + API
    conn.executescript(_SCHEMA)
    return conn


def _assurer_repertoire(chemin_db: Path) -> None:
    chemin_db.parent.mkdir(parents=True, exist_ok=True)


# ---------- Cache du dernier rapport complet (JSON) ---------- #


def sauvegarder_rapport_complet(payload: dict[str, Any], chemin_json: Path) -> None:
    """Ecrit le payload API du dernier rapport reussi, atomiquement.

    Le fichier est reecrit via `tempfile + os.replace` pour eviter qu'un
    lecteur concurrent voie un JSON tronque. Les permissions restent
    `0600` : jamais lisible par un autre utilisateur.
    """
    _assurer_repertoire(chemin_json)
    fd: int | None
    fd, chemin_tmp_str = tempfile.mkstemp(
        prefix=".rapport-", suffix=".json.tmp", dir=chemin_json.parent
    )
    try:
        os.fchmod(fd, 0o600)
        fichier = os.fdopen(fd, "w", encoding="utf-8")
        fd = None  # os.fdopen a pris possession du descripteur.
        with fichier:
            json.dump(payload, fichier, ensure_ascii=False)
        os.replace(chemin_tmp_str, chemin_json)
    except Exception:
        # Avant fdopen, le descripteur reste a notre charge.
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        # Nettoyage best-effort si le rename n'a jamais eu lieu.
        with contextlib.suppress(FileNotFoundError):
            os.unlink(chemin_tmp_str)
        raise


def charger_rapport_complet(chemin_json: Path) -> dict[str, Any] | None:
    """Renvoie le dernier rapport connu, ou None si aucune sauvegarde encore."""
    if not chemin_json.exists():
        return None
    try:
        with chemin_json.open("r", encoding="utf-8") as fichier:
            donnees: dict[str, Any] = json.load(fichier)
    except (OSError, json.JSONDecodeError):
        # Cache corrompu : on prefere renvoyer None que servir un ancien
        # payload potentiellement invalide. Le prochain refresh reecrira.
        return None
    return donnees

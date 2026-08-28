"""Historique local des rapports, stocke en SQLite.

Pourquoi SQLite plutot que des fichiers JSON dates : une seule table, une
requete pour le point d'il y a N jours, aucune serialisation ad-hoc, et
la stdlib suffit. La base vit dans `data/history.db`, comme le YAML des
positions, donc elle est deja ignoree par `.gitignore` (`data/*`).

Design :

- **Un snapshot par jour et par base**. Si on rejoue le meme jour on
  ecrase (upsert) : les rapports en cours de journee sont volatils.
- **Ecriture opportuniste**. Un rapport genere hors ligne (sans
  cotations) n'ajoute rien : mesurer un delta sur un rapport factice
  serait faux.
- **Lecture stricte**. `deltas()` renvoie None sur chaque champ quand
  l'historique ne remonte pas assez loin ; on n'invente rien.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

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

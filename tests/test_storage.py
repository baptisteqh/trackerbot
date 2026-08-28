"""Tests du stockage SQLite : offline, base temporaire, deterministes."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from trackerbot.models import Position
from trackerbot.report import Rapport, construire_rapport
from trackerbot.storage import Deltas, deltas, sauvegarder


def _rapport(valeur: float, jour: date) -> Rapport:
    """Fabrique un rapport dont la valeur_courante est controlee.

    Trois positions equivalentes a `valeur` euros : plus simple que
    d'aller triturer la dataclass immuable.
    """
    positions = [Position(ticker="AAA", quantite=1.0, prix_entree=valeur)]
    return construire_rapport(positions, {}, aujourdhui=jour)


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "history.db"


class TestSauvegarder:
    def test_creation_de_base(self, db: Path) -> None:
        sauvegarder(_rapport(1000.0, date(2026, 8, 1)), db)
        assert db.exists()

    def test_idempotent_meme_jour(self, db: Path) -> None:
        jour = date(2026, 8, 1)
        sauvegarder(_rapport(1000.0, jour), db)
        sauvegarder(_rapport(1050.0, jour), db)  # ecrase la ligne du jour

        # Un jour d'historique seulement : aucun delta calculable.
        d = deltas(_rapport(1050.0, jour), db)
        assert d == Deltas()


class TestDeltas:
    def test_pas_de_base_donne_none_partout(self, db: Path) -> None:
        assert deltas(_rapport(1000.0, date(2026, 8, 1)), db) == Deltas()

    def test_horizon_court_disponible_horizons_longs_none(self, db: Path) -> None:
        # Un seul snapshot d'il y a un jour : delta 1j valide, 7j et 30j None.
        sauvegarder(_rapport(1000.0, date(2026, 8, 1)), db)
        d = deltas(_rapport(1050.0, date(2026, 8, 2)), db)

        assert d.pnl_1d_abs == pytest.approx(50.0)
        assert d.pnl_1d_pct == pytest.approx(5.0)
        assert d.pnl_7d_abs is None
        assert d.pnl_7d_pct is None
        assert d.pnl_30d_abs is None

    def test_reference_toujours_le_snapshot_le_plus_recent_avant(self, db: Path) -> None:
        # Plusieurs snapshots : chaque horizon pioche le plus recent <= cible.
        sauvegarder(_rapport(800.0, date(2026, 7, 1)), db)  # ~31j en arriere
        sauvegarder(_rapport(900.0, date(2026, 7, 25)), db)  # ~7j en arriere
        sauvegarder(_rapport(950.0, date(2026, 7, 31)), db)  # 1j en arriere

        d = deltas(_rapport(1000.0, date(2026, 8, 1)), db)
        # 1j : cible 2026-07-31 -> 950
        assert d.pnl_1d_abs == pytest.approx(50.0)
        # 7j : cible 2026-07-25 -> 900
        assert d.pnl_7d_abs == pytest.approx(100.0)
        # 30j : cible 2026-07-02 -> 800 (unique snapshot <= cette date)
        assert d.pnl_30d_abs == pytest.approx(200.0)

    def test_base_nulle_donne_pourcentage_none(self, db: Path) -> None:
        # Position validee : prix_entree > 0. On force la reference a zero en
        # patchant directement le rapport (dataclass frozen -> nouveau rapport).
        from dataclasses import replace

        base = _rapport(1000.0, date(2026, 7, 25))
        rapport_a_zero = replace(base, lignes=[])  # aucune ligne -> valeur_courante = 0
        sauvegarder(rapport_a_zero, db)

        d = deltas(_rapport(500.0, date(2026, 8, 1)), db)
        # abs bien defini, pct None a cause de la division par zero.
        assert d.pnl_7d_abs == pytest.approx(500.0)
        assert d.pnl_7d_pct is None

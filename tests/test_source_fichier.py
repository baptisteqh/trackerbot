"""Tests de la source portefeuille en YAML local."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from trackerbot.sources.fichier_local import SourceFichier, positions_depuis_dict


def test_positions_depuis_dict_ok() -> None:
    contenu = {
        "positions": [
            {
                "ticker": "aapl",
                "quantite": 10,
                "prix_entree": 100.5,
                "stop_loss": 90.0,
                "ouverte_le": "2025-01-15",
                "libelle": "Apple",
            }
        ]
    }
    positions = positions_depuis_dict(contenu)
    assert len(positions) == 1
    p = positions[0]
    assert p.ticker == "AAPL"
    assert p.quantite == 10.0
    assert p.prix_entree == 100.5
    assert p.stop_loss == 90.0
    assert p.ouverte_le == date(2025, 1, 15)
    assert p.libelle == "Apple"
    assert p.source == "local"


def test_positions_depuis_dict_champs_manquants() -> None:
    with pytest.raises(ValueError, match="champs manquants"):
        positions_depuis_dict({"positions": [{"ticker": "A", "quantite": 1}]})


def test_positions_depuis_dict_positions_absentes() -> None:
    with pytest.raises(ValueError, match="positions"):
        positions_depuis_dict({})


def test_source_fichier_fichier_inconnu(tmp_path: Path) -> None:
    source = SourceFichier(tmp_path / "absent.yaml")
    with pytest.raises(FileNotFoundError):
        source.positions()


def test_source_fichier_lit_yaml(tmp_path: Path) -> None:
    chemin = tmp_path / "p.yaml"
    chemin.write_text(
        "positions:\n"
        "  - ticker: AAPL\n"
        "    quantite: 5\n"
        "    prix_entree: 150\n",
        encoding="utf-8",
    )
    positions = SourceFichier(chemin).positions()
    assert positions[0].ticker == "AAPL"
    assert positions[0].quantite == 5

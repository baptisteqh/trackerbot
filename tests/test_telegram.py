"""Tests du decoupage Telegram (limite 4096 caracteres)."""

from __future__ import annotations

from trackerbot.notify.telegram import LIMITE_TELEGRAM, decouper


def test_message_court_pas_decoupe() -> None:
    assert decouper("bonjour") == ["bonjour"]


def test_decoupe_sur_sauts_de_ligne() -> None:
    ligne = "a" * 100 + "\n"
    texte = ligne * 60
    morceaux = decouper(texte, limite=500)
    assert len(morceaux) > 1
    assert all(len(m) <= 500 for m in morceaux)


def test_ligne_trop_longue_est_coupee() -> None:
    texte = "x" * (LIMITE_TELEGRAM + 200)
    morceaux = decouper(texte)
    assert all(len(m) <= LIMITE_TELEGRAM for m in morceaux)
    assert "".join(morceaux) == texte

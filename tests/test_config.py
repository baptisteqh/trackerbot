"""Tests de la configuration : lecture .env et validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from trackerbot.config import charger_config, charger_dotenv


def test_charger_dotenv_ecrit_dans_environ(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for cle in ("ETORO_API_KEY", "ETORO_USER_KEY", "PERPLEXITY_API_KEY"):
        monkeypatch.delenv(cle, raising=False)
    env = tmp_path / ".env"
    env.write_text(
        'ETORO_API_KEY="abc"\n'
        "ETORO_USER_KEY=xyz\n"
        "# commentaire ignore\n"
        "PERPLEXITY_API_KEY=perp\n",
        encoding="utf-8",
    )
    charger_dotenv(env)
    import os

    assert os.environ["ETORO_API_KEY"] == "abc"
    assert os.environ["ETORO_USER_KEY"] == "xyz"
    assert os.environ["PERPLEXITY_API_KEY"] == "perp"


def test_charger_dotenv_nexiste_pas(tmp_path: Path) -> None:
    charger_dotenv(tmp_path / "inexistant")  # ne doit pas lever


def test_charger_config_valide(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for cle in (
        "ETORO_API_KEY",
        "ETORO_USER_KEY",
        "ETORO_ENVIRONMENT",
        "PERPLEXITY_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "PORTFOLIO_FILE",
    ):
        monkeypatch.delenv(cle, raising=False)

    monkeypatch.setenv("ETORO_API_KEY", "k")
    monkeypatch.setenv("ETORO_USER_KEY", "u")
    monkeypatch.setenv("ETORO_ENVIRONMENT", "real")
    monkeypatch.setenv("PORTFOLIO_FILE", str(tmp_path / "p.yaml"))

    config = charger_config(fichier_env=tmp_path / "inexistant.env")
    assert config.etoro_disponible is True
    assert config.etoro_environment == "real"
    assert config.perplexity_disponible is False
    assert config.telegram_disponible is False
    assert config.portfolio_file == tmp_path / "p.yaml"


def test_charger_config_environnement_invalide(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ETORO_ENVIRONMENT", "prod")
    with pytest.raises(ValueError):
        charger_config(fichier_env=tmp_path / "inexistant.env")

"""Canaux de sortie du bot."""

from .telegram import ErreurTelegram, envoyer

__all__ = ["envoyer", "ErreurTelegram"]

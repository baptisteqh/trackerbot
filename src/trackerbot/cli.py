"""Interface en ligne de commande.

Toutes les sous-commandes sont locales : elles n'ecrivent rien, elles
n'ouvrent aucun port. Les envois Telegram sont sortants uniquement et les
appels aux APIs (eToro, Perplexity, Yahoo via yfinance) sont declenches
explicitement par l'utilisateur.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from .config import Config, charger_config
from .fundamentals import Fondamentaux
from .fundamentals import fondamentaux as recuperer_fondamentaux
from .market import cotations as recuperer_cotations
from .models import Cotation, Niveau, Position, Signal
from .notify.telegram import ErreurTelegram
from .notify.telegram import envoyer as envoyer_telegram
from .report import construire_rapport, formater_rapport
from .research import Veille, veille_du_jour
from .signals import Seuils, evaluer_portefeuille
from .sources.base import SourcePortefeuille
from .sources.etoro import ClientEtoro, ErreurEtoro
from .sources.fichier_local import SourceFichier

logger = logging.getLogger("trackerbot")

NIVEAUX_ALERTE = {Niveau.ALERTE, Niveau.ATTENTION}


def main(argv: Sequence[str] | None = None) -> int:
    parseur = _construire_parseur()
    args = parseur.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbeux else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        config = charger_config()
    except ValueError as erreur:
        print(f"Configuration invalide : {erreur}", file=sys.stderr)
        return 2

    try:
        code: int = args.executer(args, config)
    except (ErreurEtoro, ErreurTelegram, FileNotFoundError, ValueError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1
    return code


def _construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(
        prog="trackerbot",
        description=(
            "Assistant de suivi de portefeuille : lecture des positions, signaux "
            "techniques et alertes Telegram. Aucun ordre n'est passe."
        ),
    )
    parseur.add_argument(
        "-v", "--verbeux", action="store_true", help="active les logs DEBUG"
    )

    sous = parseur.add_subparsers(dest="commande", required=True)

    p_status = sous.add_parser(
        "status", help="imprime le rapport complet dans la console"
    )
    p_status.add_argument(
        "--sans-cotations",
        action="store_true",
        help="n'appelle pas Yahoo Finance, utile hors ligne",
    )
    p_status.add_argument(
        "--benchmark",
        default="SPY",
        help="ticker de reference pour le beta (defaut SPY, vide pour ignorer)",
    )
    p_status.add_argument(
        "--fondamentaux",
        action="store_true",
        help="ajoute les fondamentaux et le score de valorisation (appel yfinance en plus)",
    )
    p_status.set_defaults(executer=_cmd_status)

    p_watch = sous.add_parser(
        "watch",
        help=(
            "envoie sur Telegram uniquement s'il y a un signal ATTENTION ou ALERTE"
        ),
    )
    p_watch.set_defaults(executer=_cmd_watch)

    p_notify = sous.add_parser(
        "notify", help="envoie le rapport complet sur Telegram"
    )
    p_notify.add_argument(
        "--avec-veille",
        action="store_true",
        help="joint la veille Perplexity au rapport",
    )
    p_notify.set_defaults(executer=_cmd_notify)

    p_veille = sous.add_parser(
        "veille", help="imprime la veille de marche du jour (Perplexity)"
    )
    p_veille.set_defaults(executer=_cmd_veille)

    p_doctor = sous.add_parser(
        "doctor", help="verifie la configuration et l'acces aux integrations"
    )
    p_doctor.set_defaults(executer=_cmd_doctor)

    return parseur


def _cmd_status(args: argparse.Namespace, config: Config) -> int:
    positions = _charger_positions(config)
    tickers = [p.ticker for p in positions]
    cotations = {} if args.sans_cotations else recuperer_cotations(tickers)
    signaux = evaluer_portefeuille(positions, cotations, Seuils())
    benchmark = _cotation_benchmark(args.benchmark, args.sans_cotations)
    fonds = _fondamentaux_pour(tickers, args.fondamentaux, args.sans_cotations)
    rapport = construire_rapport(
        positions,
        cotations,
        signaux,
        cotation_benchmark=benchmark,
        fondamentaux=fonds,
    )
    print(formater_rapport(rapport))
    return 0


def _cotation_benchmark(ticker: str | None, hors_ligne: bool) -> Cotation | None:
    """Charge la cotation d'un ticker unique, silencieux si echec ou desactive."""
    if hors_ligne or not ticker:
        return None
    return recuperer_cotations([ticker]).get(ticker.strip().upper())


def _fondamentaux_pour(
    tickers: list[str], demande: bool, hors_ligne: bool
) -> dict[str, Fondamentaux] | None:
    """Ne recupere les fondamentaux que sur demande explicite et en ligne."""
    if hors_ligne or not demande or not tickers:
        return None
    return recuperer_fondamentaux(tickers)


def _cmd_watch(args: argparse.Namespace, config: Config) -> int:
    if not config.telegram_disponible:
        print(
            "Telegram non configure : renseigner TELEGRAM_BOT_TOKEN et "
            "TELEGRAM_CHAT_ID dans .env.",
            file=sys.stderr,
        )
        return 2

    positions = _charger_positions(config)
    cotations = recuperer_cotations([p.ticker for p in positions])
    signaux = evaluer_portefeuille(positions, cotations, Seuils())

    urgents = [s for s in signaux if s.niveau in NIVEAUX_ALERTE]
    if not urgents:
        logger.info("Aucun signal ATTENTION ni ALERTE, pas d'envoi Telegram.")
        return 0

    texte = _formater_signaux(urgents)
    assert config.telegram_bot_token and config.telegram_chat_id
    envoyer_telegram(config.telegram_bot_token, config.telegram_chat_id, texte)
    return 0


def _cmd_notify(args: argparse.Namespace, config: Config) -> int:
    if not config.telegram_disponible:
        print(
            "Telegram non configure : renseigner TELEGRAM_BOT_TOKEN et "
            "TELEGRAM_CHAT_ID dans .env.",
            file=sys.stderr,
        )
        return 2

    positions = _charger_positions(config)
    cotations = recuperer_cotations([p.ticker for p in positions])
    signaux = evaluer_portefeuille(positions, cotations, Seuils())

    veille: Veille | None = None
    if args.avec_veille:
        if not config.perplexity_disponible:
            print(
                "Perplexity non configure : renseigner PERPLEXITY_API_KEY dans .env.",
                file=sys.stderr,
            )
            return 2
        assert config.perplexity_api_key
        veille = veille_du_jour(
            config.perplexity_api_key, [p.ticker for p in positions]
        )

    rapport = construire_rapport(positions, cotations, signaux, veille=veille)
    assert config.telegram_bot_token and config.telegram_chat_id
    envoyer_telegram(
        config.telegram_bot_token,
        config.telegram_chat_id,
        formater_rapport(rapport),
    )
    return 0


def _cmd_veille(args: argparse.Namespace, config: Config) -> int:
    if not config.perplexity_disponible:
        print(
            "Perplexity non configure : renseigner PERPLEXITY_API_KEY dans .env.",
            file=sys.stderr,
        )
        return 2
    positions = _charger_positions(config)
    assert config.perplexity_api_key
    veille = veille_du_jour(
        config.perplexity_api_key, [p.ticker for p in positions]
    )
    print(veille.texte)
    if veille.sources:
        print("\nSources :")
        for source in veille.sources:
            print(f"  - {source}")
    return 0


def _cmd_doctor(args: argparse.Namespace, config: Config) -> int:
    print(f"Fichier portefeuille : {config.portfolio_file}")
    print(f"  existe : {'oui' if config.portfolio_file.exists() else 'non'}")
    print(f"eToro       : {'configure' if config.etoro_disponible else 'absent'} "
          f"(environnement={config.etoro_environment})")
    print(f"Perplexity  : {'configure' if config.perplexity_disponible else 'absent'}")
    print(f"Telegram    : {'configure' if config.telegram_disponible else 'absent'}")

    source = _choisir_source(config)
    print(f"Source active : {source.nom}")
    try:
        positions = source.positions()
    except (FileNotFoundError, ErreurEtoro, ValueError) as erreur:
        print(f"  echec lecture des positions : {erreur}", file=sys.stderr)
        return 1
    print(f"  {len(positions)} position(s) lue(s)")
    return 0


def _charger_positions(config: Config) -> list[Position]:
    source = _choisir_source(config)
    logger.info("Lecture des positions via %s", source.nom)
    return source.positions()


def _choisir_source(config: Config) -> SourcePortefeuille:
    if config.etoro_disponible:
        assert config.etoro_api_key and config.etoro_user_key
        return ClientEtoro(
            api_key=config.etoro_api_key,
            user_key=config.etoro_user_key,
            environnement=config.etoro_environment,
        )
    return SourceFichier(config.portfolio_file)


def _formater_signaux(signaux: list[Signal]) -> str:
    entete = f"trackerbot : {len(signaux)} signal(s) a surveiller"
    corps = "\n".join(f"- {s}" for s in signaux)
    return f"{entete}\n{corps}"


if __name__ == "__main__":
    raise SystemExit(main())

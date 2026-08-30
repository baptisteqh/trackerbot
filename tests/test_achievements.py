"""Tests des badges gamifies."""

from __future__ import annotations

from datetime import date

from trackerbot.achievements import evaluer_badges
from trackerbot.benchmarks import ComparaisonBenchmark
from trackerbot.diversification import Diversification
from trackerbot.fundamentals import Fondamentaux
from trackerbot.metrics import MetriquesPortefeuille
from trackerbot.models import Cotation, Position
from trackerbot.report import LignePortefeuille, Rapport


def _metriques_vides(**overrides: object) -> MetriquesPortefeuille:
    """Fabrique un MetriquesPortefeuille avec tous les champs None + overrides.

    Isole les tests de l'evolution du dataclass : quand on ajoute un
    nouveau champ, seul ce helper est a mettre a jour.
    """
    valeurs: dict[str, object] = {
        "sharpe": None,
        "sortino": None,
        "calmar": None,
        "max_drawdown_pct": None,
        "volatilite_annuelle_pct": None,
        "rendement_annuel_pct": None,
        "var_95_pct": None,
        "hhi": None,
        "plus_grosse_position_pct": None,
        "beta": None,
        "alpha_annuel_pct": None,
        "information_ratio": None,
        "benchmark": None,
    }
    valeurs.update(overrides)
    return MetriquesPortefeuille(**valeurs)  # type: ignore[arg-type]


def _rapport(
    lignes: list[LignePortefeuille] | None = None,
    gain_absolu: float = 0.0,
    gain_pct: float = 0.0,
    metriques: MetriquesPortefeuille | None = None,
) -> Rapport:
    del gain_absolu, gain_pct  # derives depuis les lignes ci-dessous
    lignes = lignes or []
    return Rapport(
        genere_le=date(2026, 8, 30),
        lignes=lignes,
        signaux=[],
        metriques=metriques or _metriques_vides(),
    )


def _ligne(
    ticker: str = "AAA",
    poids_pct: float = 100.0,
    stop: float | None = None,
    sma_20: float | None = None,
    sma_50: float | None = None,
    per: float | None = None,
    gain_pct: float = 10.0,
) -> LignePortefeuille:
    position = Position(
        ticker=ticker, quantite=1.0, prix_entree=100.0, stop_loss=stop
    )
    fondamentaux = Fondamentaux(ticker=ticker, per=per) if per is not None else None
    prix = 100.0 * (1 + gain_pct / 100.0)
    return LignePortefeuille(
        position=position,
        cotation=Cotation(ticker=ticker, prix=prix, clotures=[100.0, prix]),
        poids_pct=poids_pct,
        valeur_courante=prix,
        montant_investi=100.0,
        gain_absolu=prix - 100.0,
        gain_pct=gain_pct,
        rsi_14=None,
        sma_20=sma_20,
        sma_50=sma_50,
        volatilite_20j_pct=None,
        fondamentaux=fondamentaux,
    )


def _find(badges, badge_id: str):
    return next(b for b in badges if b.id == badge_id)


class TestBadges:
    def test_first_position_locked_sur_vide(self) -> None:
        badges = evaluer_badges(_rapport([]))
        assert _find(badges, "first_position").unlocked is False

    def test_first_position_unlocked_avec_position(self) -> None:
        badges = evaluer_badges(_rapport([_ligne()]))
        assert _find(badges, "first_position").unlocked is True

    def test_positive_pnl(self) -> None:
        rapport = _rapport([_ligne(gain_pct=5.0)])
        badges = evaluer_badges(rapport)
        assert _find(badges, "positive_pnl").unlocked is True

    def test_double_digit_gainer_seuil(self) -> None:
        rapport = _rapport([_ligne(gain_pct=15.0)])
        badges = evaluer_badges(rapport)
        assert _find(badges, "double_digit_gainer").unlocked is True

        rapport_sous = _rapport([_ligne(gain_pct=5.0)])
        badges_sous = evaluer_badges(rapport_sous)
        assert _find(badges_sous, "double_digit_gainer").unlocked is False

    def test_risk_manager_sharpe(self) -> None:
        m_ok = _metriques_vides(sharpe=1.5)
        badges = evaluer_badges(_rapport([_ligne()], metriques=m_ok))
        assert _find(badges, "risk_manager").unlocked is True

    def test_loss_cutter_tous_avec_stop(self) -> None:
        lignes = [_ligne("A", 50, stop=90), _ligne("B", 50, stop=80)]
        badges = evaluer_badges(_rapport(lignes))
        assert _find(badges, "loss_cutter").unlocked is True

    def test_loss_cutter_partiel(self) -> None:
        lignes = [_ligne("A", 50, stop=90), _ligne("B", 50, stop=None)]
        badges = evaluer_badges(_rapport(lignes))
        assert _find(badges, "loss_cutter").unlocked is False

    def test_value_hunter_average_per(self) -> None:
        lignes = [_ligne("A", 50, per=10.0), _ligne("B", 50, per=12.0)]
        badges = evaluer_badges(_rapport(lignes))
        assert _find(badges, "value_hunter").unlocked is True  # moyenne = 11 < 15

    def test_momentum_ready_majorite_haussiere(self) -> None:
        lignes = [
            _ligne("A", 33, sma_20=110, sma_50=100),
            _ligne("B", 33, sma_20=110, sma_50=100),
            _ligne("C", 34, sma_20=90, sma_50=100),
        ]
        badges = evaluer_badges(_rapport(lignes))
        # 2/3 haussiers -> unlocked (2 * 2 = 4 >= 3)
        assert _find(badges, "momentum_ready").unlocked is True

    def test_diversified_requiert_positions_et_hhi(self) -> None:
        m = _metriques_vides(hhi=2000)
        lignes = [_ligne(f"T{i}", 20.0) for i in range(5)]
        div = Diversification(positions_effectives=5.0)
        badges = evaluer_badges(_rapport(lignes, metriques=m), diversification=div)
        assert _find(badges, "diversified").unlocked is True

    def test_beat_the_market_avec_comparaison(self) -> None:
        comp = ComparaisonBenchmark(
            benchmark="SPY",
            perf_portefeuille={"1M": 5.0, "3M": 10.0, "YTD": 15.0, "1Y": 20.0},
            perf_benchmark={"1M": 2.0, "3M": 4.0, "YTD": 8.0, "1Y": 12.0},
            outperformance={"1M": 3.0, "3M": 6.0, "YTD": 7.0, "1Y": 8.0},
        )
        badges = evaluer_badges(_rapport([_ligne()]), comparaison=comp)
        assert _find(badges, "beat_the_market").unlocked is True

    def test_beat_the_market_sans_donnees(self) -> None:
        badges = evaluer_badges(_rapport([_ligne()]))
        beat = _find(badges, "beat_the_market")
        assert beat.unlocked is False
        assert beat.detail == "Benchmark not configured"

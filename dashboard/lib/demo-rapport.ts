// Payload démo servi quand l'API Python n'est pas joignable.
// Toutes les valeurs sont réalistes mais fictives — jamais persistées, jamais
// envoyées au backend. Sert uniquement à donner un aperçu du dashboard sans
// devoir lancer `trackerbot serve` en parallèle.

import type { Rapport } from "./types"

function makeSeries(base: number, days: number, drift: number, volatility: number): number[] {
  const values: number[] = []
  let value = base
  let seed = 42
  for (let i = 0; i < days; i++) {
    seed = (seed * 9301 + 49297) % 233280
    const noise = (seed / 233280 - 0.5) * volatility
    value = value * (1 + drift + noise)
    values.push(Math.round(value * 100) / 100)
  }
  return values
}

const equity = makeSeries(10000, 180, 0.0015, 0.018)
const spy = makeSeries(10000, 180, 0.0009, 0.011)

export const DEMO_RAPPORT: Rapport = {
  genere_le: new Date().toISOString().slice(0, 10),
  tickers_manquants: [],
  lignes: [
    {
      position: {
        ticker: "AAPL",
        quantite: 30,
        prix_entree: 172.5,
        est_long: true,
        stop_loss: 155,
        take_profit: 240,
        ouverte_le: "2024-11-04",
        libelle: "Apple Inc.",
        source: "demo",
      },
      cotation: {
        ticker: "AAPL",
        prix: 224.31,
        clotures: makeSeries(180, 90, 0.003, 0.015),
        devise: "USD",
      },
      poids_pct: 32.4,
      valeur_courante: 6729.3,
      montant_investi: 5175,
      gain_absolu: 1554.3,
      gain_pct: 30.04,
      rsi_14: 62.1,
      sma_20: 218.4,
      sma_50: 209.7,
      volatilite_20j_pct: 18.2,
      fondamentaux: null,
      score_valorisation: null,
    },
    {
      position: {
        ticker: "MSFT",
        quantite: 12,
        prix_entree: 410,
        est_long: true,
        stop_loss: 380,
        take_profit: null,
        ouverte_le: "2024-08-12",
        libelle: "Microsoft",
        source: "demo",
      },
      cotation: {
        ticker: "MSFT",
        prix: 447.5,
        clotures: makeSeries(420, 90, 0.001, 0.012),
        devise: "USD",
      },
      poids_pct: 25.8,
      valeur_courante: 5370,
      montant_investi: 4920,
      gain_absolu: 450,
      gain_pct: 9.15,
      rsi_14: 51.2,
      sma_20: 439.8,
      sma_50: 435.4,
      volatilite_20j_pct: 14.7,
      fondamentaux: null,
      score_valorisation: null,
    },
    {
      position: {
        ticker: "VWCE.DE",
        quantite: 45,
        prix_entree: 112.3,
        est_long: true,
        stop_loss: null,
        take_profit: null,
        ouverte_le: null,
        libelle: "Vanguard FTSE All-World UCITS ETF",
        source: "demo",
      },
      cotation: {
        ticker: "VWCE.DE",
        prix: 128.7,
        clotures: makeSeries(120, 90, 0.0009, 0.01),
        devise: "EUR",
      },
      poids_pct: 22.3,
      valeur_courante: 5791.5,
      montant_investi: 5053.5,
      gain_absolu: 738,
      gain_pct: 14.6,
      rsi_14: 58.4,
      sma_20: 126.2,
      sma_50: 122.1,
      volatilite_20j_pct: 8.9,
      fondamentaux: null,
      score_valorisation: null,
    },
    {
      position: {
        ticker: "NVDA",
        quantite: 8,
        prix_entree: 118,
        est_long: true,
        stop_loss: 95,
        take_profit: 175,
        ouverte_le: "2025-01-15",
        libelle: "NVIDIA",
        source: "demo",
      },
      cotation: {
        ticker: "NVDA",
        prix: 138.4,
        clotures: makeSeries(130, 90, 0.0025, 0.025),
        devise: "USD",
      },
      poids_pct: 12.4,
      valeur_courante: 1107.2,
      montant_investi: 944,
      gain_absolu: 163.2,
      gain_pct: 17.29,
      rsi_14: 72.4,
      sma_20: 134.1,
      sma_50: 129.8,
      volatilite_20j_pct: 26.5,
      fondamentaux: null,
      score_valorisation: null,
    },
    {
      position: {
        ticker: "TSLA",
        quantite: 5,
        prix_entree: 245,
        est_long: false,
        stop_loss: null,
        take_profit: null,
        ouverte_le: "2025-02-20",
        libelle: "Tesla",
        source: "demo",
      },
      cotation: {
        ticker: "TSLA",
        prix: 218.3,
        clotures: makeSeries(240, 90, -0.001, 0.028),
        devise: "USD",
      },
      poids_pct: 7.1,
      valeur_courante: 1091.5,
      montant_investi: 1225,
      gain_absolu: 133.5,
      gain_pct: 10.9,
      rsi_14: 32.1,
      sma_20: 225.2,
      sma_50: 234.8,
      volatilite_20j_pct: 32.1,
      fondamentaux: null,
      score_valorisation: null,
    },
  ],
  signaux: [
    {
      ticker: "TSLA",
      niveau: "attention",
      regle: "repli",
      message: "12.4 % sous le plus haut des 90 dernieres seances",
    },
    {
      ticker: "NVDA",
      niveau: "info",
      regle: "rsi_surachat",
      message: "RSI a 72, zone de surachat",
    },
    {
      ticker: "AAPL",
      niveau: "info",
      regle: "gain_notable",
      message: "gain latent de 30.0 %",
    },
  ],
  veille: {
    texte:
      "Marches actions US en hausse modeste, portes par les megacaps tech. Nvidia atteint un nouveau plus haut sur fond d'annonces GPU serveur. Le rendement 10Y US se stabilise autour de 4.15 % apres la publication des chiffres CPI en ligne avec les attentes. En Europe, DAX et CAC 40 evoluent lateralement, l'euro reste faible face au dollar.",
    sources: [
      "https://www.reuters.com/markets/us/",
      "https://www.bloomberg.com/markets/stocks",
      "https://www.ft.com/markets",
    ],
  },
  metriques: {
    sharpe: 1.42,
    max_drawdown_pct: 8.6,
    volatilite_annuelle_pct: 17.4,
    rendement_annuel_pct: 24.8,
    hhi: 2418,
    plus_grosse_position_pct: 32.4,
    beta: 1.08,
    benchmark: "SPY",
  },
  equity_series: {
    values: equity,
    benchmark: spy,
  },
  deltas: {
    pnl_1d_abs: 142.8,
    pnl_1d_pct: 0.71,
    pnl_7d_abs: -318.4,
    pnl_7d_pct: -1.55,
    pnl_30d_abs: 1204.3,
    pnl_30d_pct: 6.35,
  },
  diversification: {
    poids_par_secteur: {
      "Technology": 70.6,
      "Diversified ETF": 22.3,
      "Consumer Discretionary": 7.1,
    },
    hhi_secteurs: 5545,
    plus_gros_secteur: "Technology",
    plus_gros_secteur_pct: 70.6,
    positions_effectives: 3.72,
    ratio_diversification: 1.24,
    correlation_moyenne: 0.58,
    paires_correlees: [
      { ticker_a: "AAPL", ticker_b: "MSFT", correlation: 0.87 },
    ],
  },
  comparaison_benchmark: {
    benchmark: "SPY",
    perf_portefeuille: { "1M": 6.35, "3M": 12.84, "YTD": 22.4, "1Y": 32.1 },
    perf_benchmark: { "1M": 3.1, "3M": 6.8, "YTD": 14.2, "1Y": 22.0 },
    outperformance: { "1M": 3.25, "3M": 6.04, "YTD": 8.2, "1Y": 10.1 },
  },
  badges: [
    {
      id: "first_position",
      label: "First position",
      description: "Own at least one position.",
      unlocked: true,
      detail: "5 positions",
    },
    {
      id: "positive_pnl",
      label: "In the green",
      description: "Total unrealized PnL is positive.",
      unlocked: true,
      detail: "+3,038.00",
    },
    {
      id: "double_digit_gainer",
      label: "Double-digit gainer",
      description: "Total return >= +10%.",
      unlocked: true,
      detail: "+16.4%",
    },
    {
      id: "risk_manager",
      label: "Risk manager",
      description: "Sharpe ratio above 1.0 — return justifies risk.",
      unlocked: true,
      detail: "Sharpe 1.42",
    },
    {
      id: "beat_the_market",
      label: "Beat SPY (3M)",
      description: "Outperform SPY over the last 3 months.",
      unlocked: true,
      detail: "+6.04 pts vs SPY",
    },
    {
      id: "loss_cutter",
      label: "Loss cutter",
      description: "Stop-loss set on every position.",
      unlocked: false,
      detail: "3/5 with stop-loss",
    },
    {
      id: "momentum_ready",
      label: "Momentum ready",
      description: "At least half of your positions have SMA20 above SMA50.",
      unlocked: true,
      detail: "4/5 bullish crossover",
    },
    {
      id: "diversified",
      label: "Diversified",
      description: "At least 5 positions with HHI <= 2500 (well-spread).",
      unlocked: false,
      detail: "HHI 2418",
    },
    {
      id: "value_hunter",
      label: "Value hunter",
      description: "Average portfolio PER below 15.",
      unlocked: false,
      detail: "Add --fondamentaux to check",
    },
    {
      id: "survived_drawdown",
      label: "Survived a drawdown",
      description: "Recovered from a >=10% peak-to-trough decline.",
      unlocked: false,
      detail: "MaxDD 8.6%",
    },
  ],
}

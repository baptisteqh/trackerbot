// Miroir des dataclasses Python côté frontend.
// Généré à la main pour éviter une dépendance OpenAPI en V1.
// Toute divergence avec src/trackerbot/*.py doit être corrigée ici + typée.

export type SignalLevel = "info" | "attention" | "alerte"

export interface Position {
  ticker: string
  quantite: number
  prix_entree: number
  est_long: boolean
  stop_loss: number | null
  take_profit: number | null
  ouverte_le: string | null // ISO YYYY-MM-DD
  libelle: string | null
  source: string
}

export interface Cotation {
  ticker: string
  prix: number
  clotures: number[]
  devise: string
}

export interface Signal {
  ticker: string
  niveau: SignalLevel
  regle: string
  message: string
}

export interface Fondamentaux {
  ticker: string
  per: number | null
  price_to_book: number | null
  marge_nette_pct: number | null
  debt_to_equity: number | null
  roe_pct: number | null
  dividend_yield_pct: number | null
  croissance_revenus_pct: number | null
  secteur: string | null
  industrie: string | null
}

export interface ScoreValorisation {
  ticker: string
  score: number
  criteres_remplis: string[]
  criteres_manquants: string[]
  inconnus: string[]
}

export interface Metriques {
  sharpe: number | null
  sortino: number | null
  max_drawdown_pct: number | null
  volatilite_annuelle_pct: number | null
  rendement_annuel_pct: number | null
  hhi: number | null
  plus_grosse_position_pct: number | null
  beta: number | null
  benchmark: string | null
}

export interface ExpositionDevise {
  devise: string
  poids_pct: number
  valeur: number
  nb_positions: number
}

export interface LignePortefeuille {
  position: Position
  cotation: Cotation | null
  poids_pct: number
  valeur_courante: number
  montant_investi: number
  gain_absolu: number
  gain_pct: number
  rsi_14: number | null
  sma_20: number | null
  sma_50: number | null
  volatilite_20j_pct: number | null
  fondamentaux: Fondamentaux | null
  score_valorisation: ScoreValorisation | null
}

export interface Veille {
  texte: string
  sources: string[]
}

export interface EquitySeries {
  values: number[]
  benchmark: number[] | null
}

export interface Deltas {
  pnl_1d_abs: number | null
  pnl_1d_pct: number | null
  pnl_7d_abs: number | null
  pnl_7d_pct: number | null
  pnl_30d_abs: number | null
  pnl_30d_pct: number | null
}

export interface PaireCorrelation {
  ticker_a: string
  ticker_b: string
  correlation: number
}

export interface Diversification {
  poids_par_secteur: Record<string, number>
  hhi_secteurs: number | null
  plus_gros_secteur: string | null
  plus_gros_secteur_pct: number | null
  positions_effectives: number | null
  ratio_diversification: number | null
  correlation_moyenne: number | null
  paires_correlees: PaireCorrelation[]
}

export type BenchmarkWindow = "1M" | "3M" | "YTD" | "1Y"

export interface ComparaisonBenchmark {
  benchmark: string
  perf_portefeuille: Record<BenchmarkWindow, number | null>
  perf_benchmark: Record<BenchmarkWindow, number | null>
  outperformance: Record<BenchmarkWindow, number | null>
}

export interface Badge {
  id: string
  label: string
  description: string
  unlocked: boolean
  detail: string | null
}

export interface Rapport {
  genere_le: string // ISO date
  lignes: LignePortefeuille[]
  signaux: Signal[]
  veille: Veille | null
  tickers_manquants: string[]
  metriques: Metriques | null
  equity_series: EquitySeries
  deltas: Deltas
  diversification: Diversification
  comparaison_benchmark: ComparaisonBenchmark | null
  badges: Badge[]
  exposition_devises: ExpositionDevise[]
}

export type RefreshScope = "quotes" | "veille" | "fundamentals" | "all"

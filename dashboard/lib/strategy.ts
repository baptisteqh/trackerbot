// Règles de rééquilibrage : analyse du portefeuille actuel + suggestions
// déterministes d'actions. Aucun ordre n'est passé — c'est de la
// suggestion pédagogique, pas du conseil financier.
//
// Chaque règle est une fonction pure qui prend le Rapport et retourne
// une Suggestion ou null. On les enchaîne et on trie par priorité.

import type {
  ExpositionDevise,
  LignePortefeuille,
  Metriques,
  Rapport,
} from "./types"

export type SuggestionPriority = "high" | "medium" | "low"
export type SuggestionCategory =
  | "concentration"
  | "diversification"
  | "risk"
  | "protection"
  | "profit"

export interface Suggestion {
  id: string
  priority: SuggestionPriority
  category: SuggestionCategory
  title: string
  rationale: string
  action: string
  tickers?: string[]
}

// Seuils déclaratifs — édite ici pour ajuster la sensibilité des règles.
const SEUILS = {
  positionSurponderee: 30, // %
  positionAlerte: 25, // %
  concentrationSecteur: 50, // %
  concentrationDevise: 80, // %
  concentrationDeviseAlerte: 65, // %
  hhiEleve: 3000,
  correlationForte: 0.85,
  gainNonSecurise: 25, // %
  perteNonProtegee: -10, // %
  couvertureStopLoss: 50, // % du portefeuille sans stop
  volatiliteEleve: 25, // %
}

const ORDRE_PRIORITE: Record<SuggestionPriority, number> = {
  high: 0,
  medium: 1,
  low: 2,
}

export function analyserStrategie(rapport: Rapport): Suggestion[] {
  const suggestions: Suggestion[] = []

  const push = (s: Suggestion | null) => {
    if (s) suggestions.push(s)
  }

  push(reglePositionSurponderee(rapport.lignes))
  push(regleConcentrationSecteur(rapport.diversification))
  push(regleConcentrationDevise(rapport.exposition_devises))
  push(regleHhiEleve(rapport.diversification.hhi_secteurs))
  push(regleCorrelationsFortes(rapport.diversification.paires_correlees))
  push(regleCouvertureStopLoss(rapport.lignes))
  push(regleGainsNonSecurises(rapport.lignes))
  push(reglePerteNonProtegee(rapport.lignes))
  push(regleVolatiliteExcessive(rapport.lignes))
  push(regleBetaEleve(rapport.metriques))

  return suggestions.sort(
    (a, b) => ORDRE_PRIORITE[a.priority] - ORDRE_PRIORITE[b.priority],
  )
}

// ---------- Règles individuelles ---------- //

function reglePositionSurponderee(lignes: LignePortefeuille[]): Suggestion | null {
  const grosse = [...lignes].sort((a, b) => b.poids_pct - a.poids_pct)[0]
  if (!grosse || grosse.poids_pct < SEUILS.positionAlerte) return null
  const priority: SuggestionPriority =
    grosse.poids_pct >= SEUILS.positionSurponderee ? "high" : "medium"
  return {
    id: "single-position-overweight",
    priority,
    category: "concentration",
    title: `${grosse.position.ticker} pèse ${grosse.poids_pct.toFixed(1)}% du portefeuille`,
    rationale: `Une position au-delà de ${SEUILS.positionAlerte}% expose le portefeuille à un risque idiosyncratique élevé : un mauvais trimestre sur ce titre pèserait de manière disproportionnée sur la performance globale.`,
    action: `Envisager de trimmer ${grosse.position.ticker} vers ${SEUILS.positionAlerte}% et redéployer sur les positions sous-pondérées ou un nouvel actif décorrélé.`,
    tickers: [grosse.position.ticker],
  }
}

function regleConcentrationSecteur(
  div: Rapport["diversification"],
): Suggestion | null {
  if (
    !div.plus_gros_secteur ||
    div.plus_gros_secteur_pct === null ||
    div.plus_gros_secteur_pct < SEUILS.concentrationSecteur
  )
    return null
  return {
    id: "sector-concentration",
    priority: div.plus_gros_secteur_pct >= 70 ? "high" : "medium",
    category: "diversification",
    title: `${div.plus_gros_secteur_pct.toFixed(0)}% concentré sur ${div.plus_gros_secteur}`,
    rationale: `Un secteur au-dessus de ${SEUILS.concentrationSecteur}% du portefeuille rend la performance très corrélée aux vents sectoriels : une rotation contre ce secteur (ex. resserrement monétaire pour la tech) toucherait beaucoup de positions en même temps.`,
    action: `Ajouter au moins une position dans un secteur défensif absent (santé, consommation de base, utilities) pour lisser la volatilité sectorielle.`,
  }
}

function regleConcentrationDevise(
  exp: ExpositionDevise[],
): Suggestion | null {
  if (exp.length === 0) return null
  const top = exp[0]
  if (top.poids_pct < SEUILS.concentrationDeviseAlerte) return null
  const priority: SuggestionPriority =
    top.poids_pct >= SEUILS.concentrationDevise ? "medium" : "low"
  return {
    id: "currency-concentration",
    priority,
    category: "diversification",
    title: `${top.poids_pct.toFixed(0)}% du portefeuille en ${top.devise}`,
    rationale: `Une exposition à une devise dominante ajoute un pari de change implicite : une variation de ${top.devise} contre ta devise de référence impacte l'ensemble du portefeuille indépendamment de la performance des actions.`,
    action: `Considérer une position sur un ETF international multi-devises ou un actif dans une autre zone monétaire pour réduire ce risque de change.`,
  }
}

function regleHhiEleve(hhi: number | null): Suggestion | null {
  if (hhi === null || hhi < SEUILS.hhiEleve) return null
  return {
    id: "hhi-high",
    priority: hhi >= 5000 ? "medium" : "low",
    category: "diversification",
    title: `Indice de concentration élevé (HHI ${Math.round(hhi)})`,
    rationale: `Un HHI au-dessus de ${SEUILS.hhiEleve} indique un portefeuille peu diversifié en secteurs. Les études empiriques montrent que 80% des gains de diversification s'obtiennent avec 8 à 12 positions bien réparties.`,
    action: `Ajouter 2 à 3 positions dans des secteurs actuellement absents pour faire baisser l'HHI vers 2000-2500.`,
  }
}

function regleCorrelationsFortes(
  paires: Rapport["diversification"]["paires_correlees"],
): Suggestion | null {
  if (paires.length === 0) return null
  const top = paires[0]
  if (Math.abs(top.correlation) < SEUILS.correlationForte) return null
  return {
    id: "correlated-pair",
    priority: "medium",
    category: "diversification",
    title: `${top.ticker_a} et ${top.ticker_b} sont corrélés à ${(top.correlation * 100).toFixed(0)}%`,
    rationale: `Deux positions dont les rendements suivent la même direction à ${(Math.abs(top.correlation) * 100).toFixed(0)}% n'apportent pas de diversification réelle. En pratique tu détiens l'équivalent d'une seule position en double.`,
    action: `Conserver la position avec le meilleur ratio Sharpe individuel et remplacer l'autre par une exposition décorrélée (ex. matière première, obligations, ou secteur défensif).`,
    tickers: [top.ticker_a, top.ticker_b],
  }
}

function regleCouvertureStopLoss(
  lignes: LignePortefeuille[],
): Suggestion | null {
  if (lignes.length === 0) return null
  const totalValeur = lignes.reduce((s, l) => s + l.valeur_courante, 0)
  if (totalValeur <= 0) return null
  const sansStopValeur = lignes
    .filter((l) => l.position.stop_loss === null)
    .reduce((s, l) => s + l.valeur_courante, 0)
  const pctSansStop = (sansStopValeur / totalValeur) * 100
  if (pctSansStop < SEUILS.couvertureStopLoss) return null
  return {
    id: "no-stop-loss",
    priority: pctSansStop >= 80 ? "high" : "medium",
    category: "protection",
    title: `${pctSansStop.toFixed(0)}% du portefeuille n'a pas de stop-loss`,
    rationale: `Sans stop-loss défini, tes positions restent exposées à un scénario baissier extrême. Un stop mécanique évite la paralysie émotionnelle qui aggrave généralement les pertes.`,
    action: `Ajouter un stop-loss à ${SEUILS.perteNonProtegee}%..-15% du prix d'entrée sur les positions non protégées, ou à un niveau technique clair (support ancien, moyenne mobile 200j).`,
  }
}

function regleGainsNonSecurises(
  lignes: LignePortefeuille[],
): Suggestion | null {
  const candidats = lignes.filter(
    (l) =>
      l.gain_pct >= SEUILS.gainNonSecurise &&
      l.position.take_profit === null,
  )
  if (candidats.length === 0) return null
  const meilleur = [...candidats].sort((a, b) => b.gain_pct - a.gain_pct)[0]
  return {
    id: "unlocked-gains",
    priority: "low",
    category: "profit",
    title: `${meilleur.position.ticker} affiche +${meilleur.gain_pct.toFixed(1)}% sans take-profit`,
    rationale: `Un gain latent significatif sans plan de sortie expose au risque de rendre le gain lors d'un retournement. La règle classique "let winners run" ne dispense pas de fixer un objectif partiel.`,
    action: `Poser un take-profit partiel (par exemple céder 25-33% de la position à un objectif +${(meilleur.gain_pct * 1.2).toFixed(0)}%) pour matérialiser une partie du gain.`,
    tickers: candidats.map((l) => l.position.ticker),
  }
}

function reglePerteNonProtegee(lignes: LignePortefeuille[]): Suggestion | null {
  const perdants = lignes.filter(
    (l) =>
      l.gain_pct <= SEUILS.perteNonProtegee &&
      l.position.stop_loss === null,
  )
  if (perdants.length === 0) return null
  const pire = [...perdants].sort((a, b) => a.gain_pct - b.gain_pct)[0]
  return {
    id: "losing-no-stop",
    priority: "high",
    category: "protection",
    title: `${pire.position.ticker} en perte de ${pire.gain_pct.toFixed(1)}% sans stop`,
    rationale: `Une position déjà en perte matérielle et non protégée peut continuer à se détériorer. Le biais d'aversion à la perte pousse souvent à laisser courir en espérant un retour à l'équilibre.`,
    action: `Décider maintenant : soit couper la position, soit poser un stop technique juste sous le point bas récent pour plafonner la perte additionnelle.`,
    tickers: perdants.map((l) => l.position.ticker),
  }
}

function regleVolatiliteExcessive(
  lignes: LignePortefeuille[],
): Suggestion | null {
  const volatiles = lignes.filter(
    (l) =>
      l.volatilite_20j_pct !== null &&
      l.volatilite_20j_pct >= SEUILS.volatiliteEleve &&
      l.poids_pct >= 10,
  )
  if (volatiles.length === 0) return null
  const pire = [...volatiles].sort(
    (a, b) => (b.volatilite_20j_pct ?? 0) - (a.volatilite_20j_pct ?? 0),
  )[0]
  return {
    id: "high-vol-large-position",
    priority: "medium",
    category: "risk",
    title: `${pire.position.ticker} : vol 20j ${pire.volatilite_20j_pct?.toFixed(0)}% sur ${pire.poids_pct.toFixed(0)}% du portefeuille`,
    rationale: `Une position à la fois volatile et significative dominera la volatilité globale du portefeuille. Elle mérite un sizing ajusté à son risque intrinsèque, pas au consensus.`,
    action: `Réduire le poids proportionnellement : diviser le poids cible par (vol_actuelle / vol_moyenne_portefeuille) pour équilibrer le risque contribué par chaque position.`,
    tickers: volatiles.map((l) => l.position.ticker),
  }
}

function regleBetaEleve(metriques: Metriques | null): Suggestion | null {
  if (!metriques || metriques.beta === null) return null
  if (metriques.beta < 1.3) return null
  return {
    id: "beta-high",
    priority: metriques.beta >= 1.6 ? "medium" : "low",
    category: "risk",
    title: `Beta ${metriques.beta.toFixed(2)} vs ${metriques.benchmark}`,
    rationale: `Un beta au-dessus de 1.3 signifie que le portefeuille amplifie les mouvements du marché : +/- 30% de sensibilité en plus. Attractif en marché haussier, douloureux en correction.`,
    action: `Ajouter une position à beta faible (utilities, staples, obligations, ou un ETF défensif) pour ramener le beta agrégé vers 1.0-1.2 selon ton horizon.`,
  }
}

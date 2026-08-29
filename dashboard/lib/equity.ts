// Helpers dérivés de la série d'équité côté client. Miroir simplifié
// des calculs Python : ici on n'a besoin que du max-drawdown affiché en
// pied du graphe et de la normalisation "rebase 0" pour le benchmark.

export function maxDrawdownPct(values: number[]): number | null {
  if (values.length === 0) return null
  let peak = values[0]
  let worst = 0
  for (const value of values) {
    if (value > peak) peak = value
    if (peak > 0) {
      const dd = ((peak - value) / peak) * 100
      if (dd > worst) worst = dd
    }
  }
  return worst
}

// Rebase une série sur la base 100 pour comparer benchmark et portefeuille
// sur le même axe Y.
export function rebase100(values: number[]): number[] {
  if (values.length === 0) return []
  const base = values[0]
  if (base === 0) return values.map(() => 100)
  return values.map((v) => (v / base) * 100)
}

// Génère des labels de date sans dates réelles (l'API ne renvoie que des
// valeurs). On étale sur "days" jours de bourse à reculons depuis today.
export function buildDailyLabels(count: number, endDate = new Date()): string[] {
  if (count <= 0) return []
  const labels: string[] = []
  const current = new Date(endDate)
  while (labels.length < count) {
    const day = current.getDay()
    if (day !== 0 && day !== 6) {
      labels.push(current.toISOString().slice(0, 10))
    }
    current.setDate(current.getDate() - 1)
  }
  return labels.reverse()
}

export type EquityWindow = "1M" | "3M" | "6M" | "YTD" | "MAX"

const WINDOW_DAYS: Record<Exclude<EquityWindow, "YTD" | "MAX">, number> = {
  "1M": 21,
  "3M": 63,
  "6M": 126,
}

// Tronque la série + les labels associés selon la fenêtre demandée.
export function sliceWindow<T>(
  values: T[],
  labels: string[],
  window: EquityWindow,
): { values: T[]; labels: string[] } {
  if (values.length === 0) return { values, labels }
  if (window === "MAX") return { values, labels }
  if (window === "YTD") {
    const year = new Date().getFullYear()
    const start = labels.findIndex((d) => d.startsWith(String(year)))
    if (start <= 0) return { values, labels }
    return { values: values.slice(start), labels: labels.slice(start) }
  }
  const n = WINDOW_DAYS[window]
  if (values.length <= n) return { values, labels }
  return { values: values.slice(-n), labels: labels.slice(-n) }
}

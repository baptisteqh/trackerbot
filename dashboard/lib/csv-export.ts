// Export CSV cote client : on serialise les lignes de position + deltas
// depuis le payload deja affiche, sans nouvel appel API.
//
// Les champs numeriques utilisent "." comme separateur decimal (locale-agnostique),
// les valeurs sont quotees si elles contiennent virgule/quote/newline.

import type { Rapport } from "./types"

export const CSV_HEADERS = [
  "ticker",
  "libelle",
  "quantite",
  "prix_entree",
  "prix",
  "poids_pct",
  "montant_investi",
  "valeur_courante",
  "gain_absolu",
  "gain_pct",
  "rsi_14",
  "sma_20",
  "sma_50",
  "volatilite_20j_pct",
  "stop_loss",
  "take_profit",
  "est_long",
  "ouverte_le",
] as const

export function rapportToCsv(rapport: Rapport): string {
  const rows: string[] = [CSV_HEADERS.join(",")]
  for (const l of rapport.lignes) {
    const cells = [
      l.position.ticker,
      l.position.libelle ?? "",
      num(l.position.quantite),
      num(l.position.prix_entree),
      num(l.cotation?.prix ?? null),
      num(l.poids_pct),
      num(l.montant_investi),
      num(l.valeur_courante),
      num(l.gain_absolu),
      num(l.gain_pct),
      num(l.rsi_14),
      num(l.sma_20),
      num(l.sma_50),
      num(l.volatilite_20j_pct),
      num(l.position.stop_loss),
      num(l.position.take_profit),
      l.position.est_long ? "long" : "short",
      l.position.ouverte_le ?? "",
    ]
    rows.push(cells.map(escape).join(","))
  }
  return rows.join("\n") + "\n"
}

export function downloadCsv(rapport: Rapport): void {
  const csv = rapportToCsv(rapport)
  const stamp = rapport.genere_le.replace(/[^0-9]/g, "").slice(0, 8)
  const filename = `trackerbot-snapshot-${stamp || todayStamp()}.csv`
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function num(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return ""
  return String(value)
}

function escape(cell: string | number): string {
  const s = String(cell)
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

function todayStamp(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${y}${m}${day}`
}

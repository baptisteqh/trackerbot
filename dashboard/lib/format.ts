// Formatage cohérent pour tous les composants du dashboard.
// Les tuiles utilisent USD par défaut ; devise dérivée de la première position
// si un jour on doit supporter autre chose.

export function formatCurrency(
  value: number | null | undefined,
  options: { compact?: boolean; showSign?: boolean } = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—"
  }
  const { compact = false, showSign = false } = options
  const abs = Math.abs(value)
  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : abs >= 100 ? 0 : 2,
  })
  const rendered = formatter.format(Math.abs(value))
  if (showSign) {
    if (value > 0) return `+${rendered}`
    if (value < 0) return `-${rendered}`
  } else if (value < 0) {
    return `-${rendered}`
  }
  return rendered
}

export function formatPercent(
  value: number | null | undefined,
  options: { fractionDigits?: number; showSign?: boolean } = {},
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—"
  }
  const { fractionDigits = 2, showSign = false } = options
  const rendered = `${Math.abs(value).toFixed(fractionDigits)}%`
  if (showSign) {
    if (value > 0) return `+${rendered}`
    if (value < 0) return `-${rendered}`
  } else if (value < 0) {
    return `-${rendered}`
  }
  return rendered
}

export function formatNumber(
  value: number | null | undefined,
  fractionDigits = 2,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—"
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

// Compare la valeur à 0 pour choisir la couleur du delta.
// Retourne une classe Tailwind qui pointe vers un token CSS custom.
export function pnlColorClass(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value) || value === 0) {
    return "text-muted-foreground"
  }
  return value > 0 ? "text-[var(--pnl-positive)]" : "text-[var(--pnl-negative)]"
}

export function formatDateLong(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
}

export function formatDateShort(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
  })
}

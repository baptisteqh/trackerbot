import { cn } from "@/lib/utils"

// Pill colorée soft-bg + border 1px + text bold monospace.
// Pattern extrait de Fey Screener + Bloomberg Movers + Fidelity Positions.
// Un seul look — vert pour up, rouge pour down. Ne surligne PAS les zéros
// (neutre = muted plain text).

interface PnlPillProps {
  value: number | null | undefined
  format?: "abs" | "pct"
  size?: "sm" | "md"
  solid?: boolean // si true, pattern Stake/Fidelity (bg saturé, texte noir/blanc)
  currency?: string
  className?: string
}

export function PnlPill({
  value,
  format = "pct",
  size = "sm",
  solid = false,
  currency = "$",
  className,
}: PnlPillProps) {
  if (value === null || value === undefined) {
    return <span className={cn("text-muted-foreground/60 text-xs", className)}>—</span>
  }

  const isPositive = value > 0
  const isNegative = value < 0
  const formatted = format === "pct" ? formatPct(value) : formatAbs(value, currency)

  const base = cn(
    "inline-flex items-center gap-1 rounded font-mono font-semibold tabular-nums whitespace-nowrap",
    size === "sm" && "px-1.5 py-0.5 text-xs",
    size === "md" && "px-2 py-1 text-sm",
  )

  if (solid) {
    return (
      <span
        className={cn(
          base,
          "rounded-md",
          isPositive && "bg-primary text-primary-foreground",
          isNegative && "bg-destructive text-white",
          !isPositive && !isNegative && "bg-secondary text-muted-foreground",
          className,
        )}
      >
        {isPositive ? "+" : ""}
        {formatted}
      </span>
    )
  }

  return (
    <span
      className={cn(
        base,
        isPositive && "bg-primary/10 text-primary border border-primary/20",
        isNegative && "bg-destructive/10 text-destructive border border-destructive/20",
        !isPositive && !isNegative && "bg-secondary text-muted-foreground border border-border",
        className,
      )}
    >
      {isPositive ? "+" : ""}
      {formatted}
    </span>
  )
}

function formatPct(value: number): string {
  return `${value.toFixed(2)}%`
}

function formatAbs(value: number, currency: string): string {
  const sign = value < 0 ? "-" : ""
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `${sign}${currency}${(abs / 1_000_000).toFixed(2)}M`
  if (abs >= 10_000) return `${sign}${currency}${(abs / 1_000).toFixed(1)}k`
  return `${sign}${currency}${abs.toLocaleString("en-US", { maximumFractionDigits: 2 })}`
}

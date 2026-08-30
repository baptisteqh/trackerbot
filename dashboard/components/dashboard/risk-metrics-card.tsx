"use client"

import * as React from "react"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { Metriques } from "@/lib/types"
import { cn } from "@/lib/utils"

interface RiskMetricsCardProps {
  metriques: Metriques | null
}

// Tuiles Sharpe / Sortino / MaxDD / Vol.
// Convention couleurs :
//   Sharpe/Sortino >= 1.0 -> vert, 0..1 -> muted, < 0 -> rouge
//   MaxDD < 10 % -> vert, 10..20 % -> ambre, >= 20 % -> rouge
export default function RiskMetricsCard({ metriques }: RiskMetricsCardProps) {
  if (!metriques) return null

  const items: Array<{
    label: string
    value: number | null
    format: (n: number) => string
    color: string
    tooltip: string
  }> = [
    {
      label: "Sharpe",
      value: metriques.sharpe,
      format: (n) => n.toFixed(2),
      color: ratioColor(metriques.sharpe),
      tooltip:
        "Return per unit of total risk (annualized). > 1 is considered good, > 2 excellent.",
    },
    {
      label: "Sortino",
      value: metriques.sortino,
      format: (n) => n.toFixed(2),
      color: ratioColor(metriques.sortino),
      tooltip:
        "Same as Sharpe but only penalizes downside volatility. Usually higher than Sharpe.",
    },
    {
      label: "Calmar",
      value: metriques.calmar,
      format: (n) => n.toFixed(2),
      color: ratioColor(metriques.calmar),
      tooltip:
        "Annual return divided by Max Drawdown. Reward relative to worst historical pain.",
    },
    {
      label: "Max Drawdown",
      value: metriques.max_drawdown_pct,
      format: (n) => `${n.toFixed(1)}%`,
      color: drawdownColor(metriques.max_drawdown_pct),
      tooltip: "Worst peak-to-trough decline of the portfolio equity curve.",
    },
    {
      label: "Volatility",
      value: metriques.volatilite_annuelle_pct,
      format: (n) => `${n.toFixed(1)}%`,
      color: "text-foreground/80",
      tooltip: "Annualized standard deviation of daily returns.",
    },
    {
      label: "VaR 95%",
      value: metriques.var_95_pct,
      format: (n) => `${n.toFixed(1)}%`,
      color: drawdownColor(metriques.var_95_pct !== null ? metriques.var_95_pct * 3 : null),
      tooltip:
        "Historical Value-at-Risk: 5% of past sessions saw a loss worse than this in a single day.",
    },
    {
      label: "Alpha",
      value: metriques.alpha_annuel_pct,
      format: (n) => `${n > 0 ? "+" : ""}${n.toFixed(1)}%`,
      color: alphaColor(metriques.alpha_annuel_pct),
      tooltip: metriques.benchmark
        ? `Jensen's alpha vs ${metriques.benchmark} (annualized). Value above what pure beta explains.`
        : "Jensen's alpha vs benchmark (annualized). Value above what pure beta explains.",
    },
    {
      label: "Info ratio",
      value: metriques.information_ratio,
      format: (n) => n.toFixed(2),
      color: ratioColor(metriques.information_ratio),
      tooltip:
        "Consistency of active outperformance vs benchmark. Above 0.5 is solid, above 1 is exceptional.",
    },
  ]

  return (
    <Card className="h-full border border-border/60 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 px-5 py-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Risk metrics
        </h2>
        <span className="text-xs text-muted-foreground">Annualized · 252d</span>
      </CardHeader>
      <CardContent className="p-5">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {items.map((item, i) => (
            <Tooltip key={item.label}>
              <TooltipTrigger
                render={
                  <div
                    className="tb-fade-up flex cursor-help flex-col gap-1 rounded-md border border-border/40 bg-white/[0.015] p-3 transition-colors hover:border-border/70 hover:bg-white/[0.03]"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                      {item.label}
                    </span>
                    <span
                      className={cn(
                        "tb-count-in font-mono text-2xl font-semibold tabular-nums leading-tight",
                        item.color,
                      )}
                      style={{ animationDelay: `${i * 60 + 80}ms` }}
                    >
                      {item.value === null ? "—" : item.format(item.value)}
                    </span>
                  </div>
                }
              />
              <TooltipContent className="max-w-[260px] text-xs">
                {item.tooltip}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function ratioColor(value: number | null): string {
  if (value === null) return "text-muted-foreground"
  if (value >= 1) return "text-[var(--pnl-positive)]"
  if (value < 0) return "text-[var(--pnl-negative)]"
  return "text-foreground/70"
}

function drawdownColor(value: number | null): string {
  if (value === null) return "text-muted-foreground"
  if (value >= 20) return "text-[var(--pnl-negative)]"
  if (value >= 10) return "text-[var(--chart-3)]"
  return "text-[var(--pnl-positive)]"
}

function alphaColor(value: number | null): string {
  if (value === null) return "text-muted-foreground"
  if (value > 0) return "text-[var(--pnl-positive)]"
  if (value < 0) return "text-[var(--pnl-negative)]"
  return "text-foreground/70"
}

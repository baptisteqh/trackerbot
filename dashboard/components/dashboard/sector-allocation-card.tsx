"use client"

import { AlertTriangleIcon } from "lucide-react"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { Diversification } from "@/lib/types"
import { cn } from "@/lib/utils"

interface SectorAllocationCardProps {
  diversification: Diversification
  totalPositions: number
}

// Barres horizontales sectorielles + trio d'indicateurs cle (N_eff,
// diversification ratio, correlation moyenne). Pattern extrait de
// Copilot Money Allocation + Origin Allocation & risk : barre dominante
// large, secteurs en cascade, muted color pour ceux qui dominent
// tellement qu'ils sont un risque.

export default function SectorAllocationCard({
  diversification,
  totalPositions,
}: SectorAllocationCardProps) {
  const secteurs = Object.entries(diversification.poids_par_secteur)
  const surconcentre =
    diversification.plus_gros_secteur_pct != null &&
    diversification.plus_gros_secteur_pct >= 40

  return (
    <Card className="h-full border border-border/60 bg-card shadow-none">
      <CardHeader className="border-b border-border/60 px-5 py-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Sector allocation
          </h2>
          {surconcentre ? (
            <Tooltip>
              <TooltipTrigger
                render={
                  <span className="inline-flex items-center gap-1 rounded-sm bg-[var(--chart-3)]/10 px-2 py-0.5 text-[10px] font-medium text-[var(--chart-3)]">
                    <AlertTriangleIcon className="size-3" />
                    Overexposed
                  </span>
                }
              />
              <TooltipContent>
                {diversification.plus_gros_secteur} weight is over 40% —
                consider rebalancing.
              </TooltipContent>
            </Tooltip>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5 p-5">
        {secteurs.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Sector data missing. Run{" "}
            <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-xs">
              trackerbot status --fondamentaux
            </code>{" "}
            to populate.
          </p>
        ) : (
          <ul className="flex flex-col gap-2.5">
            {secteurs.map(([secteur, pct]) => (
              <SectorBar
                key={secteur}
                name={secteur}
                pct={pct}
                emphasise={pct >= 40}
              />
            ))}
          </ul>
        )}

        <div className="grid grid-cols-3 gap-3 border-t border-border/60 pt-4">
          <Stat
            label="N_eff"
            value={
              diversification.positions_effectives != null
                ? diversification.positions_effectives.toFixed(1)
                : "—"
            }
            hint={`Effective number of positions vs ${totalPositions} in the portfolio.`}
          />
          <Stat
            label="Div ratio"
            value={
              diversification.ratio_diversification != null
                ? diversification.ratio_diversification.toFixed(2)
                : "—"
            }
            hint="Higher than 1 means diversification is actually reducing your volatility."
          />
          <Stat
            label="Avg corr"
            value={
              diversification.correlation_moyenne != null
                ? diversification.correlation_moyenne.toFixed(2)
                : "—"
            }
            hint="Weighted average pairwise correlation. Below 0.5 = well-spread; above 0.8 = your positions all move together."
          />
        </div>

        {diversification.paires_correlees.length > 0 ? (
          <div className="rounded border border-[var(--chart-3)]/20 bg-[var(--chart-3)]/[0.06] p-3">
            <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--chart-3)]">
              High correlation
            </p>
            <ul className="mt-1.5 space-y-1">
              {diversification.paires_correlees.slice(0, 3).map((paire) => (
                <li
                  key={`${paire.ticker_a}-${paire.ticker_b}`}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="font-mono">
                    {paire.ticker_a} <span className="text-muted-foreground">×</span>{" "}
                    {paire.ticker_b}
                  </span>
                  <span className="font-mono tabular-nums text-[var(--chart-3)]">
                    {paire.correlation.toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function SectorBar({
  name,
  pct,
  emphasise,
}: {
  name: string
  pct: number
  emphasise?: boolean
}) {
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className={cn(emphasise ? "text-foreground" : "text-foreground/85")}>
          {name}
        </span>
        <span className="font-mono tabular-nums text-muted-foreground">
          {pct.toFixed(1)}%
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary/40">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            emphasise
              ? "bg-[var(--chart-3)]"
              : "bg-primary",
          )}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </li>
  )
}

function Stat({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint: string
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <button type="button" className="flex flex-col items-start gap-0.5 text-left">
            <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
              {label}
            </span>
            <span className="font-mono text-base tabular-nums">{value}</span>
          </button>
        }
      />
      <TooltipContent>
        <p className="max-w-[240px] text-xs">{hint}</p>
      </TooltipContent>
    </Tooltip>
  )
}

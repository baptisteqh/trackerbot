"use client"

import * as React from "react"

import { Card } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import type { Deltas, Metriques } from "@/lib/types"
import {
  formatCurrency,
  formatNumber,
  formatPercent,
  pnlColorClass,
} from "@/lib/format"
import { PnlPill } from "./pnl-pill"

// Pattern extrait de Public iOS Portfolio + Copilot Money iOS Investments +
// Lightyear iOS Portfolio : label uppercase muted en haut, chiffre hero
// enorme au centre-gauche, delta signale sur une seule ligne en pied.
// On evite d'empiler 4 deltas comme un tableau — c'est le meta.

interface MetricTilesProps {
  currentValue: number
  totalPnlAbs: number
  totalPnlPct: number
  deltas: Deltas
  metriques: Metriques | null
}

export default function MetricTiles({
  currentValue,
  totalPnlAbs,
  totalPnlPct,
  deltas,
  metriques,
}: MetricTilesProps) {
  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Tile label="Current value">
        <HeroNumber value={formatCurrency(currentValue)} />
        <MetaRow>
          <PnlPill value={deltas.pnl_1d_pct} format="pct" />
          <span className="text-xs text-muted-foreground">today</span>
        </MetaRow>
      </Tile>

      <Tile label="Total PnL">
        <HeroNumber
          value={formatCurrency(totalPnlAbs, { showSign: true })}
          colorClass={pnlColorClass(totalPnlAbs)}
        />
        <MetaRow>
          <PnlPill value={totalPnlPct} format="pct" />
          <span className="text-xs text-muted-foreground">all time</span>
          {deltas.pnl_30d_pct !== null ? (
            <>
              <span className="text-xs text-muted-foreground/50">·</span>
              <span
                className={cn(
                  "font-mono text-xs tabular-nums",
                  pnlColorClass(deltas.pnl_30d_pct),
                )}
              >
                {formatPercent(deltas.pnl_30d_pct, { showSign: true })}
              </span>
              <span className="text-xs text-muted-foreground">30d</span>
            </>
          ) : null}
        </MetaRow>
      </Tile>

      <Tile
        label="Sharpe"
        hint="Excess return per unit of volatility, annualized (Rf = 4%)."
      >
        <HeroNumber value={formatNumber(metriques?.sharpe ?? null)} />
        <MetaRow>
          {metriques?.volatilite_annuelle_pct != null ? (
            <span className="text-xs text-muted-foreground">
              Vol{" "}
              <span className="font-mono tabular-nums text-foreground/80">
                {formatPercent(metriques.volatilite_annuelle_pct)}
              </span>
            </span>
          ) : (
            <NotEnough />
          )}
          {metriques?.rendement_annuel_pct != null ? (
            <>
              <span className="text-xs text-muted-foreground/50">·</span>
              <span className="text-xs text-muted-foreground">
                Return{" "}
                <span
                  className={cn(
                    "font-mono tabular-nums",
                    pnlColorClass(metriques.rendement_annuel_pct),
                  )}
                >
                  {formatPercent(metriques.rendement_annuel_pct, { showSign: true })}
                </span>
              </span>
            </>
          ) : null}
        </MetaRow>
      </Tile>

      <Tile
        label="Max drawdown"
        hint="Largest peak-to-trough decline of the equity curve."
      >
        <HeroNumber
          value={
            metriques?.max_drawdown_pct != null
              ? `-${metriques.max_drawdown_pct.toFixed(2)}%`
              : "—"
          }
          colorClass={
            metriques?.max_drawdown_pct && metriques.max_drawdown_pct > 0
              ? "text-destructive"
              : undefined
          }
        />
        <MetaRow>
          {metriques?.beta != null && metriques.benchmark ? (
            <span className="text-xs text-muted-foreground">
              Beta vs {metriques.benchmark}{" "}
              <span className="font-mono tabular-nums text-foreground/80">
                {metriques.beta.toFixed(2)}
              </span>
            </span>
          ) : (
            <NotEnough />
          )}
        </MetaRow>
      </Tile>
    </section>
  )
}

interface TileProps {
  label: string
  hint?: string
  children: React.ReactNode
}

function Tile({ label, hint, children }: TileProps) {
  const heading = (
    <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
      {label}
    </span>
  )
  return (
    <Card className="flex min-h-[128px] flex-col justify-between gap-5 border border-border/60 bg-card p-5 shadow-none">
      <div>
        {hint ? (
          <Tooltip>
            <TooltipTrigger render={<button type="button">{heading}</button>} />
            <TooltipContent>{hint}</TooltipContent>
          </Tooltip>
        ) : (
          heading
        )}
      </div>
      <div>{children}</div>
    </Card>
  )
}

function HeroNumber({
  value,
  colorClass,
}: {
  value: string
  colorClass?: string
}) {
  return (
    <p
      className={cn(
        "font-mono text-[32px] font-semibold leading-none tracking-tight tabular-nums",
        colorClass,
      )}
    >
      {value}
    </p>
  )
}

function MetaRow({ children }: { children: React.ReactNode }) {
  return <div className="mt-3 flex flex-wrap items-center gap-1.5">{children}</div>
}

function NotEnough() {
  return <span className="text-xs text-muted-foreground/60">Not enough history yet.</span>
}

"use client"

import * as React from "react"
import { Area, AreaChart, ResponsiveContainer, YAxis } from "recharts"

import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import type { LignePortefeuille, Signal } from "@/lib/types"
import {
  formatCurrency,
  formatNumber,
  formatPercent,
  pnlColorClass,
} from "@/lib/format"
import { cn } from "@/lib/utils"

interface TickerSheetProps {
  ligne: LignePortefeuille | null
  signals: Signal[]
  onOpenChange: (open: boolean) => void
}

export default function TickerSheet({ ligne, signals, onOpenChange }: TickerSheetProps) {
  const open = ligne !== null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-md"
      >
        {ligne ? <TickerSheetBody ligne={ligne} signals={signals} /> : null}
      </SheetContent>
    </Sheet>
  )
}

function TickerSheetBody({
  ligne,
  signals,
}: {
  ligne: LignePortefeuille
  signals: Signal[]
}) {
  const { position, cotation, fondamentaux } = ligne
  const chartData = React.useMemo(() => {
    if (!cotation) return []
    return cotation.clotures.slice(-90).map((v, i) => ({ i, v }))
  }, [cotation])

  const trendUp = ligne.gain_absolu >= 0
  const areaColor = trendUp ? "var(--pnl-positive)" : "var(--pnl-negative)"

  return (
    <>
      <SheetHeader className="tb-fade-up border-b border-border/50 px-5 pb-4">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "h-10 w-1 rounded-full",
              trendUp ? "bg-[var(--pnl-positive)]" : "bg-[var(--pnl-negative)]",
            )}
            aria-hidden
          />
          <div className="flex flex-col leading-tight">
            <SheetTitle className="font-mono text-lg font-semibold tracking-tight">
              {position.ticker}
            </SheetTitle>
            <SheetDescription className="text-[11px]">
              {position.libelle ?? position.ticker}
              {position.est_long ? null : (
                <Badge
                  variant="outline"
                  className="ml-2 border-destructive/40 px-1 py-0 font-mono text-[9px] uppercase text-destructive"
                >
                  Short
                </Badge>
              )}
            </SheetDescription>
          </div>
        </div>
      </SheetHeader>

      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-5 px-5 py-5">
          {/* Prix + PnL headline */}
          <section
            className="tb-fade-up flex items-baseline gap-4"
            style={{ animationDelay: "40ms" }}
          >
            <span className="font-mono text-3xl font-semibold tabular-nums">
              {cotation ? formatCurrency(cotation.prix) : "—"}
            </span>
            <span
              className={cn(
                "font-mono text-base tabular-nums",
                pnlColorClass(ligne.gain_absolu),
              )}
            >
              {formatCurrency(ligne.gain_absolu, { showSign: true })}
              <span className="ml-1 text-sm opacity-80">
                ({formatPercent(ligne.gain_pct, { showSign: true })})
              </span>
            </span>
          </section>

          {/* Mini chart 90j */}
          {chartData.length > 1 ? (
            <section
              className="tb-fade-up h-[140px] rounded-md border border-border/40 bg-white/[0.015] p-2"
              style={{ animationDelay: "100ms" }}
            >
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="tb-ticker-area" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={areaColor} stopOpacity={0.35} />
                      <stop offset="100%" stopColor={areaColor} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <YAxis domain={["dataMin", "dataMax"]} hide />
                  <Area
                    type="monotone"
                    dataKey="v"
                    stroke={areaColor}
                    strokeWidth={1.5}
                    fill="url(#tb-ticker-area)"
                    isAnimationActive
                    animationDuration={520}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </section>
          ) : null}

          {/* Position facts */}
          <FactGrid
            delay={160}
            items={[
              ["Quantity", formatNumber(position.quantite, position.quantite % 1 === 0 ? 0 : 2)],
              ["Entry", formatCurrency(position.prix_entree)],
              ["Weight", formatPercent(ligne.poids_pct, { fractionDigits: 1 })],
              ["Value", formatCurrency(ligne.valeur_courante)],
              ["Stop loss", position.stop_loss !== null ? formatCurrency(position.stop_loss) : "—"],
              ["Take profit", position.take_profit !== null ? formatCurrency(position.take_profit) : "—"],
            ]}
          />

          {/* Technicals */}
          <FactGrid
            title="Technicals"
            delay={220}
            items={[
              ["RSI 14", formatNumber(ligne.rsi_14, 0)],
              ["SMA 20", formatCurrency(ligne.sma_20)],
              ["SMA 50", formatCurrency(ligne.sma_50)],
              ["Vol 20d", formatPercent(ligne.volatilite_20j_pct, { fractionDigits: 1 })],
            ]}
          />

          {/* Fondamentaux (optionnel) */}
          {fondamentaux ? (
            <FactGrid
              title="Fundamentals"
              delay={280}
              items={[
                ["PER", formatNumber(fondamentaux.per, 1)],
                ["P/B", formatNumber(fondamentaux.price_to_book, 2)],
                ["ROE", formatPercent(fondamentaux.roe_pct, { fractionDigits: 1 })],
                ["Margin", formatPercent(fondamentaux.marge_nette_pct, { fractionDigits: 1 })],
                ["Debt/Eq", formatNumber(fondamentaux.debt_to_equity, 2)],
                ["Div yield", formatPercent(fondamentaux.dividend_yield_pct, { fractionDigits: 2 })],
              ]}
            />
          ) : null}

          {/* Signaux */}
          <section
            className="tb-fade-up flex flex-col gap-2"
            style={{ animationDelay: "340ms" }}
          >
            <h3 className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Signals ({signals.length})
            </h3>
            {signals.length === 0 ? (
              <p className="text-sm text-muted-foreground">No active signals for this ticker.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {signals.map((s, i) => (
                  <li
                    key={i}
                    className="tb-fade-up flex items-start gap-2 rounded-md border border-border/40 bg-white/[0.015] p-2.5 text-sm"
                    style={{ animationDelay: `${360 + i * 40}ms` }}
                  >
                    <span
                      className={cn(
                        "mt-0.5 h-4 w-0.5 shrink-0 rounded",
                        s.niveau === "alerte"
                          ? "bg-destructive"
                          : s.niveau === "attention"
                            ? "bg-[var(--chart-3)]"
                            : "bg-muted-foreground/40",
                      )}
                      aria-hidden
                    />
                    <div className="flex flex-col leading-snug">
                      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                        {s.regle}
                      </span>
                      <span>{s.message}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </ScrollArea>
    </>
  )
}

function FactGrid({
  items,
  title,
  delay,
}: {
  items: Array<[string, string]>
  title?: string
  delay: number
}) {
  return (
    <section
      className="tb-fade-up flex flex-col gap-2"
      style={{ animationDelay: `${delay}ms` }}
    >
      {title ? (
        <h3 className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {title}
        </h3>
      ) : null}
      <dl className="grid grid-cols-2 gap-2">
        {items.map(([label, value]) => (
          <div
            key={label}
            className="flex flex-col gap-0.5 rounded-md border border-border/40 bg-white/[0.015] px-3 py-2"
          >
            <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
              {label}
            </dt>
            <dd className="font-mono text-sm tabular-nums text-foreground/90">
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

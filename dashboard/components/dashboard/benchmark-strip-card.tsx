"use client"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { BenchmarkWindow, ComparaisonBenchmark } from "@/lib/types"
import { cn } from "@/lib/utils"
import { formatPercent } from "@/lib/format"
import { PnlPill } from "./pnl-pill"

interface BenchmarkStripCardProps {
  comparaison: ComparaisonBenchmark | null
}

const WINDOWS: BenchmarkWindow[] = ["1M", "3M", "YTD", "1Y"]

// 4 colonnes : la perf du portefeuille au-dessus, la perf du benchmark en
// dessous, et un pill d'outperformance en accent. Pattern inspire de
// Monarch Investments (comparaison Your Portfolio / S&P 500 par periode)
// mais en version condensee pour un dashboard perso.

export default function BenchmarkStripCard({ comparaison }: BenchmarkStripCardProps) {
  if (!comparaison) {
    return (
      <Card className="h-full border border-border/60 bg-card shadow-none">
        <CardHeader className="border-b border-border/60 px-5 py-4">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            vs Benchmark
          </h2>
        </CardHeader>
        <CardContent className="p-5">
          <p className="text-sm text-muted-foreground">
            No benchmark configured. Pass{" "}
            <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-xs">
              --benchmark SPY
            </code>{" "}
            to compare.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="h-full border border-border/60 bg-card shadow-none">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 px-5 py-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          vs {comparaison.benchmark}
        </h2>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
          Outperformance
        </span>
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid grid-cols-4 divide-x divide-border/40">
          {WINDOWS.map((window) => (
            <WindowCell
              key={window}
              window={window}
              portefeuille={comparaison.perf_portefeuille[window]}
              benchmark={comparaison.perf_benchmark[window]}
              delta={comparaison.outperformance[window]}
              benchLabel={comparaison.benchmark}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function WindowCell({
  window,
  portefeuille,
  benchmark,
  delta,
  benchLabel,
}: {
  window: BenchmarkWindow
  portefeuille: number | null
  benchmark: number | null
  delta: number | null
  benchLabel: string
}) {
  const available = portefeuille !== null && benchmark !== null
  return (
    <div className="flex flex-col gap-2 px-3 py-4 md:px-4">
      <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        {window}
      </span>
      {available ? (
        <>
          <div className="flex items-baseline gap-1.5">
            <span
              className={cn(
                "font-mono text-lg font-semibold tabular-nums",
                portefeuille! >= 0
                  ? "text-[var(--pnl-positive)]"
                  : "text-[var(--pnl-negative)]",
              )}
            >
              {formatPercent(portefeuille!, { showSign: true })}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span className="uppercase tracking-wider">{benchLabel}</span>
            <span className="font-mono tabular-nums">
              {formatPercent(benchmark!, { showSign: true })}
            </span>
          </div>
          <div className="pt-1">
            <PnlPill value={delta} format="pct" />
          </div>
        </>
      ) : (
        <p className="text-xs text-muted-foreground/60">
          Not enough
          <br />
          history yet.
        </p>
      )}
    </div>
  )
}

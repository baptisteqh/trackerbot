"use client"

import * as React from "react"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { LignePortefeuille } from "@/lib/types"
import { formatNumber, formatPercent } from "@/lib/format"
import { cn } from "@/lib/utils"

interface ValuationCardProps {
  lignes: LignePortefeuille[]
}

interface Row {
  ticker: string
  score: number
  per: number | null
  pb: number | null
  margin: number | null
  roe: number | null
  de: number | null
}

export default function ValuationCard({ lignes }: ValuationCardProps) {
  const rows = React.useMemo<Row[]>(() => {
    return lignes
      .filter((l) => l.score_valorisation && l.fondamentaux)
      .map((l) => ({
        ticker: l.position.ticker,
        score: l.score_valorisation!.score,
        per: l.fondamentaux!.per,
        pb: l.fondamentaux!.price_to_book,
        margin: l.fondamentaux!.marge_nette_pct,
        roe: l.fondamentaux!.roe_pct,
        de: l.fondamentaux!.debt_to_equity,
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 5)
  }, [lignes])

  return (
    <Card className="h-full border border-border/60 shadow-none">
      <CardHeader className="border-b border-border/60 px-5 py-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Valuation
        </h2>
        <p className="mt-1 text-xs text-muted-foreground/70">Top scored 0–7 with fundamentals</p>
      </CardHeader>
      <CardContent className="p-5">
        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No fundamentals available. Run{" "}
            <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-xs">
              trackerbot status --fondamentaux
            </code>{" "}
            to populate.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {rows.map((r) => (
              <li key={r.ticker} className="flex flex-col gap-1.5">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm">{r.ticker}</span>
                  <ScoreBar score={r.score} />
                  <span className="ml-auto font-mono text-[11px] text-muted-foreground tabular-nums">
                    {r.score}/7
                  </span>
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground">
                  <Metric label="PER" value={formatNumber(r.per, 1)} />
                  <Metric label="PB" value={formatNumber(r.pb, 1)} />
                  <Metric label="Margin" value={formatPercent(r.margin, { fractionDigits: 1 })} />
                  <Metric label="ROE" value={formatPercent(r.roe, { fractionDigits: 1 })} />
                  <Metric label="D/E" value={formatNumber(r.de, 2)} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="uppercase tracking-wide">{label}</span>
      <span className="font-mono text-foreground tabular-nums">{value}</span>
    </span>
  )
}

function ScoreBar({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(7, score))
  return (
    <div className="flex gap-[3px]" aria-label={`Score ${clamped} of 7`}>
      {Array.from({ length: 7 }).map((_, i) => (
        <span
          key={i}
          className={cn(
            "h-1.5 w-4 rounded-[1px]",
            i < clamped ? "bg-primary" : "bg-muted",
          )}
        />
      ))}
    </div>
  )
}

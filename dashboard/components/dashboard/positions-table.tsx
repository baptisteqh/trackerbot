"use client"

import * as React from "react"
import { ArrowDownIcon, ArrowUpIcon, ChevronDownIcon, ChevronUpIcon } from "lucide-react"
import { Line, LineChart, ResponsiveContainer } from "recharts"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { LignePortefeuille, Signal } from "@/lib/types"
import {
  formatCurrency,
  formatNumber,
  formatPercent,
  pnlColorClass,
} from "@/lib/format"
import { cn } from "@/lib/utils"
import { PnlPill } from "./pnl-pill"

// Table style Fey Screener / Kraken Favorites : rows sur fond card, hover
// discret, sparkline colore par trend, ticker + nom stacked, PnL pills soft.

type SortKey =
  | "ticker"
  | "poids_pct"
  | "prix"
  | "variation_jour_pct"
  | "gain_absolu"
  | "gain_pct"
  | "rsi_14"
  | "volatilite_20j_pct"
  | "score"

interface PositionsTableProps {
  lignes: LignePortefeuille[]
  signaux: Signal[]
  tickersManquants: string[]
}

export default function PositionsTable({
  lignes,
  signaux,
  tickersManquants,
}: PositionsTableProps) {
  const [sort, setSort] = React.useState<{ key: SortKey; asc: boolean }>({
    key: "poids_pct",
    asc: false,
  })

  const signalsByTicker = React.useMemo(() => {
    const map = new Map<string, Signal[]>()
    for (const s of signaux) {
      const arr = map.get(s.ticker) ?? []
      arr.push(s)
      map.set(s.ticker, arr)
    }
    return map
  }, [signaux])

  const missingSet = React.useMemo(
    () => new Set(tickersManquants),
    [tickersManquants],
  )

  const sortedLignes = React.useMemo(() => {
    const rows = [...lignes]
    rows.sort((a, b) => cmp(a, b, sort.key, sort.asc))
    return rows
  }, [lignes, sort])

  const onSort = (key: SortKey) => {
    setSort((s) =>
      s.key === key ? { key, asc: !s.asc } : { key, asc: false },
    )
  }

  return (
    <Card className="border border-border/60 bg-card p-0 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between gap-4 border-b border-border/60 px-5 py-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Positions
        </h2>
        <p className="text-xs text-muted-foreground">
          {lignes.length} positions
          {tickersManquants.length > 0
            ? ` · ${tickersManquants.length} missing quote${tickersManquants.length > 1 ? "s" : ""}`
            : ""}
        </p>
      </CardHeader>
      <CardContent className="p-0">
        {lignes.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-muted-foreground">
            No positions in this report.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-b border-border/60 [&>th]:h-9 [&>th]:text-[10px] [&>th]:font-medium [&>th]:uppercase [&>th]:tracking-[0.12em] [&>th]:text-muted-foreground">
                <SortHead onClick={() => onSort("ticker")} sort={sort} k="ticker">
                  Asset
                </SortHead>
                <SortHead onClick={() => onSort("prix")} sort={sort} k="prix" align="right">
                  Price
                </SortHead>
                <SortHead
                  onClick={() => onSort("variation_jour_pct")}
                  sort={sort}
                  k="variation_jour_pct"
                  align="right"
                >
                  24h
                </SortHead>
                <TableHead className="text-right">30d</TableHead>
                <SortHead
                  onClick={() => onSort("poids_pct")}
                  sort={sort}
                  k="poids_pct"
                  align="right"
                >
                  Weight
                </SortHead>
                <SortHead
                  onClick={() => onSort("gain_absolu")}
                  sort={sort}
                  k="gain_absolu"
                  align="right"
                >
                  PnL
                </SortHead>
                <SortHead
                  onClick={() => onSort("gain_pct")}
                  sort={sort}
                  k="gain_pct"
                  align="right"
                >
                  PnL %
                </SortHead>
                <SortHead
                  onClick={() => onSort("rsi_14")}
                  sort={sort}
                  k="rsi_14"
                  align="right"
                >
                  RSI
                </SortHead>
                <TableHead className="text-center">Trend</TableHead>
                <SortHead
                  onClick={() => onSort("volatilite_20j_pct")}
                  sort={sort}
                  k="volatilite_20j_pct"
                  align="right"
                >
                  Vol
                </SortHead>
                <TableHead className="text-center">Signals</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedLignes.map((ligne) => (
                <PositionRow
                  key={`${ligne.position.ticker}-${ligne.position.ouverte_le ?? "na"}`}
                  ligne={ligne}
                  signals={signalsByTicker.get(ligne.position.ticker) ?? []}
                  isMissing={missingSet.has(ligne.position.ticker)}
                />
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}

interface PositionRowProps {
  ligne: LignePortefeuille
  signals: Signal[]
  isMissing: boolean
}

function PositionRow({ ligne, signals, isMissing }: PositionRowProps) {
  const { position, cotation } = ligne
  const sparkData = React.useMemo(() => {
    if (!cotation) return []
    return cotation.clotures.slice(-30).map((v, i) => ({ i, v }))
  }, [cotation])

  const change24h =
    cotation?.clotures && cotation.clotures.length >= 2
      ? ((cotation.prix - cotation.clotures[cotation.clotures.length - 2]) /
          cotation.clotures[cotation.clotures.length - 2]) *
        100
      : null

  const change30d =
    cotation?.clotures && cotation.clotures.length >= 30
      ? ((cotation.prix - cotation.clotures[cotation.clotures.length - 30]) /
          cotation.clotures[cotation.clotures.length - 30]) *
        100
      : null

  const sparkTrend = change30d ?? change24h ?? 0
  const sparkColor =
    sparkTrend >= 0 ? "var(--pnl-positive)" : "var(--pnl-negative)"

  const smaGlyph = renderSmaGlyph(cotation?.prix ?? null, ligne.sma_20)

  return (
    <TableRow className="group border-b border-border/40 transition-colors hover:bg-white/[0.02]">
      <TableCell className="py-4">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "h-8 w-1 shrink-0 rounded-full",
              ligne.gain_pct > 0 && "bg-primary",
              ligne.gain_pct < 0 && "bg-destructive",
              ligne.gain_pct === 0 && "bg-border",
            )}
            aria-hidden
          />
          <div className="flex flex-col leading-tight">
            <span className="flex items-center gap-2">
              <span className="font-mono text-sm font-semibold tracking-tight">
                {position.ticker}
              </span>
              {position.est_long ? null : (
                <Badge
                  variant="outline"
                  className="border-destructive/40 px-1 py-0 font-mono text-[9px] uppercase text-destructive"
                >
                  Short
                </Badge>
              )}
              {isMissing ? (
                <Badge variant="outline" className="border-dashed px-1 py-0 text-[9px]">
                  no quote
                </Badge>
              ) : null}
            </span>
            <span className="text-[11px] text-muted-foreground">
              {position.libelle ?? position.ticker}
              <span className="mx-1 opacity-40">·</span>
              {formatNumber(position.quantite, position.quantite % 1 === 0 ? 0 : 2)}{" "}
              @ {formatCurrency(position.prix_entree)}
            </span>
          </div>
        </div>
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums">
        {cotation ? formatCurrency(cotation.prix) : "—"}
      </TableCell>
      <TableCell className="text-right">
        <PnlPill value={change24h} format="pct" />
      </TableCell>
      <TableCell className="text-right">
        <PnlPill value={change30d} format="pct" />
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums text-muted-foreground">
        {formatPercent(ligne.poids_pct)}
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-mono text-sm tabular-nums",
          pnlColorClass(ligne.gain_absolu),
        )}
      >
        {formatCurrency(ligne.gain_absolu, { showSign: true })}
      </TableCell>
      <TableCell className="text-right">
        <PnlPill value={ligne.gain_pct} format="pct" />
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums text-muted-foreground">
        {formatNumber(ligne.rsi_14, 0)}
      </TableCell>
      <TableCell className="w-[110px] px-2">
        {sparkData.length > 1 ? (
          <div className="mx-auto h-8 w-[96px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sparkData}>
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke={sparkColor}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex items-center justify-center text-muted-foreground">
            {smaGlyph}
          </div>
        )}
      </TableCell>
      <TableCell className="text-right font-mono text-sm tabular-nums text-muted-foreground">
        {formatPercent(ligne.volatilite_20j_pct)}
      </TableCell>
      <TableCell className="text-center">
        {signals.length > 0 ? (
          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5"
                >
                  <span
                    className={cn(
                      "h-2 w-2 rounded-full",
                      signals.some((s) => s.niveau === "alerte")
                        ? "bg-destructive"
                        : signals.some((s) => s.niveau === "attention")
                          ? "bg-[var(--chart-3)]"
                          : "bg-primary/60",
                    )}
                    aria-hidden
                  />
                  <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
                    {signals.length}
                  </span>
                </button>
              }
            />
            <TooltipContent>
              <ul className="space-y-1">
                {signals.map((s, i) => (
                  <li key={i} className="text-xs">
                    <span className="font-mono uppercase">{s.niveau}</span>
                    <span className="mx-1">·</span>
                    {s.message}
                  </li>
                ))}
              </ul>
            </TooltipContent>
          </Tooltip>
        ) : (
          <span className="text-muted-foreground/40">—</span>
        )}
      </TableCell>
    </TableRow>
  )
}

function renderSmaGlyph(
  price: number | null,
  sma20: number | null,
): React.ReactNode {
  if (price == null || sma20 == null) return null
  const above = price >= sma20
  return above ? (
    <ArrowUpIcon
      className="inline size-3.5 text-[var(--pnl-positive)]"
      aria-label="Above SMA 20"
    />
  ) : (
    <ArrowDownIcon
      className="inline size-3.5 text-[var(--pnl-negative)]"
      aria-label="Below SMA 20"
    />
  )
}

interface SortHeadProps {
  onClick: () => void
  sort: { key: SortKey; asc: boolean }
  k: SortKey
  align?: "left" | "right"
  children: React.ReactNode
}

function SortHead({ onClick, sort, k, align = "left", children }: SortHeadProps) {
  const isActive = sort.key === k
  return (
    <TableHead
      className={cn(
        "cursor-pointer select-none",
        align === "right" ? "text-right" : "text-left",
      )}
      onClick={onClick}
    >
      <span
        className={cn(
          "inline-flex items-center gap-1",
          align === "right" && "flex-row-reverse",
        )}
      >
        {children}
        {isActive ? (
          sort.asc ? (
            <ChevronUpIcon className="size-3 text-foreground/80" />
          ) : (
            <ChevronDownIcon className="size-3 text-foreground/80" />
          )
        ) : null}
      </span>
    </TableHead>
  )
}

function cmp(
  a: LignePortefeuille,
  b: LignePortefeuille,
  key: SortKey,
  asc: boolean,
): number {
  const dir = asc ? 1 : -1
  const av = extractSort(a, key)
  const bv = extractSort(b, key)
  if (av === null && bv === null) return 0
  if (av === null) return 1
  if (bv === null) return -1
  if (typeof av === "string" && typeof bv === "string") {
    return av.localeCompare(bv) * dir
  }
  return ((av as number) - (bv as number)) * dir
}

function extractSort(l: LignePortefeuille, key: SortKey): number | string | null {
  switch (key) {
    case "ticker":
      return l.position.ticker
    case "poids_pct":
      return l.poids_pct
    case "prix":
      return l.cotation?.prix ?? null
    case "variation_jour_pct": {
      const c = l.cotation
      if (!c || c.clotures.length < 2) return null
      const prev = c.clotures[c.clotures.length - 2]
      return prev > 0 ? ((c.prix - prev) / prev) * 100 : null
    }
    case "gain_absolu":
      return l.gain_absolu
    case "gain_pct":
      return l.gain_pct
    case "rsi_14":
      return l.rsi_14
    case "volatilite_20j_pct":
      return l.volatilite_20j_pct
    case "score":
      return l.score_valorisation?.score ?? null
  }
}

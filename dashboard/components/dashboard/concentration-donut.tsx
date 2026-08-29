"use client"

import * as React from "react"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { LignePortefeuille, Metriques } from "@/lib/types"
import { formatPercent } from "@/lib/format"

interface ConcentrationDonutProps {
  lignes: LignePortefeuille[]
  metriques: Metriques | null
}

// Palette dérivée du terracotta (chart-1) + un gris chaud pour "Others".
const SLICE_COLORS = [
  "var(--chart-1)",
  "color-mix(in oklch, var(--chart-1), var(--background) 15%)",
  "color-mix(in oklch, var(--chart-1), var(--background) 30%)",
  "color-mix(in oklch, var(--chart-1), var(--background) 45%)",
  "color-mix(in oklch, var(--chart-1), var(--background) 60%)",
]
const OTHERS_COLOR = "var(--muted-foreground)"

export default function ConcentrationDonut({
  lignes,
  metriques,
}: ConcentrationDonutProps) {
  const slices = React.useMemo(() => {
    const sorted = [...lignes]
      .filter((l) => l.poids_pct > 0)
      .sort((a, b) => b.poids_pct - a.poids_pct)
    const top = sorted.slice(0, 5)
    const rest = sorted.slice(5)
    const restWeight = rest.reduce((acc, l) => acc + l.poids_pct, 0)
    const data = top.map((l, idx) => ({
      name: l.position.ticker,
      value: l.poids_pct,
      color: SLICE_COLORS[idx] ?? OTHERS_COLOR,
    }))
    if (restWeight > 0) {
      data.push({ name: "Others", value: restWeight, color: OTHERS_COLOR })
    }
    return data
  }, [lignes])

  const isEmpty = slices.length === 0

  return (
    <Card className="h-full border border-border/60 shadow-none">
      <CardHeader className="border-b border-border/60 px-5 py-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Concentration
        </h2>
        <p className="mt-1 text-xs text-muted-foreground/70">Top positions by weight</p>
      </CardHeader>
      <CardContent className="flex h-full flex-col gap-4 p-5">
        {isEmpty ? (
          <p className="text-sm text-muted-foreground">Portfolio is empty.</p>
        ) : (
          <>
            <div className="h-[180px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={slices}
                    dataKey="value"
                    nameKey="name"
                    innerRadius="60%"
                    outerRadius="90%"
                    stroke="var(--card)"
                    strokeWidth={2}
                    paddingAngle={1}
                    isAnimationActive={false}
                  >
                    {slices.map((slice) => (
                      <Cell key={slice.name} fill={slice.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    cursor={false}
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const item = payload[0]
                      return (
                        <div className="rounded-xl bg-popover px-3 py-1.5 text-xs shadow-lg ring-1 ring-foreground/5">
                          <span className="font-mono">{item.name}</span>
                          <span className="mx-1 text-muted-foreground">·</span>
                          <span className="font-mono tabular-nums">
                            {formatPercent(Number(item.value))}
                          </span>
                        </div>
                      )
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="flex flex-col gap-1 text-xs">
              {slices.map((slice) => (
                <li
                  key={slice.name}
                  className="flex items-center gap-2"
                >
                  <span
                    className="size-2 shrink-0 rounded-[2px]"
                    style={{ backgroundColor: slice.color }}
                    aria-hidden
                  />
                  <span className="font-mono">{slice.name}</span>
                  <span className="ml-auto font-mono tabular-nums text-muted-foreground">
                    {formatPercent(slice.value)}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-auto flex items-center justify-between border-t border-border/60 pt-3 text-xs text-muted-foreground">
              <span>
                HHI{" "}
                <span className="font-mono tabular-nums text-foreground">
                  {metriques?.hhi != null ? metriques.hhi.toFixed(0) : "—"}
                </span>
              </span>
              <span>
                Top{" "}
                <span className="font-mono tabular-nums text-foreground">
                  {metriques?.plus_grosse_position_pct != null
                    ? formatPercent(metriques.plus_grosse_position_pct)
                    : "—"}
                </span>
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

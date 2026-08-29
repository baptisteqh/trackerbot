"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Toggle } from "@/components/ui/toggle"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { EquitySeries } from "@/lib/types"
import {
  type EquityWindow,
  buildDailyLabels,
  maxDrawdownPct,
  rebase100,
  sliceWindow,
} from "@/lib/equity"
import { formatCurrency } from "@/lib/format"
import { cn } from "@/lib/utils"

interface EquityChartProps {
  equity: EquitySeries
  updatedAt: string | null
}

const WINDOWS: EquityWindow[] = ["1M", "3M", "6M", "YTD", "MAX"]

export default function EquityChart({ equity, updatedAt }: EquityChartProps) {
  const [window, setWindow] = React.useState<EquityWindow>("3M")
  const [showBenchmark, setShowBenchmark] = React.useState(false)

  const labels = React.useMemo(
    () => buildDailyLabels(equity.values.length),
    [equity.values.length],
  )

  const view = React.useMemo(() => {
    const sliced = sliceWindow(equity.values, labels, window)
    const benchmark = equity.benchmark
      ? sliceWindow(equity.benchmark, labels, window).values
      : null
    const rebasedPortfolio = rebase100(sliced.values)
    const rebasedBenchmark = benchmark ? rebase100(benchmark) : null
    return sliced.values.map((value, idx) => ({
      date: sliced.labels[idx],
      value,
      portfolio: rebasedPortfolio[idx],
      benchmark: rebasedBenchmark?.[idx] ?? null,
    }))
  }, [equity.values, equity.benchmark, labels, window])

  const drawdown = React.useMemo(
    () => maxDrawdownPct(equity.values),
    [equity.values],
  )
  const hasBenchmark = equity.benchmark !== null && equity.benchmark.length > 0
  const isEmpty = view.length === 0

  return (
    <Card className="h-full border border-border/60 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Equity
          </h2>
          <p className="mt-1 text-xs text-muted-foreground/70">
            Rebased to 100
            {updatedAt ? ` · Updated just now` : null}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {hasBenchmark ? (
            <Toggle
              size="sm"
              variant="outline"
              pressed={showBenchmark}
              onPressedChange={setShowBenchmark}
              aria-label="Show benchmark overlay"
            >
              vs SPY
            </Toggle>
          ) : (
            <Tooltip>
              <TooltipTrigger
                render={
                  <span>
                    <Toggle
                      size="sm"
                      variant="outline"
                      pressed={false}
                      disabled
                      aria-label="Benchmark unavailable"
                    >
                      vs SPY
                    </Toggle>
                  </span>
                }
              />
              <TooltipContent>Benchmark series not available.</TooltipContent>
            </Tooltip>
          )}
          <Tabs
            value={window}
            onValueChange={(v) => setWindow(v as EquityWindow)}
          >
            <TabsList>
              {WINDOWS.map((w) => (
                <TabsTrigger key={w} value={w} className="px-2 text-xs">
                  {w}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        {isEmpty ? (
          <div className="flex h-[300px] items-center justify-center">
            <p className="text-sm text-muted-foreground">No equity series yet.</p>
          </div>
        ) : (
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={view}
                margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
              >
                <defs>
                  <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="0%"
                      stopColor="var(--primary)"
                      stopOpacity={0.35}
                    />
                    <stop
                      offset="100%"
                      stopColor="var(--primary)"
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="var(--border)"
                  strokeOpacity={0.35}
                  vertical={false}
                />
                <XAxis
                  dataKey="date"
                  tickFormatter={compactDate}
                  tick={{ fontSize: 11 }}
                  minTickGap={40}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v: number) => v.toFixed(0)}
                  tick={{ fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  domain={["dataMin - 2", "dataMax + 2"]}
                  width={40}
                />
                <RTooltip
                  cursor={{ stroke: "var(--border)" }}
                  content={<EquityTooltip />}
                />
                <Area
                  type="monotone"
                  dataKey="portfolio"
                  stroke="var(--primary)"
                  strokeWidth={1.5}
                  fill="url(#equityGradient)"
                  isAnimationActive={!prefersReducedMotion()}
                  animationDuration={400}
                />
                {showBenchmark && hasBenchmark ? (
                  <Line
                    type="monotone"
                    dataKey="benchmark"
                    stroke="var(--chart-3)"
                    strokeWidth={1}
                    strokeDasharray="4 3"
                    dot={false}
                    isAnimationActive={!prefersReducedMotion()}
                  />
                ) : null}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
        <div
          className={cn(
            "mt-3 flex items-center justify-between text-xs text-muted-foreground",
          )}
        >
          <span>
            Max drawdown{" "}
            <span className="font-mono tabular-nums text-foreground">
              {drawdown != null ? `-${drawdown.toFixed(2)}%` : "—"}
            </span>
          </span>
          <span>{view.length} points · window {window}</span>
        </div>
      </CardContent>
    </Card>
  )
}

// SSR-safe reduced-motion check.
function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
}

function compactDate(iso: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

interface TooltipPayloadItem {
  name?: string
  value?: number
  payload?: { value: number; portfolio: number; benchmark: number | null }
}

function EquityTooltip({
  active,
  label,
  payload,
}: {
  active?: boolean
  label?: string
  payload?: TooltipPayloadItem[]
}) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  return (
    <div className="rounded-xl bg-popover px-3 py-2 text-xs shadow-lg ring-1 ring-foreground/5">
      <div className="font-medium">{compactDate(String(label ?? ""))}</div>
      <div className="mt-1 flex items-center gap-3">
        <span className="text-muted-foreground">Value</span>
        <span className="font-mono tabular-nums">
          {formatCurrency(row.value)}
        </span>
      </div>
      {row.benchmark != null ? (
        <div className="flex items-center gap-3">
          <span className="text-muted-foreground">Benchmark</span>
          <span className="font-mono tabular-nums">
            {row.benchmark.toFixed(1)}
          </span>
        </div>
      ) : null}
    </div>
  )
}

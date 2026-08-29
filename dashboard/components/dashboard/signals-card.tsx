"use client"

import * as React from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Signal, SignalLevel } from "@/lib/types"
import { cn } from "@/lib/utils"

interface SignalsCardProps {
  signaux: Signal[]
}

const LEVEL_ORDER: SignalLevel[] = ["alerte", "attention", "info"]

const LEVEL_LABEL: Record<SignalLevel, string> = {
  alerte: "Alert",
  attention: "Attention",
  info: "Info",
}

const LEVEL_CLASS: Record<SignalLevel, string> = {
  alerte: "bg-destructive/10 text-destructive border border-destructive/30",
  attention: "bg-[var(--chart-3)]/10 text-[var(--chart-3)] border border-[var(--chart-3)]/30",
  info: "bg-muted text-muted-foreground border border-border/60",
}

const LEVEL_BAR: Record<SignalLevel, string> = {
  alerte: "bg-destructive",
  attention: "bg-[var(--chart-3)]",
  info: "bg-muted-foreground/40",
}

export default function SignalsCard({ signaux }: SignalsCardProps) {
  const grouped = React.useMemo(() => {
    const map = new Map<SignalLevel, Signal[]>()
    for (const level of LEVEL_ORDER) map.set(level, [])
    for (const signal of signaux) {
      map.get(signal.niveau)?.push(signal)
    }
    return map
  }, [signaux])

  const total = signaux.length

  return (
    <Card className="h-full border border-border/60 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 px-5 py-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Today&apos;s signals
        </h2>
        <span className="text-xs text-muted-foreground">
          {total} {total === 1 ? "signal" : "signals"}
        </span>
      </CardHeader>
      <CardContent className="p-5">
        {total === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing to report today.</p>
        ) : (
          <ScrollArea className="max-h-[280px] pr-2">
            <div className="flex flex-col gap-3">
              {LEVEL_ORDER.map((level) => {
                const items = grouped.get(level) ?? []
                if (items.length === 0) return null
                return (
                  <div key={level} className="flex flex-col gap-2">
                    {items.map((s, i) => (
                      <div
                        key={`${level}-${i}`}
                        className="tb-fade-up flex items-start gap-3 rounded-md border border-border/40 bg-white/[0.015] p-3 transition-colors hover:border-border/70 hover:bg-white/[0.03]"
                        style={{ animationDelay: `${i * 40}ms` }}
                      >
                        <span
                          className={cn("mt-0.5 h-8 w-0.5 shrink-0 rounded", LEVEL_BAR[level])}
                          aria-hidden
                        />
                        <div className="flex-1 leading-snug">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-semibold">
                              {s.ticker}
                            </span>
                            <Badge
                              className={cn(
                                LEVEL_CLASS[level],
                                "px-1.5 py-0 text-[9px] uppercase tracking-wide",
                              )}
                            >
                              {LEVEL_LABEL[level]}
                            </Badge>
                            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                              {s.regle}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-foreground/80">{s.message}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}

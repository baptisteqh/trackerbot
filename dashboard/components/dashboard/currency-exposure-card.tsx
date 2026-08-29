"use client"

import * as React from "react"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { ExpositionDevise } from "@/lib/types"
import { formatPercent } from "@/lib/format"
import { cn } from "@/lib/utils"

// Codes drapeau approximatifs pour la devise (glyph ISO -> flag).
// Rendu sobre en emoji : pas d'asset ni de dep, joli sur dark bg.
const FLAG_PAR_DEVISE: Record<string, string> = {
  USD: "🇺🇸",
  EUR: "🇪🇺",
  GBP: "🇬🇧",
  JPY: "🇯🇵",
  CHF: "🇨🇭",
  CAD: "🇨🇦",
  AUD: "🇦🇺",
  NZD: "🇳🇿",
  SEK: "🇸🇪",
  NOK: "🇳🇴",
  DKK: "🇩🇰",
  HKD: "🇭🇰",
  CNY: "🇨🇳",
  KRW: "🇰🇷",
  TWD: "🇹🇼",
  INR: "🇮🇳",
  SGD: "🇸🇬",
  BRL: "🇧🇷",
  MXN: "🇲🇽",
}

interface CurrencyExposureCardProps {
  expositions: ExpositionDevise[]
}

export default function CurrencyExposureCard({ expositions }: CurrencyExposureCardProps) {
  const total = expositions.length

  return (
    <Card className="h-full border border-border/60 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 px-5 py-4">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Currency exposure
        </h2>
        <span className="text-xs text-muted-foreground">
          {total} {total === 1 ? "currency" : "currencies"}
        </span>
      </CardHeader>
      <CardContent className="p-5">
        {total === 0 ? (
          <p className="text-sm text-muted-foreground">No positions to allocate.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {expositions.map((exp, i) => (
              <li
                key={exp.devise}
                className="tb-fade-up"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className="flex items-center gap-2">
                    <span aria-hidden className="text-base">
                      {FLAG_PAR_DEVISE[exp.devise] ?? "🌐"}
                    </span>
                    <span className="font-mono font-semibold tracking-tight">
                      {exp.devise}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {exp.nb_positions} {exp.nb_positions === 1 ? "pos" : "pos"}
                    </span>
                  </span>
                  <span className="font-mono tabular-nums text-foreground/80">
                    {formatPercent(exp.poids_pct, { fractionDigits: 1 })}
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted/40">
                  <div
                    className={cn(
                      "tb-grow-x h-full rounded-full",
                      barColor(i),
                    )}
                    style={{
                      width: `${Math.max(exp.poids_pct, 1.5)}%`,
                      animationDelay: `${i * 60 + 120}ms`,
                    }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

// Cycle 5 accents pour distinguer visuellement les devises.
// L'ordre est le meme que dans l'array (trie par poids desc).
function barColor(index: number): string {
  const palette = [
    "bg-[var(--chart-1)]",
    "bg-[var(--chart-3)]",
    "bg-[var(--chart-4)]",
    "bg-[var(--chart-2)]",
    "bg-[var(--chart-5)]",
  ]
  return palette[index % palette.length]
}

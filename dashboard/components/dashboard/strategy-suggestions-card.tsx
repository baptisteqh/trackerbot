"use client"

import * as React from "react"
import {
  AlertCircleIcon,
  ChevronDownIcon,
  ShieldCheckIcon,
  ShieldIcon,
  TargetIcon,
  TrendingUpIcon,
  LayersIcon,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type {
  Suggestion,
  SuggestionCategory,
  SuggestionPriority,
} from "@/lib/strategy"
import { cn } from "@/lib/utils"

interface StrategySuggestionsCardProps {
  suggestions: Suggestion[]
}

const CATEGORY_ICON: Record<SuggestionCategory, React.ComponentType<{ className?: string }>> = {
  concentration: LayersIcon,
  diversification: TargetIcon,
  risk: AlertCircleIcon,
  protection: ShieldIcon,
  profit: TrendingUpIcon,
}

const CATEGORY_LABEL: Record<SuggestionCategory, string> = {
  concentration: "Concentration",
  diversification: "Diversification",
  risk: "Risk",
  protection: "Protection",
  profit: "Profit taking",
}

const PRIORITY_STYLE: Record<SuggestionPriority, { badge: string; bar: string }> = {
  high: {
    badge: "bg-destructive/10 text-destructive border border-destructive/30",
    bar: "bg-destructive",
  },
  medium: {
    badge: "bg-[var(--chart-3)]/10 text-[var(--chart-3)] border border-[var(--chart-3)]/30",
    bar: "bg-[var(--chart-3)]",
  },
  low: {
    badge: "bg-muted text-muted-foreground border border-border/60",
    bar: "bg-muted-foreground/40",
  },
}

const PRIORITY_LABEL: Record<SuggestionPriority, string> = {
  high: "Priority",
  medium: "Consider",
  low: "Nice to have",
}

export default function StrategySuggestionsCard({
  suggestions,
}: StrategySuggestionsCardProps) {
  const total = suggestions.length
  const highCount = suggestions.filter((s) => s.priority === "high").length

  return (
    <Card className="h-full border border-border/60 shadow-none">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 px-5 py-4">
        <div className="flex items-center gap-3">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Rebalancing strategy
          </h2>
          {highCount > 0 ? (
            <Badge className="border border-destructive/30 bg-destructive/10 px-1.5 py-0 font-mono text-[9px] uppercase tracking-wide text-destructive">
              {highCount} priority
            </Badge>
          ) : null}
        </div>
        <span className="text-xs text-muted-foreground">
          {total === 0 ? "All clear" : `${total} suggestion${total === 1 ? "" : "s"}`}
        </span>
      </CardHeader>
      <CardContent className="p-5">
        {total === 0 ? (
          <div className="flex items-center gap-3 rounded-md border border-border/40 bg-white/[0.015] p-4">
            <ShieldCheckIcon className="size-5 text-[var(--pnl-positive)]" />
            <div>
              <p className="text-sm font-medium">Portfolio looks balanced.</p>
              <p className="text-xs text-muted-foreground">
                No concentration, protection, or diversification flags at the moment.
              </p>
            </div>
          </div>
        ) : (
          <ul className="flex flex-col gap-3">
            {suggestions.map((s, i) => (
              <SuggestionItem key={s.id} suggestion={s} index={i} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

function SuggestionItem({
  suggestion,
  index,
}: {
  suggestion: Suggestion
  index: number
}) {
  const [open, setOpen] = React.useState(false)
  const Icon = CATEGORY_ICON[suggestion.category]
  const priorityStyle = PRIORITY_STYLE[suggestion.priority]

  return (
    <li
      className="tb-fade-up overflow-hidden rounded-md border border-border/40 bg-white/[0.015] transition-colors hover:border-border/70"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.02]"
        aria-expanded={open}
      >
        <span
          className={cn("mt-0.5 h-9 w-0.5 shrink-0 rounded", priorityStyle.bar)}
          aria-hidden
        />
        <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
        <div className="flex-1 leading-snug">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">{suggestion.title}</span>
            <Badge
              className={cn(
                priorityStyle.badge,
                "px-1.5 py-0 text-[9px] uppercase tracking-wide",
              )}
            >
              {PRIORITY_LABEL[suggestion.priority]}
            </Badge>
            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
              {CATEGORY_LABEL[suggestion.category]}
            </span>
          </div>
          {suggestion.tickers && suggestion.tickers.length > 0 ? (
            <div className="mt-1 flex flex-wrap gap-1">
              {suggestion.tickers.map((t) => (
                <span
                  key={t}
                  className="font-mono text-[10px] tracking-tight text-muted-foreground"
                >
                  {t}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <ChevronDownIcon
          className={cn(
            "mt-1 size-4 shrink-0 text-muted-foreground transition-transform duration-200",
            open && "rotate-180",
          )}
          aria-hidden
        />
      </button>
      <div
        className={cn(
          "grid transition-[grid-template-rows] duration-300 ease-out",
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="overflow-hidden">
          <div className="border-t border-border/40 px-4 py-3 pl-11 text-xs leading-relaxed text-foreground/80">
            <p>
              <span className="mr-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                Why
              </span>
              {suggestion.rationale}
            </p>
            <p className="mt-2 rounded-md border border-primary/30 bg-primary/[0.05] px-3 py-2 text-primary">
              <span className="mr-1 text-[10px] uppercase tracking-wide opacity-80">
                Action
              </span>
              {suggestion.action}
            </p>
          </div>
        </div>
      </div>
    </li>
  )
}

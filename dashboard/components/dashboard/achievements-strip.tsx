"use client"

import { CheckIcon, LockIcon } from "lucide-react"

import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { Badge } from "@/lib/types"
import { cn } from "@/lib/utils"

interface AchievementsStripProps {
  badges: Badge[]
}

// Strip horizontale scrollable — pattern gamifie type Duolingo / Strava.
// Unlocked = fond fluo, contour fluo. Locked = fond neutre, texte muted.
// Tooltip au survol pour la description complete.

export default function AchievementsStrip({ badges }: AchievementsStripProps) {
  if (badges.length === 0) return null

  const unlocked = badges.filter((b) => b.unlocked).length

  return (
    <section className="rounded-md border border-border/60 bg-card">
      <div className="flex items-center justify-between border-b border-border/60 px-4 py-2.5">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Achievements
        </h2>
        <span className="font-mono text-xs tabular-nums text-muted-foreground">
          <span className="text-primary">{unlocked}</span>
          <span className="mx-1 opacity-40">/</span>
          <span>{badges.length}</span>
        </span>
      </div>
      <ScrollArea>
        <div className="flex gap-2 p-3">
          {badges.map((badge) => (
            <BadgeChip key={badge.id} badge={badge} />
          ))}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </section>
  )
}

function BadgeChip({ badge }: { badge: Badge }) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <button
            type="button"
            className={cn(
              "group flex shrink-0 items-center gap-2 rounded border px-3 py-2 text-left transition-colors",
              badge.unlocked
                ? "border-primary/40 bg-primary/[0.08] hover:bg-primary/[0.12]"
                : "border-border/50 bg-secondary/40 hover:bg-secondary/60",
            )}
          >
            <span
              className={cn(
                "flex h-6 w-6 shrink-0 items-center justify-center rounded-sm",
                badge.unlocked
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground/70",
              )}
              aria-hidden
            >
              {badge.unlocked ? (
                <CheckIcon className="size-3.5" strokeWidth={2.5} />
              ) : (
                <LockIcon className="size-3" strokeWidth={2.5} />
              )}
            </span>
            <span className="flex flex-col leading-tight">
              <span
                className={cn(
                  "text-[11px] font-semibold",
                  badge.unlocked ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {badge.label}
              </span>
              {badge.detail ? (
                <span
                  className={cn(
                    "font-mono text-[10px] tabular-nums",
                    badge.unlocked ? "text-primary" : "text-muted-foreground/70",
                  )}
                >
                  {badge.detail}
                </span>
              ) : null}
            </span>
          </button>
        }
      />
      <TooltipContent>
        <p className="max-w-[220px] text-xs">{badge.description}</p>
      </TooltipContent>
    </Tooltip>
  )
}

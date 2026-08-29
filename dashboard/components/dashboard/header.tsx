"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import {
  MoonIcon,
  MoreHorizontalIcon,
  RefreshCwIcon,
  SunIcon,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { formatDateLong } from "@/lib/format"

interface DashboardHeaderProps {
  generatedAt: string | null
  benchmark: string | null
  isRefreshing: boolean
  isRegeneratingVeille: boolean
  isRefreshingFundamentals: boolean
  onRefreshQuotes: () => void
  onRegenerateVeille: () => void
  onRefreshFundamentals: () => void
  reportSourceUrl: string
}

export default function DashboardHeader({
  generatedAt,
  benchmark,
  isRefreshing,
  isRegeneratingVeille,
  isRefreshingFundamentals,
  onRefreshQuotes,
  onRegenerateVeille,
  onRefreshFundamentals,
  reportSourceUrl,
}: DashboardHeaderProps) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <span
          className="inline-block h-2 w-2 rounded-full bg-primary shadow-[0_0_8px_var(--primary)]"
          aria-hidden
        />
        <div className="flex flex-col leading-tight">
          <span className="font-mono text-sm font-semibold tracking-tight">
            trackerbot
          </span>
          <span className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            {generatedAt
              ? `Snapshot · ${formatDateLong(generatedAt)}`
              : "Awaiting first report"}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {benchmark ? (
          <Badge
            variant="outline"
            className="border-border/60 bg-card font-mono text-[10px] uppercase tracking-wide text-muted-foreground"
          >
            vs {benchmark}
          </Badge>
        ) : null}
        <Button
          onClick={onRefreshQuotes}
          disabled={isRefreshing}
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 border-border/60 bg-card font-mono text-xs"
        >
          <RefreshCwIcon
            className={isRefreshing ? "animate-spin" : undefined}
          />
          Refresh
          <kbd className="ml-1 hidden rounded bg-secondary px-1 text-[9px] tracking-widest text-muted-foreground sm:inline">
            R
          </kbd>
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button variant="ghost" size="icon-sm" aria-label="More actions">
                <MoreHorizontalIcon />
              </Button>
            }
          />
          <DropdownMenuContent align="end" sideOffset={6}>
            <DropdownMenuItem
              onClick={onRegenerateVeille}
              disabled={isRegeneratingVeille}
            >
              Regenerate market watch
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={onRefreshFundamentals}
              disabled={isRefreshingFundamentals}
            >
              Refresh fundamentals
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              render={
                <a
                  href={reportSourceUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                >
                  View report source
                </a>
              }
            />
          </DropdownMenuContent>
        </DropdownMenu>
        <DarkToggle />
      </div>
    </header>
  )
}

function DarkToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)
  // Garde-fou anti-hydration : le theme n'est resolu que cote client.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  React.useEffect(() => setMounted(true), [])

  const isDark = resolvedTheme === "dark"
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {mounted && isDark ? <SunIcon /> : <MoonIcon />}
    </Button>
  )
}

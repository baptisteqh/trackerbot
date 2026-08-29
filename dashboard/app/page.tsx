"use client"

import * as React from "react"
import { toast } from "sonner"

import DashboardHeader from "@/components/dashboard/header"
import MetricTiles from "@/components/dashboard/metric-tiles"
import EquityChart from "@/components/dashboard/equity-chart"
import ConcentrationDonut from "@/components/dashboard/concentration-donut"
import PositionsTable from "@/components/dashboard/positions-table"
import SignalsCard from "@/components/dashboard/signals-card"
import ValuationCard from "@/components/dashboard/valuation-card"
import MarketWatchCard from "@/components/dashboard/market-watch-card"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  TrackerbotApiError,
  fetchRapport,
  refreshRapport,
} from "@/lib/api"
import { DEMO_RAPPORT } from "@/lib/demo-rapport"
import type { Rapport, RefreshScope } from "@/lib/types"

const API_BASE =
  process.env.NEXT_PUBLIC_TRACKERBOT_API ?? "http://127.0.0.1:8000"

type LoadState =
  | { kind: "loading" }
  | { kind: "empty"; message: string }
  | { kind: "error"; message: string }
  | { kind: "ready"; rapport: Rapport; isDemo?: boolean }

export default function OverviewPage() {
  const [state, setState] = React.useState<LoadState>({ kind: "loading" })
  const [busy, setBusy] = React.useState<RefreshScope | null>(null)
  const [newAlertsBanner, setNewAlertsBanner] = React.useState<number | null>(
    null,
  )

  const load = React.useCallback(async () => {
    setState({ kind: "loading" })
    try {
      const rapport = await fetchRapport()
      setState({ kind: "ready", rapport })
    } catch (error) {
      // API 503 = cache vide mais l'API repond -> on garde l'empty state
      // dedie (l'utilisateur peut cliquer Refresh, la CSRF marchera).
      if (error instanceof TrackerbotApiError && error.status === 503) {
        setState({ kind: "empty", message: "No report cached yet." })
        return
      }
      // Toute autre erreur (Failed to fetch, network, CORS) = API pas lancee.
      // On sert un payload demo pour que l'utilisateur voie l'UI sans avoir
      // a demarrer le backend Python. Le banner precise que c'est demo.
      setState({ kind: "ready", rapport: DEMO_RAPPORT, isDemo: true })
    }
  }, [])

  React.useEffect(() => {
    // Fetch initial : load() met a jour l'etat, c'est le point de synchronisation
    // avec le systeme externe (l'API). Le lint set-state-in-effect ne s'applique
    // pas ici — c'est exactement le cas d'usage documente.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load()
  }, [load])

  const runRefresh = React.useCallback(
    async (scope: RefreshScope, messages: { pending: string; success: string }) => {
      setBusy(scope)
      const previous = state.kind === "ready" ? state.rapport : null
      const previousAlerts = previous
        ? previous.signaux.filter((s) => s.niveau === "alerte").length
        : 0
      const toastId = toast.loading(messages.pending)
      try {
        const rapport = await refreshRapport(scope)
        setState({ kind: "ready", rapport })
        toast.success(messages.success, { id: toastId })
        const nextAlerts = rapport.signaux.filter(
          (s) => s.niveau === "alerte",
        ).length
        if (previous && nextAlerts > previousAlerts) {
          setNewAlertsBanner(nextAlerts - previousAlerts)
        }
      } catch (error) {
        toast.error(
          error instanceof Error ? error.message : "Refresh failed",
          { id: toastId },
        )
      } finally {
        setBusy(null)
      }
    },
    [state],
  )

  const onRefreshQuotes = React.useCallback(() => {
    void runRefresh("quotes", {
      pending: "Refreshing quotes…",
      success: "Quotes refreshed.",
    })
  }, [runRefresh])

  const onRegenerateVeille = React.useCallback(() => {
    void runRefresh("veille", {
      pending: "Regenerating market watch…",
      success: "Market watch updated.",
    })
  }, [runRefresh])

  const onRefreshFundamentals = React.useCallback(() => {
    void runRefresh("fundamentals", {
      pending: "Refreshing fundamentals…",
      success: "Fundamentals refreshed.",
    })
  }, [runRefresh])

  // Raccourci clavier "r" pour rafraîchir les cotations.
  React.useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.repeat) return
      if (event.metaKey || event.ctrlKey || event.altKey) return
      if (event.key.toLowerCase() !== "r") return
      if (isTypingTarget(event.target)) return
      event.preventDefault()
      onRefreshQuotes()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [onRefreshQuotes])

  const rapport = state.kind === "ready" ? state.rapport : null
  const totals = React.useMemo(() => derivePortfolioTotals(rapport), [rapport])

  return (
    <div className="min-h-svh bg-background">
      <div className="mx-auto max-w-[1240px] px-6 py-8">
        <DashboardHeader
          generatedAt={rapport?.genere_le ?? null}
          benchmark={rapport?.metriques?.benchmark ?? null}
          isRefreshing={busy === "quotes"}
          isRegeneratingVeille={busy === "veille"}
          isRefreshingFundamentals={busy === "fundamentals"}
          onRefreshQuotes={onRefreshQuotes}
          onRegenerateVeille={onRegenerateVeille}
          onRefreshFundamentals={onRefreshFundamentals}
          reportSourceUrl={`${API_BASE}/rapport`}
        />

        {state.kind === "ready" && state.isDemo ? (
          <div className="mt-6 flex w-full items-center justify-between rounded-md border border-amber-500/30 bg-amber-500/[0.06] px-4 py-2.5 text-sm">
            <span className="flex items-center gap-2 text-amber-300/90">
              <span className="inline-block h-2 w-2 rounded-full bg-amber-400" />
              Demo data — start the API to see your real portfolio.
            </span>
            <code className="rounded bg-black/40 px-2 py-1 font-mono text-xs text-amber-200/90">
              trackerbot serve
            </code>
          </div>
        ) : null}

        {newAlertsBanner ? (
          <button
            type="button"
            onClick={() => setNewAlertsBanner(null)}
            className="mt-6 flex w-full items-center justify-between rounded-md border border-primary/30 bg-primary/10 px-4 py-2 text-left text-sm text-primary transition hover:bg-primary/15"
          >
            <span>
              {newAlertsBanner} new{" "}
              {newAlertsBanner === 1 ? "alert" : "alerts"} · scroll to Today&apos;s
              signals
            </span>
            <span className="text-xs opacity-70">dismiss</span>
          </button>
        ) : null}

        <main className="mt-8 space-y-8">
          {state.kind === "loading" ? (
            <LoadingLayout />
          ) : state.kind === "empty" ? (
            <EmptyReport
              message={state.message}
              onRefresh={onRefreshQuotes}
              busy={busy === "quotes"}
            />
          ) : state.kind === "error" ? (
            <ErrorReport message={state.message} onRetry={load} />
          ) : (
            <>
              <MetricTiles
                currentValue={totals.currentValue}
                totalPnlAbs={totals.pnlAbs}
                totalPnlPct={totals.pnlPct}
                deltas={state.rapport.deltas}
                metriques={state.rapport.metriques}
              />

              <section className="grid grid-cols-1 gap-6 lg:grid-cols-12">
                <div className="lg:col-span-8">
                  <EquityChart
                    equity={state.rapport.equity_series}
                    updatedAt={state.rapport.genere_le}
                  />
                </div>
                <div className="lg:col-span-4">
                  <ConcentrationDonut
                    lignes={state.rapport.lignes}
                    metriques={state.rapport.metriques}
                  />
                </div>
              </section>

              <PositionsTable
                lignes={state.rapport.lignes}
                signaux={state.rapport.signaux}
                tickersManquants={state.rapport.tickers_manquants}
              />

              <section className="grid grid-cols-1 gap-6 lg:grid-cols-12">
                <div className="lg:col-span-4">
                  <SignalsCard signaux={state.rapport.signaux} />
                </div>
                <div className="lg:col-span-4">
                  <ValuationCard lignes={state.rapport.lignes} />
                </div>
                <div className="lg:col-span-4">
                  <MarketWatchCard veille={state.rapport.veille} />
                </div>
              </section>

              <footer className="pt-6 text-center text-xs text-muted-foreground">
                Report generated {new Date(state.rapport.genere_le).toLocaleString("en-US")}
                {" · "}
                {state.rapport.lignes.length} positions
                {" · "}
                {state.rapport.signaux.length} signals
              </footer>
            </>
          )}
        </main>
      </div>
    </div>
  )
}

function derivePortfolioTotals(rapport: Rapport | null): {
  currentValue: number
  pnlAbs: number
  pnlPct: number
} {
  if (!rapport) return { currentValue: 0, pnlAbs: 0, pnlPct: 0 }
  let value = 0
  let invested = 0
  for (const l of rapport.lignes) {
    value += l.valeur_courante
    invested += l.montant_investi
  }
  const pnl = value - invested
  const pct = invested !== 0 ? (pnl / invested) * 100 : 0
  return { currentValue: value, pnlAbs: pnl, pnlPct: pct }
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return (
    target.isContentEditable ||
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.tagName === "SELECT"
  )
}

function LoadingLayout() {
  return (
    <>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[160px]" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Skeleton className="h-[360px] lg:col-span-8" />
        <Skeleton className="h-[360px] lg:col-span-4" />
      </div>
      <Skeleton className="h-[280px]" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Skeleton className="h-[220px] lg:col-span-4" />
        <Skeleton className="h-[220px] lg:col-span-4" />
        <Skeleton className="h-[220px] lg:col-span-4" />
      </div>
    </>
  )
}

function EmptyReport({
  message,
  onRefresh,
  busy,
}: {
  message: string
  onRefresh: () => void
  busy: boolean
}) {
  return (
    <Card className="border border-border/60 bg-card shadow-none">
      <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
        <p className="text-lg font-semibold">{message}</p>
        <p className="max-w-md text-sm text-muted-foreground">
          Run a quotes refresh to pull the latest state from your broker and
          generate the first report.
        </p>
        <Button onClick={onRefresh} disabled={busy}>
          Refresh now
        </Button>
      </CardContent>
    </Card>
  )
}

function ErrorReport({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) {
  return (
    <Card className="border border-destructive/40 bg-card shadow-none">
      <CardContent className="flex flex-col items-start gap-3 py-8">
        <p className="text-lg font-semibold text-destructive">
          Couldn&apos;t reach the report.
        </p>
        <p className="text-sm text-muted-foreground">{message}</p>
        <p className="text-xs text-muted-foreground">
          Check that the API is running on {API_BASE}.
        </p>
        <Button variant="outline" onClick={onRetry}>
          Retry
        </Button>
      </CardContent>
    </Card>
  )
}

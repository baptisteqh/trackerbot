"use client"

import { ArrowUpRightIcon } from "lucide-react"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import type { Veille } from "@/lib/types"

interface MarketWatchCardProps {
  veille: Veille | null
}

export default function MarketWatchCard({ veille }: MarketWatchCardProps) {
  return (
    <Card className="h-full border border-border/60 shadow-none">
      <CardHeader className="border-b border-border/60 px-5 py-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Market watch
          </h2>
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
            Perplexity
          </span>
        </div>
      </CardHeader>
      <CardContent className="flex h-full flex-col gap-4 p-5">
        {!veille || !veille.texte.trim() ? (
          <p className="text-sm text-muted-foreground">
            Market watch hasn&apos;t been generated yet.
          </p>
        ) : (
          <>
            <p className="text-[13px] leading-relaxed text-foreground/85">
              {veille.texte}
            </p>
            {veille.sources.length > 0 ? (
              <ul className="mt-auto flex flex-col gap-1 border-t border-border/60 pt-3 text-xs">
                {veille.sources.map((src) => (
                  <li key={src}>
                    <a
                      href={src}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="inline-flex items-center gap-1 text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                    >
                      <span className="max-w-[280px] truncate">
                        {shortenSource(src)}
                      </span>
                      <ArrowUpRightIcon className="size-3 shrink-0" />
                    </a>
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  )
}

function shortenSource(url: string): string {
  try {
    const u = new URL(url)
    return `${u.hostname.replace(/^www\./, "")}${u.pathname === "/" ? "" : u.pathname}`
  } catch {
    return url
  }
}

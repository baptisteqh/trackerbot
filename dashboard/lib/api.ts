// Client HTTP pour l'API Python locale.
// Le contrat sécurité : GET /rapport lit le cache, POST /refresh exige
// Origin + cookie CSRF + header X-XSRF-Token. On récupère le token via
// GET /csrf au premier besoin, puis on le renvoie sur chaque POST.

import type { Rapport, RefreshScope } from "./types"

const API_BASE =
  process.env.NEXT_PUBLIC_TRACKERBOT_API ?? "http://127.0.0.1:8000"

const COOKIE_CSRF = "xsrf-token"
const HEADER_CSRF = "X-XSRF-Token"

export class TrackerbotApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = "TrackerbotApiError"
  }
}

export async function fetchRapport(): Promise<Rapport> {
  const response = await fetch(`${API_BASE}/rapport`, {
    credentials: "include",
    cache: "no-store",
  })
  if (!response.ok) {
    throw new TrackerbotApiError(
      response.status,
      response.status === 503
        ? "No report cached yet. Run `trackerbot status` or Refresh."
        : `GET /rapport failed (${response.status})`,
    )
  }
  return (await response.json()) as Rapport
}

export async function refreshRapport(scope: RefreshScope): Promise<Rapport> {
  const token = await ensureCsrfToken()
  const response = await fetch(`${API_BASE}/refresh`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      [HEADER_CSRF]: token,
    },
    body: JSON.stringify({ scope }),
  })
  if (!response.ok) {
    const detail = await safeReadDetail(response)
    throw new TrackerbotApiError(
      response.status,
      detail ?? `POST /refresh failed (${response.status})`,
    )
  }
  return (await response.json()) as Rapport
}

async function ensureCsrfToken(): Promise<string> {
  const existing = readCookie(COOKIE_CSRF)
  if (existing) return existing
  const response = await fetch(`${API_BASE}/csrf`, {
    credentials: "include",
  })
  if (!response.ok) {
    throw new TrackerbotApiError(response.status, "Could not obtain CSRF token")
  }
  const { token } = (await response.json()) as { token: string }
  return token
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split("=")[1]) : null
}

async function safeReadDetail(response: Response): Promise<string | null> {
  try {
    const data = (await response.json()) as { detail?: string }
    return typeof data.detail === "string" ? data.detail : null
  } catch {
    return null
  }
}

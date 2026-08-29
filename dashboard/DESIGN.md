# DESIGN.md — Tableau de bord Trackerbot (v2)

> Brief opinionne pour l'agent qui construit le dashboard.
> Cible : Next.js 16 + React 19 + Tailwind v4 + shadcn (style `base-rhea`), rendu par `/rapport` (FastAPI).
> **UI copy en anglais.** Le brief lui-meme reste en francais (documentation interne).
> v2 : enrichi avec des references Mobbin et Perplexity (voir §12). Aligne avec l'API `deltas` et le refresh scoped.

---

## 1. North star

Un dashboard trading pro, pas un journal de bord. Fond noir profond, chiffres bold en sans-serif type SF Pro (rendu Inter 600/700 sur le web), accents fluo pour ce qui bouge : vert vif pour le PnL positif et l'equity, rouge vif pour le PnL negatif, ambre pour les warnings. Le reste de l'interface reste sobre : bordures fines, aucune ombre inutile, aucune fantaisie (pas d'italique decoratif, pas de serif, pas de couleur "chaude"). Le PnL et l'equity sautent aux yeux ; le meta (labels, chrome) reste gris muet.

Reference visuelle la plus proche parmi les ecrans reels : [**Yahoo Finance iOS**](https://mobbin.com/screens/f90cf0d1-8f2f-424a-ad75-601345b47751) (fond noir, PnL vert/rouge fluo, chiffres bold Apple-esque, sparklines partout) et [**QuestMobile RRSP**](https://mobbin.com/screens/ed3dd312-6ff8-40aa-8837-b47a59ed801f) (aire d'equity en vert fluo sur noir absolu). Pour la densite web, [**Fey Screener**](https://mobbin.com/screens/920817af-adb1-4853-90ec-acd729c9101b) et [**Kraken Portfolio**](https://mobbin.com/screens/25b67ef9-d56e-4f69-865f-16a702da74b7).

---

## 2. Information architecture

Ordre de priorite (V1 = une seule page ; les sous-pages ne se justifient que quand la page devient illisible) :

1. **Overview** (`/`) — l'unique page V1. Tout ce qui compte tient au-dessus ou juste en dessous du pli.
2. **Positions** (`/positions`) — V1.5 : deportee quand le tableau depasse 20 lignes ou qu'on veut filtrer serieusement.
3. **Signaux** (`/signaux`) — V2 : historique et regles declenchees ; en V1 c'est un panneau lateral.
4. **Veille** (`/veille`) — V2 : archive des veilles Perplexity ; en V1 c'est une carte au bas de l'overview.
5. **Reglages** (`/reglages`) — V2 : source de portefeuille, seuils, benchmark.

Aucune navigation profonde en V1. Une barre superieure minimaliste (logo texte "trackerbot", date de generation, refresh scoped, toggle dark) suffit. Pattern navigation editoriale confirme par Perplexity : `Breadcrumb -> Typography-led headline -> Chart as lead visual -> Tabs for related coverage`.

---

## 3. Page layout — Overview

Grille : `max-w-[1240px] mx-auto px-6 py-8`, 12 colonnes, gap 24.

### Header (h ~ 88px)

- Colonnes 1-6 : titre Fraunces **"Portfolio"** + sous-titre **"Generated Aug 29, 2026 · 14:32"** (`genere_le`).
- Colonnes 7-12 (align right, ordre de gauche a droite) :
  1. `Badge` **"vs SPY"** (benchmark actif, `metriques.benchmark`).
  2. Bouton primaire **`Refresh`** — **rafraichit uniquement les cotations** (rapide, ~2s).
  3. Bouton `⋯` (icon-only, `variant="ghost"`) qui ouvre un `DropdownMenu` avec :
     - **"Regenerate market watch"** (relance Perplexity, ~15s, `Sonner` progress toast).
     - **"Refresh fundamentals"** (relance Yahoo, ~10s).
     - Separator, puis **"View report source"** (lien vers `/rapport` JSON brut).
  4. Toggle dark (icon-only, deja cable sur touche `d`).
- Raccourcis clavier : `r` = Refresh (cotations), `d` = dark toggle.

Reference : ecrans Mobbin **Copilot Money** (`/screens/df0a19e8-...`) et **Origin** (`/screens/3a516cce-...`) — le petit menu roue-crantee dans le coin est le pattern standard pour les actions rares (source display, benchmark, accounts included). On adopte la meme separation "action principale + `⋯` pour les actions couteuses".

### Bandeau de tete — Metric tiles (au-dessus du pli, h ~ 200px)

Grille de 4 `Card` en colonnes 1-12 (chacune sur 3 colonnes) :

| Cellule | Label (uppercase) | Valeur principale | Sous-ligne (deltas) | Champ source |
|--------|-------------------|-------------------|---------------------|--------------|
| 1 | **CURRENT VALUE** | `valeur_courante` (Fraunces 40px) | `+$1,234 · +0.42% (1d)` colore | `valeur_courante`, `deltas.pnl_1d_abs`, `deltas.pnl_1d_pct` |
| 2 | **TOTAL PNL** | `gain_absolu` (mono 32px, signe) | `gain_pct` + segmented `1D / 7D / 30D / ALL` (Tabs) | `gain_absolu`, `gain_pct`, `deltas.pnl_{1d,7d,30d}_{abs,pct}` |
| 3 | **SHARPE** | `metriques.sharpe` (mono 32px) | `Vol ann. XX.X% · Return ann. XX.X%` | `metriques.sharpe`, `metriques.volatilite_annuelle_pct`, `metriques.rendement_annuel_pct` |
| 4 | **MAX DRAWDOWN** | `metriques.max_drawdown_pct` (mono 32px, signe) | `Beta vs SPY: X.XX` | `metriques.max_drawdown_pct`, `metriques.beta`, `metriques.benchmark` |

- Chaque `Card` : bordure `border-border/70`, pas de fond colore. Label Inter uppercase tracking-wide, valeur Fraunces OU mono selon le tableau, micro-legende en `text-muted-foreground text-xs`.
- **Deltas** : si la valeur est `null` (historique < N jours), afficher `—` en `text-muted-foreground` avec tooltip **"Not enough history yet"**. Ne jamais afficher `0` a la place.
- **Segmented control** sur la tuile PnL : bascule entre `1D / 7D / 30D / ALL`. `ALL` = `gain_absolu` / `gain_pct` (life-to-date), les autres = valeurs du bloc `deltas`.
- Couleur des deltas : `text-[--pnl-positive]` (vert sobre) si > 0, `text-[--pnl-negative]` (rouge terracotta) si < 0, sinon `text-muted-foreground`.

Reference pattern : **Whop Analytics** (`/screens/add1901d-...`), **Quicken Investments** (`/screens/f61813eb-...` — "Day $ / Day % / 1 Month $ / 1 Month %" en colonnes), et **Monarch Holdings** (`/screens/c9f450db-...` — "PAST 90 DAYS / TODAY" en sous-ligne). Perplexity a insiste sur `progressive disclosure` et `benchmark + observation window` pour beta — d'ou la sous-ligne explicite "vs SPY".

### Zone principale (h ~ 420px)

- Colonnes 1-8 : **Equity curve** dans une `Card` :
  - `AreaChart` recharts, gradient terracotta -> transparent, ligne pleine 1.5px.
  - Tabs `1M / 3M / 6M / YTD / MAX` en haut a droite. Source = `equity_series` (expose par l'API) ; fallback = reconstruction cote client depuis `lignes[*].cotation.clotures` sur fenetre commune.
  - Overlay **drawdown** en pointille sombre (axe Y secondaire cote droit), toggle via `Toggle` en haut a droite.
  - Overlay **benchmark** (SPY) en `stroke-muted-foreground/60` fin, toggle separe. Pattern **Monarch** (`/screens/c9f450db-...`) : le benchmark reste visuellement subordonne (couleur froide, ligne plus fine).
  - Point terminal souligne d'un dot terracotta + label `Updated just now` en `text-xs italic text-muted-foreground` — cue de fraicheur recommande par Perplexity (voir §7 anim).
- Colonnes 9-12 : **Concentration** dans une `Card` :
  - Donut leger (`innerRadius=60%`), 5 slices terracotta degrade + gris pour "Others".
  - Legende sous forme de liste : ticker + `poids_pct`, tri desc.
  - En pied : `HHI: X.XX` et `Top position: TICKER XX%` (`metriques.hhi`, `metriques.plus_grosse_position_pct`).

### Positions (pleine largeur, h auto)

- `Card` avec `Table` shadcn. Colonnes (dans l'ordre) :
  `Ticker | Side (L/S) | Qty | Entry | Price | 24h Chg (sparkline mini) | Weight % | PnL abs | PnL % | RSI 14 | vs SMA 20/50 | Vol 20d | Valuation | Signals`
- Sparkline mini : `LineChart` 80x24, stroke `--primary`, aucun axe, source = `cotation.clotures[-30:]`.
- Tri par defaut : `poids_pct` desc. Entetes cliquables, chevron discret.
- Hover ligne : `bg-secondary/40`. Click sur ticker ouvre un `Sheet` de detail (V1.5).
- Tickers sans cotation en italique + tag **"missing quote"** (source : `tickers_manquants`).
- Empty cells : `—` en `text-muted-foreground`, jamais `null` ou `0`.

Reference : **Fey Portfolio** (`/screens/f4b1fb8e-...`) et **Uniswap Tokens** (`/screens/e39f0d0f-...`) — sparklines en fin de ligne, prix aligne a droite, badges de variation en pilule. Densite acceptable pour ~30 lignes sans scroll.

### Trois cartes en pied (colonnes 1-4 / 5-8 / 9-12)

- **Today's signals** : liste groupee par niveau (`alerte` puis `attention` puis `info`), badge couleur par niveau, message + regle en petit. Empty state : *"No signals fired today."* (`signaux`). Compteur en header : `Today's signals · 3`.
- **Valuation** : top 5 des tickers avec `score_valorisation`, barre horizontale 0-7 en terracotta, PER / PB / margin / ROE / D/E en mono a droite (`lignes[*].score_valorisation`, `fondamentaux`).
- **Market watch** (ex-"Veille") : titre `Market watch · Perplexity`, texte serre en Fraunces italique 15px, sources listees en `text-xs` avec liens externes (`veille.texte`, `veille.sources`). Icon `↗` a cote de chaque source. Perplexity conseille : *featured story avec accent terracotta + smaller items groupes "Your positions / Watchlist / Market backdrop"* — en V1 on a un seul bloc, on decoupera si Perplexity retourne du contenu structure.

### Footer (h ~ 40px)

Menu discret : *"Report generated Aug 29, 2026 · 12 positions · 3 signals · Source: eToro"*. Rien de plus.

---

## 4. Component inventory

A installer via `npx shadcn@latest add` (dans `dashboard/`) :

```
npx shadcn@latest add card badge table tabs sheet separator skeleton \
  tooltip dropdown-menu scroll-area sonner chart accordion input select \
  toggle-group toggle
```

Role par composant (evidence entre parentheses quand applicable) :

- **Card** — chaque tuile metrique, chaque section.
- **Badge** — sens L/S, niveaux de signal (`info` / `attention` / `alerte`), tag benchmark, tag "missing quote".
- **Table** — tableau des positions ; tri cote client via `<TableHead>` cliquable (pattern Fey/Uniswap).
- **Tabs** — fenetre de la courbe d'equity (1M/3M/6M/YTD/MAX) + segmented `1D/7D/30D/ALL` sur la tuile PnL (pattern Origin `/screens/3a516cce-...`, Monarch `/screens/c9f450db-...`).
- **Sheet** — panneau lateral de detail ticker (V1.5). Pattern : **Monarch VTI detail** (`/screens/07bf1695-...`) qui glisse depuis la droite avec chart + summary + accounts.
- **Separator** — hairlines editoriales entre blocs.
- **Skeleton** — placeholders par section pendant le fetch (jamais un spinner plein ecran).
- **Tooltip** — definitions Sharpe, HHI, MaxDD, Beta au survol du label (recommandation Perplexity : *tooltip + text alternative*).
- **Dropdown-menu** — menu `⋯` du header (regenerate watch, refresh fundamentals, view raw JSON).
- **Scroll-area** — panneau des signaux si la liste devient longue.
- **Sonner** — toasts pour "Report refreshed", erreurs de fetch, progress des refresh longs (regenerate watch / fundamentals).
- **Chart** (recharts wrapper) — equity curve + drawdown overlay + benchmark overlay + donut + sparklines.
- **Accordion** — details des criteres de valorisation par ticker (7 lignes qui se deplient).
- **Input / Select** — filtres du tableau positions (V1.5).
- **Toggle-group** — bascule "value / PnL / PnL %" sur les grandes tuiles (V1.5).
- **Toggle** — bascules overlays (drawdown on/off, benchmark on/off) sur l'equity curve.

Pas de `Breadcrumb` en V1 (une seule page) ; a considerer si on ajoute `/positions` et `/signaux` en V2 (recommandation Perplexity pour la feel editoriale).

---

## 5. Data mapping

Endpoint : `GET http://127.0.0.1:8000/rapport` -> `Rapport`. Un seul fetch cote page (server component) avec revalidation manuelle par le bouton Refresh. Payload enrichi depuis v1 avec **`deltas`** (voir §2 des instructions).

| Section UI | Label affiche | Champs (chemin dans `Rapport`) |
|-----------|--------------|-------------------------------|
| Header title | Portfolio | `nombre_positions` (derive), `genere_le` |
| Tile 1 — Current value | CURRENT VALUE | `valeur_courante` + `deltas.pnl_1d_abs`, `deltas.pnl_1d_pct` |
| Tile 2 — Total PnL | TOTAL PNL | `gain_absolu`, `gain_pct`, `montant_investi` ; segmented -> `deltas.pnl_{1d,7d,30d}_{abs,pct}` |
| Tile 3 — Sharpe | SHARPE | `metriques.sharpe`, `metriques.volatilite_annuelle_pct`, `metriques.rendement_annuel_pct` |
| Tile 4 — Max drawdown | MAX DRAWDOWN | `metriques.max_drawdown_pct`, `metriques.beta`, `metriques.benchmark` |
| Equity curve | Equity | `equity_series` (API) ; fallback = reconstruction depuis `lignes[*].cotation.clotures` |
| Drawdown overlay | Drawdown | derive de `equity_series` cote client |
| Benchmark overlay | vs SPY | idealement `equity_series.benchmark` ; sinon absent en V1 |
| Donut concentration | Concentration | `lignes[*].ticker`, `lignes[*].poids_pct`, `metriques.hhi`, `metriques.plus_grosse_position_pct` |
| Table positions | Positions | `lignes[*]` : `.ticker`, `.position.est_long`, `.position.quantite`, `.position.prix_entree`, `.cotation.prix`, `.cotation.variation_jour_pct`, `.cotation.clotures` (sparkline), `.poids_pct`, `.gain_absolu`, `.gain_pct`, `.rsi_14`, `.sma_20`, `.sma_50`, `.volatilite_20j_pct`, `.score_valorisation.score` |
| Missing quotes | Missing quotes | `tickers_manquants` |
| Signals card | Today's signals | `signaux[*]` : `.ticker`, `.niveau`, `.regle`, `.message` ; groupes par `niveau` (`alerte` > `attention` > `info`) |
| Valuation card | Valuation | `lignes[*].score_valorisation` (`.score`, `.criteres_remplis`, `.criteres_manquants`, `.inconnus`) + `lignes[*].fondamentaux` (`per`, `price_to_book`, `marge_nette_pct`, `debt_to_equity`, `roe_pct`, `dividend_yield_pct`, `secteur`) |
| Market watch card | Market watch | `veille.texte`, `veille.sources` |
| Footer | — | `genere_le`, `nombre_positions`, `signaux.length`, `source` (a exposer par l'API) |

Types TS : generer un `types.ts` a la main qui reflete `Rapport`, `LignePortefeuille`, `MetriquesPortefeuille`, `Fondamentaux`, `ScoreValorisation`, `Signal`, `Cotation`, **`Deltas`**. Ne pas dependre d'un generateur OpenAPI en V1. Les noms de champs restent en francais dans le type (miroir de la dataclass Python), les labels d'UI sont traduits au moment du rendu.

---

## 6. Design tokens

Dark = mode par defaut. Light reste fonctionnel mais tempere : le produit
vit en dark, on ne teste ni ne calibre le light sur ecran plein. Le toggle
`d` bascule pour ceux qui veulent.

Palette hex (rendu final ; les valeurs `oklch` reelles sont dans
`app/globals.css`) :

- Fond dark : `#0A0A0A` (`.dark`) / `#FAFAFA` (light)
- Surface / card dark : `#141414` / `#FFFFFF`
- Foreground dark : `#FAFAFA` / `#0A0A0A`
- Border dark : `rgba(255,255,255,0.08)` / `rgba(0,0,0,0.10)`
- Muted foreground dark : `#9E9E9E` / `#737373`
- **Fluo green 500 (primary + PnL+ + equity)** : `#4EFF9F` dark / `#22A05E` light
- **Fluo red 500 (destructive + PnL- + alerte)** : `#FF4A4A` dark / `#DC2626` light
- **Fluo amber (attention)** : `#FFC64A` dark / `#D97706` light
- Chart 4 (bench neutre) : `#B3B3B3` / gris moyen

Bordures fines uniquement, aucune ombre, radius `0.375rem` (`--radius`)
plus sec que le defaut shadcn — plus proche d'un terminal que d'un editorial.

Typographie :

- **Inter** (`variable: '--font-sans'`, weights 400/500/600/700) — TOUT le texte de l'app.
  Alias : `--font-display: var(--font-sans)` pour que les classes `font-display` heritees rendent Inter. Un `.font-display { font-weight: 600; letter-spacing: -0.01em }` dans `@layer base` donne le rendu bold Apple-esque sans toucher chaque composant.
- **Geist Mono** (`--font-mono`) — chiffres des tuiles et du tableau (`font-mono tabular-nums`).
- **Aucun serif, aucun italic decoratif.** Fraunces retire du scaffold. L'italic est autorise UNIQUEMENT pour du meta contextuel (ex : "missing quote" sur une ligne de position).
- Echelle : hero tuile `text-4xl font-mono font-semibold tabular-nums`, section `text-2xl font-display`, label `text-xs uppercase tracking-[0.14em] text-muted-foreground`, corps `text-sm`.

Espacement : gap standard 16 / 24. Fond des cards : `bg-card` (`#141414`),
border 1px `border-border` (`rgba(255,255,255,0.08)`), pas d'ombre.

---

## 7. Interaction patterns

- **Tri** : entetes de colonne cliquables (icone chevron discret) ; multi-tri non necessaire en V1.
- **Filtres** : au-dessus du tableau, `Input` "Search ticker" + `Select` "Signal level" + `Select` "Sector" (V1.5).
- **Hover** : lignes de tableau -> `bg-secondary/40` ; cellules PnL -> tooltip *"Entry $X · Current $Y · Qty Z"*.
- **Badges signaux** :
  - `info` -> `bg-muted text-muted-foreground border`
  - `attention` -> `bg-[--chart-4]/15 text-[--chart-4] border-[--chart-4]/40` (ambre)
  - `alerte` -> `bg-primary/15 text-primary border-primary/40`
- **Empty states** editoriaux, phrase courte en italique Fraunces :
  - *"Nothing to report today."*
  - *"No fundamentals available for these tickers."*
  - *"Market watch hasn't been generated yet."*
  - *"Not enough history yet."* (deltas nuls)
- **Loading** : `Skeleton` par section (jamais un spinner plein ecran) ; les tuiles metriques gardent leur label, seul le chiffre devient une barre grise.
- **Erreurs** : toast Sonner + carte inline *"Couldn't reach the report. Check that the API is running on 127.0.0.1:8000."* avec bouton `Retry`.
- **Refresh scoped** :
  - Bouton `Refresh` du header + raccourci `r` -> `fetch('/rapport?scope=quotes')` (rapide). Toast Sonner *"Quotes refreshed."* + comparaison avec l'etat precedent pour detecter les nouveaux signaux.
  - `⋯` -> *"Regenerate market watch"* -> `fetch('/rapport?scope=veille')`. Toast progress *"Regenerating market watch..."* puis *"Market watch updated."*
  - `⋯` -> *"Refresh fundamentals"* -> `fetch('/rapport?scope=fundamentals')`. Toast progress *"Refreshing fundamentals..."*
  - Note d'implementation : les scopes seront supportes cote API (endpoint deja unifie, ajouter un query param) — c'est une open question §11.
- **Animation refresh** (source : Perplexity §12.b) : sur nouvelle equity_series, interpoler la ligne 300-500ms, garder axes / labels / annotations fixes, dot terracotta sur le point terminal + label *"Updated just now"* qui fade in. **Respecter `prefers-reduced-motion`** : mise a jour instantanee, on garde uniquement le highlight du dernier point et le timestamp.

---

## 8. Charts

Librairie : `chart` shadcn (wrapper autour de recharts, deja livre par `npx shadcn add chart`).

- **Equity curve** : `AreaChart`, gradient terracotta -> transparent, ligne pleine 1.5px. Axe X en dates (Fraunces italic tick), axe Y en `NumberFormat` compact ("$12.4k"). Tooltip custom : date + valeur + PnL cumule + delta jour.
- **Drawdown overlay** : `Line` en pointille sur meme graphe, axe Y secondaire cote droit (%). Toggle on/off via `Toggle`.
- **Benchmark overlay** : `Line` fine en `--chart-3` (gris), axe Y partage (rebase 0). Toggle on/off. Le benchmark reste **visuellement subordonne** — la portfolio line reste dominante (recommandation Perplexity + pattern Monarch `/screens/c9f450db-...`).
- **Concentration** : `PieChart` type donut, `innerRadius=60%`, 5 slices terracotta degrade + gris pour "Others". Label central : `HHI XX.XX`.
- **Sparklines** dans la table positions : `LineChart` mini (largeur ~80px, hauteur 24px), stroke `primary`, aucun axe, source = `cotation.clotures[-30:]`.
- **Barres score valorisation** : element simple 7 segments (`div` flex + `bg-primary`), pas besoin de recharts.

Regle generale : jamais plus de 3 couleurs par graphe, jamais de grille de fond noire, ticks en `text-muted-foreground`. Motion honoree via `prefers-reduced-motion`.

---

## 9. Notifications UX

Les signaux Trackerbot sont deja envoyes sur Telegram : le dashboard n'a pas a re-notifier. Il **affiche** :

1. **Panneau overview** — carte "Today's signals" (voir §3). Canal principal.
2. **Signal dot dans la ligne de position** — un dot terracotta apparait dans la colonne "Signals" du tableau des que le ticker a au moins un signal ; tooltip liste les regles.
3. **Toast Sonner** discret quand un `Refresh` fait passer le nombre d'alertes de N a N+1 (compare a l'etat precedent, cote client). Pas de son. Toast text : *"1 new alert · TICKER"*.
4. **Pas de banniere globale** en V1. Une banniere n'apparait qu'a partir de 3 `alerte` simultanees : bandeau creme fonce en haut de page *"3 active alerts — view signals"*, cliquable.
5. **Freshness cue** sur l'equity curve : dot terracotta + *"Updated just now"* qui fade in apres refresh (voir §7).

Pattern de reference pour la severite : **Sentry Feed** (`/screens/084d445d-...`) — colonne "Trend / 24h / Events / Priority" avec priorite en icone discrete. On adopte la triple severite sans copier le look sombre.

Pas de centre de notifications separe en V1 (la page overview est le centre).

---

## 10. Non-goals (V1)

- Pas de multi-utilisateur, pas d'auth (le dashboard tourne en local).
- Pas de streaming temps reel (WebSocket) : refresh manuel + revalidation Next.
- Pas de passage d'ordre, jamais.
- Pas de mobile-first : responsive raisonnable a partir de `md`, mais la cible est desktop 1440px.
- Pas de i18n runtime : **UI en anglais**, brief en francais.
- **Historique inter-jours OK** (nouveau vs v1) : `storage.py` + `deltas` dans le payload. Pas d'ecran d'archive complet en V1 — les deltas sur les tuiles suffisent.
- Pas de theming utilisateur : creme + terracotta est le style unique, dark mode inclus mais reste chaud.
- Pas d'export PDF automatique (mais la page doit rester imprimable via CSS `@media print`).

---

## 11. Open questions (a valider avec l'utilisateur)

1. **Endpoint scoped** — l'API `/rapport` doit-elle accepter `?scope=quotes|veille|fundamentals` ou faut-il exposer 3 endpoints separes (`/rapport/quotes`, `/rapport/veille`, `/rapport/fundamentals`) ? La v2 du brief suppose la premiere option (query param) mais l'implementation reste a decider.
2. **`equity_series` structure** — l'API expose-t-elle `equity_series: {dates: string[], values: number[], benchmark?: number[]}` ? Sans la cle `benchmark`, l'overlay SPY sur l'equity curve est impossible (toggle grise avec tooltip *"Benchmark series not available"*).
3. **Sous-page Positions** — a partir de combien de lignes migre-t-on hors de l'overview ? Proposition : 20 lignes.
4. **Structure de `veille`** — si Perplexity renvoie des sections par ticker (recommandation §12.b), faut-il enrichir `Veille` avec `sections: {ticker: string, texte: string, sources: []}[]` ? Sans structure, on garde un seul bloc texte.
5. **Historique deltas dispo** — combien de jours d'historique SQLite a-t-on typiquement au moment du render ? Impact : si `pnl_30d_pct` est presque toujours `null` les 30 premiers jours, on cache le segment ALL/30D des tuiles jusqu'a X entrees.
6. **Icones** — quelle bibliotheque ? `lucide-react` est le defaut shadcn. Confirmer.

---

## 12. Evidence trail

### 12.a Mobbin — flows et screens cites

Requetes cette session via `mcp__claude_ai_Mobbin__search_screens` / `_flows` (platform=web) :

- **"portfolio overview with total value and daily change"** (6 resultats) — influence §3 header + tuiles : Copilot Money https://mobbin.com/screens/df0a19e8-30c4-4d6a-8855-7060478380ac ; Monarch https://mobbin.com/screens/c9f450db-5200-4352-87b4-fa11ae8f2137 ; Origin https://mobbin.com/screens/3a516cce-bf0f-4eb8-90d7-1625e5d49c32 ; Quicken (Day $ / Day % / 1M $ / 1M %) https://mobbin.com/screens/f61813eb-4a2f-44b7-8c19-e34ae0072979
- **"watchlist table with sparkline and percent change columns"** (5) — influence §3 Positions : Fey https://mobbin.com/screens/f4b1fb8e-1db1-407c-a1b1-41ec1eb312c7 ; Uniswap Tokens https://mobbin.com/screens/e39f0d0f-bed1-49ff-92e0-c53d36d34de6
- **"portfolio allocation donut with concentration percentages"** (5) — influence §3 Concentration : Quicken savings goals https://mobbin.com/screens/8c443a6b-1bd2-468d-afd6-a01042929932
- **"equity curve line chart with time range tabs"** (5) — influence §3 Equity + §8 : Origin https://mobbin.com/screens/3a516cce-bf0f-4eb8-90d7-1625e5d49c32 ; Fey TSLA (tabs 1D/1W/1M/3M/YTD/1Y/5Y/All + news summary a droite) https://mobbin.com/screens/4ac6daeb-a2ab-46ea-b8fe-7e328f2c493b
- **"news feed article list with source citations"** (5) — influence §3 Market watch : Perplexity Discover (featured + trending aside) https://mobbin.com/screens/ec59e633-ba10-46a5-9277-363061007f02 ; Substack Home https://mobbin.com/screens/de1b3c40-9046-4a6a-9bfb-bc7c8476e7e3
- **"metric tile with delta indicator and trend arrow"** (5) — influence §3 tuiles : Whop Analytics (tuiles + sparklines) https://mobbin.com/screens/add1901d-9b32-4751-83e0-b44083fd2c03
- **"alerts and signals inbox with severity levels"** (5) — influence §9 : Sentry Feed (Trend / 24h / Events / Priority) https://mobbin.com/screens/084d445d-603f-48e0-8442-dd5cf0ffacb2
- **"stock detail with fundamentals PE ratio and margin"** (5) — influence §3 Valuation + Sheet V1.5 : Perplexity Finance TSLA financials https://mobbin.com/screens/9403c5aa-9ecf-4e38-828f-7f702ef23448 ; Monarch VTI detail sheet https://mobbin.com/screens/07bf1695-3589-443c-a0eb-4ed8dab05de1 ; Revolut Apple https://mobbin.com/screens/3076e57a-078d-482f-be3a-9c4d079c3153
- **"dashboard header with refresh button and overflow menu"** (5) — peu concluant : Zoho CRM https://mobbin.com/screens/83a3cd87-1eee-4748-8194-ae159f50f3db. Aucun screen ne montre exactement le split "Refresh + `⋯` scoped" — pattern derive de Copilot Money (roue crantee coin de la card Investments) applique au header global.
- **Flow "investment app portfolio overview and holdings drilldown"** — Origin "Portfolio" 5 ecrans (overview -> holdings tab -> chart + benchmark), **source principale pour la sequence** : https://mobbin.com/flows/054c2bf6-ebe0-4e21-8e52-97f48ebf01b7 ; Origin "Portfolio overview" https://mobbin.com/flows/5f9f6d4a-19d7-4c03-bb7d-a1a8c73bfbd4 ; Copilot Money "Investments" https://mobbin.com/flows/09dca80d-68bf-4653-b1b4-13d19384c634
- **Flow "dashboard refresh data with time range selection"** — Railway "Filtering by time" https://mobbin.com/flows/a8043688-ec79-4a69-a0aa-78153021e649 ; Seline "Filtering dashboard by date" https://mobbin.com/flows/766eff87-4f98-488e-948a-c1ad0029a569. Aucun ne montre un refresh scoped — invention alignee sur le split Perplexity/Yahoo (voir §11.1).

### 12.b Perplexity — questions posees et findings

1. **"Best UX patterns for portfolio dashboards showing Sharpe drawdown alongside PnL"** — influence §3 tuiles + §8 :
   - Sources retenues :
     - lollypop.design — "Investment Dashboard UX Design Guide (May 2026)" — https://lollypop.design/blog/2026/may/investment-dashboard-ux-design-guide/
     - lazarev.agency — "Dashboard UX design" — https://www.lazarev.agency/articles/dashboard-ux-design
     - wildnetedge.com — "Fintech UX design best practices" — https://www.wildnetedge.com/blogs/fintech-ux-design-best-practices-for-financial-dashboards
   - Recommandations retenues : `Lead with one cumulative-PnL chart and a consistent time-range control` (adopte §3 equity), `Place Sharpe, max drawdown, and beta in a compact Risk card beside the chart` (partiellement adopte — on garde 4 tuiles au lieu d'une carte Risk pour rester editorial), `Visualize max drawdown directly on the PnL timeline` (adopte -> overlay drawdown §8), `Make beta benchmark-specific` (adopte -> "Beta vs SPY" en sous-ligne §3 tile 4), `Progressive disclosure + accessible alternatives via tooltip + text` (adopte §7).
2. **"In-app market news feed patterns + smooth equity-curve refresh animations"** (fusionnee car rate-limit sur premiere tentative separee) — influence §3 Market watch + §7 animation :
   - Sources WCAG et animation :
     - openreplay.com — `prefers-reduced-motion` — https://blog.openreplay.com/prefers-reduced-motion-accessible-animation/
     - w3.org WCAG21 C39 — https://www.w3.org/WAI/WCAG21/Techniques/css/C39
     - accessibility.build 2.3.3 — https://accessibility.build/wcag/2-3-3
   - Recommandations retenues : `Lead with relevance, not recency` (adopte pour V2 marchet watch quand Perplexity renverra du contenu structure — voir §11.4), `Attach news directly to positions` (a valider avec la structure `veille.sections` §11.4), `Editorial hierarchy: one featured story + smaller grouped items` (adopte), `Animate the transition, not the entire chart` + `300-500ms interpolation` + `honor prefers-reduced-motion` (adopte §7 anim).
3. **"shadcn dashboard editorial patterns 2025"** — influence §2 IA + §4 inventory :
   - Sources : ui.shadcn.com/examples/dashboard — https://ui.shadcn.com/examples/dashboard ; github shadcn-ui/ui — https://github.com/shadcn-ui/ui
   - Recommandation retenue : `Breadcrumb -> Typography-led headline -> Chart as lead visual -> Tabs for related coverage`. Adopte partiellement : Breadcrumb reporte en V2 (§4), le reste applique en V1.

### 12.c Ce que v1/v2 avaient juste (conserve tel quel)

- Grille 12 colonnes `max-w-[1240px]`, gap 24 — conserve.
- Ordre des sections Overview (header -> tuiles -> equity+donut -> table -> 3 cartes en pied -> footer) — conserve.
- Ne pas notifier depuis le dashboard (Telegram est deja le canal) — conserve.
- Skeleton par section, jamais spinner plein ecran — conserve.
- Payload API (`Rapport` + `equity_series` + `deltas`) — conserve.

### 12.d Ce que v2 recommandait et qu'on abandonne (pivot v3 : dashboard pro)

- **Palette creme + terracotta** -> pivot noir + fluo vert/rouge. Contrainte utilisateur post-v2 : "surtout pas de terracotta de creme et de marron, va a fond sur le noir avec des traits fluo".
- **Fraunces (serif editorial)** -> retire. Inter partout, `--font-display` alias sur Inter avec `.font-display { font-weight: 600 }` en base layer.
- **Empty states italique Fraunces** -> abandonner l'italique decoratif. Empty states = simple `text-muted-foreground` (voir §7).
- **"Journal de bord / magazine financier"** -> pivot vers "dashboard trading pro". Densite table-first ala Fey/Kraken.

### 12.e Nouvelles references Mobbin pour le pivot v3 (dark + fluo)

Requetes cette session via `mcp__claude_ai_Mobbin__search_screens` :

- **"eToro portfolio overview screen with holdings list, total value, PnL and chart"** (web) — resultats principalement blancs (Monarch, Origin, Copilot Money, Cake Equity) mais on retient [Gemini web Portfolio](https://mobbin.com/screens/cc6a1261-a495-4977-8ca8-36d9a20b46db) (fond noir, chart rouge fluo, gros nombre blanc bold) et [Kraken Pro](https://mobbin.com/screens/87cf22f4-48fa-474b-9ac1-ffe8eba368b1).
- **"Delta portfolio tracker dark mode with holdings breakdown and equity chart"** (ios) — [Yahoo Finance iOS](https://mobbin.com/screens/f90cf0d1-8f2f-424a-ad75-601345b47751) est la reference #1 (noir absolu, PnL vert/rouge fluo, chiffres bold, sparklines colorees), [Crypto.com](https://mobbin.com/screens/8505ff3c-ef22-46a9-b33e-3ae2bcdd39dc) et [QuestMobile RRSP](https://mobbin.com/screens/ed3dd312-6ff8-40aa-8837-b47a59ed801f) (aire d'equity vert fluo pleine largeur).
- **"dark mode trading dashboard with neon green red PnL indicators and equity chart"** (web) — [Binance Spot Grid](https://mobbin.com/screens/1dd4caa0-4a84-41db-ae44-37298bd785ff), [OKX](https://mobbin.com/screens/d83ddd9e-f689-41f1-9d29-1ca6070bcfac), [Coinbase](https://mobbin.com/screens/a372b65a-4ac3-4ff6-b9c3-a5bbb4ee42ad), [Gemini](https://mobbin.com/screens/a457e291-74c3-4bf7-a9e4-9f2ea3a97211) — densite pro, chiffres partout, colonnes de couleur, aucune fantaisie.
- **"portfolio holdings table with sparklines, weight, PnL columns on dark background"** (web) — [Fey Screener](https://mobbin.com/screens/920817af-adb1-4853-90ec-acd729c9101b) est la reference table (fond noir, monospace pour les nombres, PnL rouge/vert, sparklines mini). [Kraken](https://mobbin.com/screens/25b67ef9-d56e-4f69-865f-16a702da74b7) aussi.

### 12.f Outils utilises / echecs

- `mcp__claude_ai_Mobbin__search_screens` — OK a chaque requete v1 + v2 + v3.
- `mcp__claude_ai_Mobbin__search_flows` — OK sur v2 uniquement.
- `mcp__perplexity__perplexity_ask` — OK sur v2 uniquement.
- `mcp__mobbin__authenticate` — jamais necessaire.

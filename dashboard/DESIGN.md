# DESIGN.md — Tableau de bord Trackerbot

> Brief opinionne pour l'agent qui construit le dashboard.
> Cible : Next.js 16 + React 19 + Tailwind v4 + shadcn (style `base-rhea`), rendu par `/rapport` (FastAPI).
> Langue : francais pour les libelles metier, anglais pour le code.

---

## 1. North star

Un journal de bord d'investisseur, pas un terminal. Une page principale qui se lit comme une double-page de magazine financier : titres editoriaux en Fraunces, corps en Inter, fond creme, accents terracotta, chiffres cles en mono. Le PnL saute aux yeux avant les indicateurs techniques ; les signaux ressemblent a des notes de marge, jamais a des sirenes. On doit pouvoir imprimer la page et l'agrafer au cahier.

---

## 2. Information architecture

Ordre de priorite (V1 = une seule page ; les sous-pages ne se justifient que quand la page devient illisible) :

1. **Overview** (`/`) — l'unique page V1. Tout ce qui compte tient au-dessus ou juste en dessous du pli.
2. **Positions** (`/positions`) — V1.5 : deportee quand le tableau depasse 20 lignes ou qu'on veut filtrer serieusement.
3. **Signaux** (`/signaux`) — V2 : historique et regles declenchees ; en V1 c'est un panneau lateral.
4. **Veille** (`/veille`) — V2 : archive des veilles Perplexity ; en V1 c'est une carte au bas de l'overview.
5. **Reglages** (`/reglages`) — V2 : source de portefeuille, seuils, benchmark.

Aucune navigation profonde en V1. Une barre superieure minimaliste (logo texte "trackerbot", date de generation, bouton refresh, toggle dark) suffit.

---

## 3. Page layout — Overview

Grille : `max-w-[1240px] mx-auto px-6 py-8`, 12 colonnes, gap 24.

### Header (h ~ 88px)

- Colonnes 1-6 : titre Fraunces "Portefeuille" + sous-titre "genere le 29 aout 2026" (`genere_le`).
- Colonnes 7-12 (align right) : bouton `Refresh`, `Badge` benchmark ("vs SPY"), toggle dark, menu discret (source du portefeuille : eToro / YAML).

### Bandeau de tete — Metriques cles (au-dessus du pli, h ~ 180px)

Grille de 4 `Card` en colonnes 1-12 (chacune sur 3 colonnes) :

| Cellule | Contenu | Champ source |
|--------|---------|--------------|
| 1 | Valeur courante + delta jour en badge terracotta | `valeur_courante`, calcul jour |
| 2 | PnL absolu + PnL % (chiffres XL en mono, couleur signee) | `gain_absolu`, `gain_pct` |
| 3 | Sharpe + vol annuelle en sous-ligne | `metriques.sharpe`, `metriques.volatilite_annuelle_pct` |
| 4 | Max drawdown + beta en sous-ligne | `metriques.max_drawdown_pct`, `metriques.beta` |

Chaque `Card` : label Inter uppercase tracking-wide, valeur Fraunces 32-40px OU chiffre mono 28px, micro-legende en `text-muted-foreground text-xs`. Pas de fond colore, juste une fine bordure terracotta 10% sur le fond creme.

### Zone principale (h ~ 420px, sous le pli 1)

- Colonnes 1-8 : **Courbe d'equity** dans une `Card` : aire ombree terracotta, ligne pleine terracotta 700, overlay drawdown en pointille sombre. Tabs `1M / 3M / 6M / YTD / MAX` en haut a droite (donnees derivees de `serie_equity_portefeuille`, cote client si non expose ; sinon fenetre = `min(len(clotures))`).
- Colonnes 9-12 : **Concentration** dans une `Card` : donut leger (top 5 positions + "autres"), legende sous forme de liste avec `poids_pct`. En pied : HHI et plus grosse position (`metriques.hhi`, `metriques.plus_grosse_position_pct`).

### Positions (pleine largeur, h auto)

- `Card` avec `Table` shadcn, colonnes : Ticker | Sens (L/S badge) | Qte | Prix entree | Prix | Var 24h (sparkline mini) | Poids % | PnL abs | PnL % | RSI 14 | vs SMA 20/50 (glyphes ↑/↓) | Vol 20j | Score valo | Signaux (dot).
- Tri par defaut : `poids_pct` desc.
- Ligne en `hover:bg-secondary/40`, click sur ticker ouvre un `Sheet` de detail (V1.5).
- Tickers sans cotation en italique + tag "cotation manquante" (source : `tickers_manquants`).

### Trois cartes en pied (colonnes 1-4 / 5-8 / 9-12)

- **Signaux du jour** : liste groupee par niveau (`alerte` puis `attention` puis `info`), badge couleur par niveau, message + regle en petit. Empty state : "Aucun signal declenche." (`signaux`).
- **Valorisation** : top 5 des tickers avec `score_valorisation`, barre horizontale 0-7 en terracotta, PER / PB / marge / ROE / D/E en mono a droite (`lignes[*].score_valorisation`, `fondamentaux`).
- **Veille du jour** : titre "Veille Perplexity", texte serre en Fraunces italique, sources listees en `text-xs` avec liens (`veille.texte`, `veille.sources`).

### Footer (h ~ 40px)

Menu discret : "Rapport genere le ... · 12 positions · 3 signaux · Source : eToro". Rien de plus.

---

## 4. Component inventory

A installer via `npx shadcn@latest add` (dans `dashboard/`) :

```
npx shadcn@latest add card badge table tabs sheet separator skeleton \
  tooltip dropdown-menu scroll-area sonner chart accordion input select \
  toggle-group
```

Role par composant :

- **Card** — chaque tuile metrique, chaque section (equity, concentration, positions, signaux, valo, veille).
- **Badge** — sens L/S, niveaux de signal (`info` / `attention` / `alerte`), tag benchmark, tag "cotation manquante".
- **Table** — tableau des positions ; tri cote client via `<TableHead>` cliquable.
- **Tabs** — fenetre de la courbe d'equity (1M/3M/6M/YTD/MAX), plus filtres futurs.
- **Sheet** — panneau lateral de detail ticker (V1.5 : cotation, indicateurs, fondamentaux, signaux du ticker).
- **Separator** — hairlines editoriales entre blocs de la page.
- **Skeleton** — placeholders pendant le fetch de `/rapport` (une skeleton par section, pas une seule).
- **Tooltip** — definitions des metriques (Sharpe, HHI, MaxDD) au survol du label.
- **Dropdown-menu** — menu source dans le header (eToro / YAML / import).
- **Scroll-area** — panneau des signaux si la liste devient longue.
- **Sonner** — toasts pour "rapport rafraichi", erreurs de fetch.
- **Chart** (recharts wrapper) — courbe d'equity + drawdown + donut concentration + sparklines lignes de table.
- **Accordion** — details des criteres de valorisation par ticker (7 lignes qui se deplient).
- **Input / Select** — filtres du tableau positions (V1.5 : filtre par secteur, min poids, niveau de signal).
- **Toggle-group** — bascule "valeur / PnL / PnL %" sur les grandes tuiles.

---

## 5. Data mapping

Endpoint : `GET http://127.0.0.1:8000/rapport` -> `Rapport`. Un seul fetch cote page (server component) avec revalidation manuelle par le bouton Refresh.

| Section UI | Champs (chemin dans `Rapport`) |
|-----------|-------------------------------|
| Titre + date | `genere_le`, `nombre_positions` (derive) |
| Tuile Valeur | `valeur_courante`, delta = valeur - somme derniere cloture (cote client) |
| Tuile PnL | `gain_absolu`, `gain_pct`, `montant_investi` |
| Tuile Sharpe/Vol | `metriques.sharpe`, `metriques.volatilite_annuelle_pct`, `metriques.rendement_annuel_pct` |
| Tuile MaxDD/Beta | `metriques.max_drawdown_pct`, `metriques.beta`, `metriques.benchmark` |
| Courbe d'equity | serie `lignes[*].cotation.clotures` reconstituee (idealement expose par l'API comme `equity_series`) ; fallback = derniere valeur seule + placeholder |
| Overlay drawdown | derive de la meme serie cote client |
| Donut concentration | `lignes[*].ticker`, `lignes[*].poids_pct`, `metriques.hhi`, `metriques.plus_grosse_position_pct` |
| Table positions | `lignes[*]` : `.ticker`, `.position.est_long`, `.position.quantite`, `.position.prix_entree`, `.cotation.prix`, `.cotation.variation_jour_pct`, `.cotation.clotures` (sparkline), `.poids_pct`, `.gain_absolu`, `.gain_pct`, `.rsi_14`, `.sma_20`, `.sma_50`, `.volatilite_20j_pct`, `.score_valorisation.score` |
| Cotations manquantes | `tickers_manquants` |
| Panneau signaux | `signaux[*]` : `.ticker`, `.niveau`, `.regle`, `.message` ; groupes par `niveau` (`alerte` > `attention` > `info`) |
| Carte valorisation | `lignes[*].score_valorisation` (score, criteres_remplis, criteres_manquants, inconnus) + `lignes[*].fondamentaux` (`per`, `price_to_book`, `marge_nette_pct`, `debt_to_equity`, `roe_pct`, `dividend_yield_pct`, `secteur`) |
| Carte veille | `veille.texte`, `veille.sources` |

Types TS : generer un `types.ts` a la main qui reflete `Rapport`, `LignePortefeuille`, `MetriquesPortefeuille`, `Fondamentaux`, `ScoreValorisation`, `Signal`, `Cotation`. Ne pas dependre d'un generateur OpenAPI en V1.

---

## 6. Design tokens

Palette (approximations hex ; les vraies valeurs restent en `oklch` pour rester coherent avec le scaffolding shadcn) :

- Creme fond : `#F6F1E7` (light) / `#1A1712` (dark)
- Creme surface : `#FBF6EC` / `#221E17`
- Encre : `#1F1B16` / `#F3EEE3`
- Terracotta 500 : `#C6633F`
- Terracotta 700 : `#9C4A2E`
- Terracotta 100 : `#F1D9CB`
- Vert sobre (PnL +) : `#4E7A4B`
- Rouge sobre (PnL −, alerte) : `#B24A3A` (proche terracotta pour cohesion)
- Ambre attention : `#C79A3A`
- Muted encre : `#7C6F5B`

A coller dans `app/globals.css` (remplace les blocs `:root` et `.dark` existants) :

```css
:root {
    --background: oklch(0.955 0.024 82);          /* creme */
    --foreground: oklch(0.22 0.02 60);             /* encre chaude */
    --card: oklch(0.975 0.018 82);
    --card-foreground: oklch(0.22 0.02 60);
    --popover: oklch(0.975 0.018 82);
    --popover-foreground: oklch(0.22 0.02 60);
    --primary: oklch(0.55 0.14 40);                /* terracotta 500 */
    --primary-foreground: oklch(0.98 0.01 80);
    --secondary: oklch(0.92 0.03 75);
    --secondary-foreground: oklch(0.28 0.03 55);
    --muted: oklch(0.93 0.02 78);
    --muted-foreground: oklch(0.5 0.03 60);
    --accent: oklch(0.88 0.07 55);                 /* terracotta 100 */
    --accent-foreground: oklch(0.3 0.08 40);
    --destructive: oklch(0.55 0.16 30);
    --border: oklch(0.88 0.02 70);
    --input: oklch(0.9 0.02 70);
    --ring: oklch(0.55 0.14 40);
    --chart-1: oklch(0.55 0.14 40);                /* terracotta */
    --chart-2: oklch(0.7 0.09 45);
    --chart-3: oklch(0.5 0.05 65);
    --chart-4: oklch(0.65 0.09 100);               /* ambre */
    --chart-5: oklch(0.45 0.08 150);               /* vert sobre */
    --radius: 0.5rem;
}

.dark {
    --background: oklch(0.18 0.01 55);
    --foreground: oklch(0.94 0.02 80);
    --card: oklch(0.22 0.01 55);
    --card-foreground: oklch(0.94 0.02 80);
    --popover: oklch(0.22 0.01 55);
    --popover-foreground: oklch(0.94 0.02 80);
    --primary: oklch(0.68 0.13 42);
    --primary-foreground: oklch(0.18 0.02 40);
    --secondary: oklch(0.28 0.02 55);
    --secondary-foreground: oklch(0.94 0.02 80);
    --muted: oklch(0.28 0.02 55);
    --muted-foreground: oklch(0.72 0.02 70);
    --accent: oklch(0.35 0.06 45);
    --accent-foreground: oklch(0.94 0.02 80);
    --destructive: oklch(0.65 0.15 30);
    --border: oklch(1 0 0 / 8%);
    --input: oklch(1 0 0 / 12%);
    --ring: oklch(0.68 0.13 42);
    --chart-1: oklch(0.72 0.13 42);
    --chart-2: oklch(0.6 0.09 50);
    --chart-3: oklch(0.65 0.04 70);
    --chart-4: oklch(0.75 0.1 100);
    --chart-5: oklch(0.6 0.09 150);
}
```

Typographie :

- Ajouter Fraunces via `next/font/google` (`variable: '--font-display'`, subsets latin, poids 400/500/600, italic on). L'ajouter dans `@theme inline` : `--font-display: var(--font-display);` puis dans `<html>` : `className={cn(..., fraunces.variable)}`.
- Utility : `font-display` -> Fraunces (titres, chiffres editoriaux), `font-sans` -> Inter (corps, labels), `font-mono` -> Geist Mono (chiffres de tableau, prix, tickers).
- Echelle : display XL `text-4xl md:text-5xl`, section `text-2xl`, tuile chiffre `text-3xl font-mono`, label `text-xs uppercase tracking-[0.14em] text-muted-foreground`, corps `text-sm`.

Espacement : gap standard 16 / 24 / 32. Radius : `--radius: 0.5rem` (moins arrondi que le defaut shadcn pour un rendu editorial). Bordures : `border-border/70` partout, jamais d'ombre lourde ; au maximum `shadow-[0_1px_0_rgb(0_0_0/0.04)]` pour les cartes.

---

## 7. Interaction patterns

- **Tri** : entetes de colonne cliquables (icone chevron discret) ; multi-tri non necessaire en V1.
- **Filtres** : au-dessus du tableau, `Input` recherche ticker + `Select` niveau signal + `Select` secteur (V1.5).
- **Hover** : lignes de tableau -> `bg-secondary/40` ; cellules PnL -> tooltip avec detail (prix entree, prix courant, quantite).
- **Badges signaux** :
  - `info` -> `bg-muted text-muted-foreground border`
  - `attention` -> `bg-amber-100 text-amber-900 border-amber-300` (ou tokens equivalents `--chart-4`)
  - `alerte` -> `bg-primary/15 text-primary border-primary/40`
- **Empty states** editoriaux, phrase courte en italique Fraunces : "Rien a signaler aujourd'hui.", "Aucun fondamental disponible pour ces valeurs.", "La veille n'a pas encore ete generee."
- **Loading** : `Skeleton` par section (jamais un spinner plein ecran) ; les tuiles metriques gardent leur label, seul le chiffre devient une barre grise.
- **Erreurs** : toast Sonner + carte inline "Impossible de charger le rapport. Verifier que l'API tourne sur 127.0.0.1:8000." avec bouton `Reessayer`.
- **Refresh** : bouton dans le header + raccourci `r` (ecouteur global comme le `d` deja en place).

---

## 8. Charts

Librairie : `chart` shadcn (wrapper autour de recharts, deja livre par `npx shadcn add chart`).

- **Equity curve** : `AreaChart`, gradient terracotta -> transparent, ligne pleine 1.5px. Axe X en dates (Fraunces italic tick), axe Y en `NumberFormat` compact ("$12.4k"). Tooltip custom : date + valeur + PnL cumule.
- **Drawdown overlay** : `Line` en pointille sur meme graphe, axe Y secondaire cote droit (%). Toggle on/off via `Toggle`.
- **Concentration** : `PieChart` type donut, `innerRadius=60%`, 5 slices terracotta degrade + gris pour "autres".
- **Sparklines** dans la table positions : `LineChart` mini (largeur ~80px, hauteur 24px), stroke `primary`, aucun axe, source = `cotation.clotures[-30:]`.
- **Barres score valorisation** : element simple 7 segments, pas besoin de recharts.

Regle generale : jamais plus de 3 couleurs par graphe, jamais de grille de fond noire, ticks en `text-muted-foreground`.

---

## 9. Notifications UX

Les signaux Trackerbot sont deja envoyes sur Telegram : le dashboard n'a pas a re-notifier. Il **affiche** :

1. **Panneau lateral overview** — carte "Signaux du jour" (voir §3). C'est le canal principal.
2. **Point rouge dans la ligne de position** — un `dot` terracotta apparait dans la colonne "Signaux" du tableau des que le ticker a au moins un signal ; tooltip liste les regles.
3. **Toast Sonner** discret quand un `Refresh` fait passer le nombre d'alertes de N a N+1 (compare a l'etat precedent, cote client). Pas de son.
4. **Pas de banniere globale** en V1. Une banniere n'apparait qu'a partir de 3 `alerte` simultanees : bandeau creme fonce en haut de page "3 alertes actives — voir les signaux", cliquable.

Pas de centre de notifications separe en V1 (la page overview est le centre).

---

## 10. Non-goals (V1)

- Pas de multi-utilisateur, pas d'auth (le dashboard tourne en local).
- Pas de streaming temps reel (WebSocket) : refresh manuel + revalidation Next.
- Pas de passage d'ordre, jamais.
- Pas de mobile-first : responsive raisonnable a partir de `md`, mais la cible est desktop 1440px.
- Pas de i18n : francais fige.
- Pas d'historique multi-jours en V1 (le rapport est instantane). L'archivage viendra avec une table SQLite cote bot.
- Pas de theming utilisateur : creme + terracotta est le style unique, dark mode inclus mais reste chaud.
- Pas d'export PDF automatique (mais la page doit rester imprimable via CSS `@media print`).

---

## 11. Open questions (a valider avec l'utilisateur)

1. **Serie d'equity** — l'API `/rapport` expose-t-elle une serie temporelle alignee, ou faut-il reconstruire cote client depuis `lignes[*].cotation.clotures` (fenetre commune) ? Impact : ajouter un champ `equity_series` au Rapport simplifie la vie.
2. **Historique** — voulons-nous garder les rapports precedents (SQLite ou fichiers datés) pour comparer d'un jour a l'autre (delta jour dans la tuile Valeur) ? Sans historique, "variation jour" se limite a `cotation.variation_jour_pct` par ligne.
3. **Sous-page Positions** — a partir de combien de lignes migre-t-on hors de l'overview ? Proposition : 20 lignes, mais depend de la taille reelle du portefeuille.
4. **Traduction des libelles techniques** — RSI, SMA, HHI, Sharpe restent en anglais ; PER / PB / D/E aussi ? Ou francise-t-on tout (marge nette, dette/fonds propres) ? Proposition actuelle : anglais pour les acronymes financiers, francais pour les phrases.
5. **Refresh** — le bouton doit-il aussi relancer la veille Perplexity et les fondamentaux Yahoo (couteux) ou seulement les cotations ? Proposition : bouton principal = cotations seules, menu "..." = "Regenerer la veille" et "Rafraichir les fondamentaux" separement.

---

## 12. Evidence trail

Transparence sur la recherche :

- **Mobbin** (`mcp__claude_ai_Mobbin__search_screens`) et **Perplexity** (`mcp__perplexity__perplexity_ask`) : outils demandes dans le brief mais **refuses par le sandbox de permissions** dans cette session. Impossible de citer des ecrans ou requetes precis.
- Les recommandations s'appuient sur les conventions publiques et bien documentees des references citees dans le brief :
  - Bandeau 4 tuiles metriques + courbe equity dominante -> pattern **Delta / Robinhood / eToro**.
  - Table dense avec sparklines + colonnes signaletiques -> **TradingView watchlist** et **Bloomberg BLP**.
  - Metric cards editoriales + skeletons par section + toggle theme discret -> **Vercel Analytics / Linear Insights / Stripe Dashboard**.
  - Carte "veille" avec sources listees en pied -> pattern **FT / Perplexity Finance**.
  - Panneau signaux triple severite -> **Linear Inbox** et **Sentry** (info / warning / error).
- Recommandation : la prochaine iteration devrait rejouer ces requetes avec les permissions Mobbin/Perplexity activees pour confirmer/enrichir la §3 (grille overview) et §7 (patterns de badges).

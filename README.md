# trackerbot

Assistant personnel de suivi de portefeuille actions et ETF.

trackerbot lit les positions depuis eToro (API publique, lecture seule) ou
depuis un fichier YAML local, calcule des indicateurs techniques sur les
cours, evalue un jeu de regles de surveillance, produit un rapport lisible
et pousse eventuellement les alertes par Telegram. Une commande separee
recupere une veille de marche quotidienne via l'API Perplexity.

Le bot ne passe aucun ordre, ne modifie rien chez le courtier et n'ouvre
aucun port : tout le trafic est sortant.

Disclaimer : Personal project, built for my own use. Nothing in this repository constitutes investment advice or a recommendation to buy or sell any security. Past performance is not indicative of future results.
Use at your own risk.

## Contraintes de securite

- Depot publiable : aucun secret n'est ni ne doit etre commis. Toutes les
  cles vivent dans un `.env` local, ignore par `.gitignore`. Seul
  `.env.example` documente les variables attendues.
- Positions privees : `data/` et `portfolio.yaml` sont ignores par git. Le
  fichier `portfolio.example.yaml` fourni ne contient que des exemples.
- Aucun endpoint d'ecriture eToro n'est implemente. Les cles doivent etre
  emises avec le scope de lecture seule `etoro-public:trade.real:read`.
- Aucun webhook Telegram : le bot appelle `sendMessage`, il n'ecoute pas.

## Installation

Prerequis : Python 3.12.

```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Configuration

Copier `.env.example` vers `.env` puis remplir ce qui est utilise :

```
cp .env.example .env
```

Variables :

- `ETORO_API_KEY`, `ETORO_USER_KEY` : cles emises depuis le compte eToro
  verifie, en lecture seule. `ETORO_ENVIRONMENT` vaut `demo` ou `real`
  (rester sur `demo` tant que la lecture n'est pas validee).
- `PERPLEXITY_API_KEY` : cle API Perplexity utilisee par la commande
  `veille` et par `notify --avec-veille`.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` : token du bot BotFather et
  identifiant du seul chat autorise a recevoir les messages.
- `PORTFOLIO_FILE` : chemin du portefeuille YAML utilise quand aucune cle
  eToro n'est fournie. Par defaut `data/portfolio.yaml`.

Pour demarrer sans eToro, copier l'exemple :

```
cp portfolio.example.yaml data/portfolio.yaml
```

### Activer les cles eToro (lecture seule)

1. Verifier le compte eToro (piece d'identite + justificatif) : l'acces
   API n'est pas disponible avant la validation KYC.
2. Depuis `https://www.etoro.com/settings/api`, generer une paire de cles
   avec le seul scope `etoro-public:trade.real:read`. Aucun scope
   d'ecriture n'est necessaire, aucun n'est utilise par le bot.
3. Renseigner `ETORO_API_KEY` et `ETORO_USER_KEY` dans `.env`. Laisser
   `ETORO_ENVIRONMENT=demo` tant que la lecture reelle n'est pas validee.
4. Lancer `trackerbot doctor` pour confirmer que les cles sont lues et
   que le portefeuille distant repond.

Si eToro repond `401`, la cle n'a probablement pas les bons scopes ou le
compte n'est pas verifie. Rien n'est jamais ecrit dans `.env` par le bot ;
en cas de doute, revoquer la cle depuis l'interface eToro et regenerer.

## Utilisation

Toutes les commandes vivent derriere l'executable `trackerbot`.

| Commande                              | Effet                                                              |
| ------------------------------------- | ------------------------------------------------------------------ |
| `trackerbot status`                   | Rapport complet dans la console (positions + metriques + signaux). |
| `trackerbot status --sans-cotations`  | Meme rapport, sans appel a Yahoo Finance.                          |
| `trackerbot status --benchmark SPY`   | Ajoute le beta du portefeuille contre un benchmark (defaut SPY).   |
| `trackerbot status --fondamentaux`    | Ajoute PER, marge, D/E, ROE et score de valorisation par position. |
| `trackerbot watch`                    | Envoie sur Telegram uniquement s'il y a un signal grave.           |
| `trackerbot notify`                   | Envoie le rapport complet sur Telegram.                            |
| `trackerbot notify --avec-veille`     | Idem, en joignant la veille Perplexity du jour.                    |
| `trackerbot veille`                   | Imprime la veille Perplexity du jour.                              |
| `trackerbot doctor`                   | Verifie la configuration et l'acces aux integrations.              |

Ajouter `-v` pour activer les logs DEBUG.

## Regles de surveillance

Les regles vivent dans `src/trackerbot/signals.py`. Elles sont pures et se
declinent en trois niveaux : `info`, `attention`, `alerte`. La commande
`watch` ne notifie que les deux niveaux les plus urgents.

Regles disponibles :

- Stop-loss touche ou approche.
- Take-profit atteint.
- Repli marque depuis le plus haut recent.
- Variation intraday au-dela d'un seuil.
- Croisement de moyennes mobiles.
- RSI en zone de surachat ou de survente.
- Gain ou perte latente sortant de l'ordinaire.

Les seuils sont regroupes dans la dataclasse `Seuils` et peuvent etre
modifies sans toucher aux regles.

## Metriques portefeuille

En plus des indicateurs par position, le rapport affiche un bloc niveau
portefeuille : ratio de Sharpe annualise (taux sans risque par defaut 4 %),
volatilite et rendement annualises, max drawdown, indice de concentration
HHI, poids de la plus grosse ligne, et beta contre un benchmark (SPY par
defaut, modifiable via `--benchmark`). Toutes les formules vivent dans
`src/trackerbot/metrics.py` en fonctions pures.

## Fondamentaux et score de valorisation

`trackerbot status --fondamentaux` recupere via Yahoo (yfinance) les
fondamentaux minimaux : PER, PB, marge nette, ratio dette/capital, ROE,
rendement du dividende, croissance du chiffre d'affaires. Un score
0 a 7 type Graham/Buffett-lite (`valuation.py`) recompense les criteres
remplis : PER < 15, PB < 1.5, marge > 10 %, D/E < 1, ROE > 10 %,
croissance > 5 %, dividende verse. Les seuils sont dans
`SeuilsValorisation` et peuvent etre ajustes sans toucher aux regles.

L'option est opt-in car chaque ticker declenche un appel supplementaire.

## Structure

```
src/trackerbot/
  config.py         lecture des variables d'environnement
  models.py         Position, Cotation, Signal, Niveau
  indicators.py     SMA, RSI, croisements, volatilite (fonctions pures)
  metrics.py        Sharpe, drawdown, HHI, beta (fonctions pures)
  signals.py        regles de surveillance
  fundamentals.py   fondamentaux Yahoo
  valuation.py      score de valorisation (fonction pure)
  market.py         acces cours via yfinance
  research.py       veille Perplexity
  report.py         agregation rapport
  cli.py            commandes trackerbot
  sources/          fichier local, eToro
  notify/           envoi Telegram
dashboard/          app Next.js + shadcn, consomme les donnees du bot
```

## Tests

```
pytest
```

Les tests sont entierement offline : aucun appel reseau. Ils couvrent les
indicateurs, les modeles, les regles, la configuration, le rapport et les
sources de portefeuille.

Verifications complementaires :

```
ruff check .
mypy
```

## Limites

- yfinance est un client non officiel de Yahoo Finance. Il peut casser :
  toute la logique de recuperation vit dans `market.py`, et le rapport
  degrade proprement les positions dont la cotation est absente.
- Les signaux techniques ne sont pas des conseils d'investissement. Le
  bot decrit ce qui se passe sur le marche, il ne dit pas quoi faire.

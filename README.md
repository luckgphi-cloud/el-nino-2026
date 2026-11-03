# El Niño 2026-27 : carte interactive

Web app statique, en français, qui montre l'épisode El Niño 2026-27 semaine par semaine :

- un **globe** (ou une carte plate) des anomalies de température de surface de la mer, depuis janvier 2026 ;
- un curseur temporel avec lecture automatique ;
- l'**indice Niño-3.4** hebdomadaire et le **RONI** officiel de la NOAA, avec le seuil El Niño ;
- la **prévision officielle NOAA**, en probabilités par saison ;
- les **événements extrêmes** GDACS (incendies, inondations, cyclones, sécheresses), avec filtres et fiches ;
- des **zones de tendance** El Niño (option, schématiques) ;
- un panneau **Méthodologie** (observé / prévu / tendance).

Voir [METHODOLOGIE.md](METHODOLOGIE.md) et [SOURCES.md](SOURCES.md).

## Installation

Prérequis : Node.js 20+ et Python 3.11+.

```bash
npm install
python3.11 -m venv .venv
.venv/bin/pip install -r collect/requirements.txt
cp .env.example .env   # facultatif : aucune clé n'est nécessaire
```

## Lancement

```bash
npm run dev       # http://localhost:5173
```

Build de production statique (dossier `dist/`, à servir tel quel) :

```bash
npm run build
npm run preview   # pour le vérifier localement
```

Pour un hébergement sous un sous-chemin (GitHub Pages : `https://<compte>.github.io/<depot>/`), définir
`VITE_BASE_PATH=/<depot>/` avant le build. Sur un VPS servi à la racine, garder `/`.

## Tests

```bash
npm test          # logique du front (Vitest)
npm run test:py   # traitement des données (pytest)
```

## Mise à jour des données

Les données générées sont versionnées dans `public/data/`. Pour les mettre à jour :

```bash
npm run collect                         # toutes les étapes
.venv/bin/python -m collect nino forecast events   # seulement certaines étapes
```

| Étape | Produit | Durée indicative |
|---|---|---|
| `nino` | `nino.json` (Niño-3.4 hebdo, RONI, ONI) | quelques secondes |
| `forecast` | `forecast.json` (probabilités CPC, bulletins, statuts) | ~30 s |
| `sst` | `sst/*.png`, `sst/*.bin`, `sst/index.json` | ~1 min par semaine au premier passage (serveur NOAA limité), puis seulement les nouvelles semaines grâce au cache `.cache/` |
| `events` | `events.json` (alertes orange et rouge) + `events_green.json` (alertes vertes, chargées à la demande) | 10 à 15 min (API lente, milliers de petits feux) |
| `trends` | `trends.json` (zones schématiques) | immédiat |
| `basemap` | `public/basemap/*.geojson` (Natural Earth) | ponctuel, hors collecte par défaut |

La date de départ se change dans `collect/config.py` (`START_DATE`). Une étape en échec ne supprime pas les
données existantes : l'erreur est notée dans `public/data/manifest.json`.

### Automatisation

- `.github/workflows/collect.yml` lance la collecte chaque mardi (et à la demande), puis commite `public/data/`.
- `.github/workflows/deploy.yml` construit et publie sur GitHub Pages à chaque push sur `main` et après chaque collecte.
- Sur un VPS : une tâche cron peut lancer `npm run collect && npm run build`, puis copier `dist/` vers la racine web.

À activer dans le dépôt GitHub : *Settings → Pages → Source : GitHub Actions*.

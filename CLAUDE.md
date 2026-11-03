# CLAUDE.md — El Niño 2026-27, visualisation

Guide pour Claude et tout futur agent. À tenir à jour à chaque étape significative.

## Projet

Web app statique, en français, qui montre l'épisode El Niño 2026-27 sur un globe / une carte :
anomalies de température de surface de la mer (SST) semaine par semaine depuis la date de départ,
courbe de l'indice Niño-3.4 synchronisée, prévision officielle NOAA, événements extrêmes (incendies,
inondations, cyclones, sécheresses) et, en option, zones de tendance El Niño.

Contexte vérifié (bulletins CPC 2026) : La Niña (Advisory) janv.–mars, ENSO-neutre en avril,
El Niño Watch en mai, **El Niño Advisory déclaré le 11 juin 2026**, intensification depuis
(bulletin du 8 oct. 2026 : fort à très fort, probable jusqu'à JFM 2027). Pas de date de fin officielle.

## Règles non négociables

1. **Ne jamais inventer, simuler ou interpoler des données** présentées comme observées. Donnée absente
   → afficher « indisponible » et le signaler. Les fixtures de test vivent dans `collect/tests/fixtures/`
   et `src/**/__fixtures__/`, et leur nom commence par `FIXTURE_`.
2. **Ne jamais attribuer un événement précis à El Niño.** Aucun texte du type « causé par El Niño ».
   Les zones de tendance portent toujours la mention « tendance statistique, pas causalité ».
3. **Distinction visuelle observé / prévision / tendance** partout (styles distincts, étiquettes, source
   et date d'émission pour la prévision).
4. **Aucun secret dans le dépôt ni dans le front.** Variables d'environnement, `.env` ignoré par git,
   `.env.example` documenté. (Aucune source actuelle n'exige de clé.)
5. **Pas de grille brute dans le navigateur** : uniquement des PNG hebdomadaires légers et des JSON agrégés.
6. **Accessibilité** : aucune information portée par la couleur seule (forme + libellé + motif).
7. Crédits et attributions des sources visibles dans l'app.

## Stack et pourquoi

- **Front** : Vite + TypeScript sans framework. Une page, peu d'état : un framework n'apporterait que du poids.
- **Carte** : MapLibre GL JS v6 (projection globe ↔ mercator, open source, sans clé). Fond de carte :
  Natural Earth (domaine public) embarqué, donc aucun fournisseur de tuiles.
- **Graphique** : D3 (modules), pour contrôler seuil, zone de prévision et synchronisation.
- **Collecte** : Python 3.11 (numpy, netCDF4, Pillow, requests). Génère `public/data/`.
- **Tests** : pytest (traitement des données), Vitest (logique front).
- **Hébergement** : GitHub Pages via GitHub Actions, puis VPS (build statique identique, `VITE_BASE_PATH`).

## Structure

```
collect/                 script de collecte (package Python, lancé par `python -m collect`)
  config.py              START_DATE (date de départ, constante unique) + URLs des sources
  nino.py                indices Niño-3.4 hebdo (CPC), RONI, ONI
  forecast.py            probabilités officielles CPC (catégories + intensité)
  sst.py                 anomalies SST hebdo → PNG + validation Niño-3.4
  events.py              événements GDACS
  trends.py              zones de tendance (schématiques, d'après CPC)
  tests/                 pytest ; fixtures dans tests/fixtures/FIXTURE_*
public/data/             données générées (versionnées) consommées par le front
public/basemap/          Natural Earth
src/                     front TypeScript
.github/workflows/       déploiement Pages + collecte planifiée
```

## Commandes

```bash
# installation
npm install
python3.11 -m venv .venv && .venv/bin/pip install -r collect/requirements.txt

npm run dev          # serveur de dev (http://localhost:5173)
npm run build        # build statique dans dist/
npm run preview      # sert dist/
npm test             # Vitest (front)
npm run test:py      # pytest (collecte)
npm run collect      # collecte complète → public/data/
```

## Conventions

- Code et identifiants en anglais, textes d'interface et docs en français.
- Dates ISO `YYYY-MM-DD`, UTC. Semaines alignées sur le CPC : **centrées sur le mercredi** (dim.–sam.).
- Anomalies SST : référence **1991-2020** (même base que les indices CPC).
- Tout fichier de données généré contient `source`, `retrieved_at` et, si pertinent, `issued`.
- Une fonction de parsing = un test sur une fixture `FIXTURE_*` copiée d'une vraie réponse.

## Décisions importantes

- Seuil El Niño officiel : **RONI > +0,5 °C** (moyenne 3 mois, indice relatif, CPC). La ligne de seuil
  est rattachée au RONI, pas à l'indice hebdo classique (qui est nettement plus élevé en 2026).
- Prévision : **barres de probabilités par saison** issues du tableau officiel CPC. Pas de ligne
  « centrale » : la NOAA n'en publie pas et la classe haute (≥ 2 °C) est ouverte.
- Prévisions modèle par modèle IRI : non utilisées (publiées seulement en images).
- Événements : GDACS seul (EONET relaie surtout GDACS). Par défaut Orange + Rouge ; Vert en option.
  Critère identique pour le monde entier.
- Incendies : pas de NASA FIRMS (refusé par l'utilisateur, clé requise).
- Zones de tendance : option A, zones **schématiques** tracées d'après la carte et le texte CPC
  (IRI Data Library exige un compte). Toujours marquées approximatives.
- Hébergement : GitHub Pages d'abord, puis VPS de l'utilisateur.

## État d'avancement

- [x] Plan validé (2026-11-03)
- [x] 0. Dépôt, CLAUDE.md, squelette
- [x] 1. Collecte Niño / RONI / prévision + statuts mensuels + tests
- [x] 2. PNG SST hebdo + validation contre Niño-3.4 CPC (écart ≈ 0,0–0,1 °C)
- [x] 3. Globe/carte, couche SST, curseur, lecture, légende, lecture au survol
- [x] 4. Courbe synchronisée + prévision (barres de probabilités) + bandeau de statut CPC
- [x] 5. Événements GDACS (filtres type/niveau/période, fiches)
- [x] 6. Zones de tendance (DJF/JJA), Méthodologie, crédits
- [x] 7. Vérification navigateur (desktop, mobile, build sous sous-chemin), rapport final (RAPPORT.md)
- [x] Publié : dépôt public https://github.com/luckgphi-cloud/el-nino-2026 ,
      site https://luckgphi-cloud.github.io/el-nino-2026/ (Pages via Actions, déployé le 2026-11-03)
- [x] Collecte (collect.yml) exécutée avec succès sur GitHub le 2026-11-03 (~13 min, résultats identiques au local)
- [ ] Actions en Node 20 dépréciées (avertissements) : monter les versions des actions
- [ ] Suite : hébergement sur le VPS de l'utilisateur

## Pièges connus

- MapLibre v6 + Vite : `optimizeDeps.exclude: ["maplibre-gl"]` et `setWorkerUrl(...?url)` sinon « Worker failed to load ».
- PSL THREDDS : 429 si requêtes rapprochées → collecte SST séquentielle, pause 2 s, cache `.cache/sst/*.npy`.
  OPeNDAP via netCDF4 échoue (certificat SSL de libcurl) → on utilise le service NCSS + `requests`.
- GDACS : User-Agent ASCII obligatoire (403 sinon) ; « ; » non encodés dans `alertlevel` (400 sinon).
- Page CPC « strengths » : ancien « Issued … » en commentaire HTML → retirer les commentaires avant parsing.
- Vite dev + collecte en cours : `server.watch.ignored` exclut public/data (sinon rechargement en boucle) ; après
  une collecte, redémarrer le serveur de dev pour qu'il serve les nouveaux fichiers.
- Popups MapLibre : la feuille de style MapLibre est chargée après la nôtre → sélecteurs `.event-popup …`.
- Les commandes `cd` dans Bash changent le répertoire de session : toujours revenir à la racine du projet.

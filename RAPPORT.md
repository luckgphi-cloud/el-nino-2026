# Rapport final : V1 (3 novembre 2026)

## Ce qui fonctionne

- **Globe et carte plate** (MapLibre GL v6, bouton Globe / Carte), centrés à l'ouverture sur le Pacifique
  équatorial, sur la semaine la plus récente.
- **Anomalies de température de surface**, une image par semaine CPC (dim.–sam.) depuis la semaine du
  28 déc. 2025 au 3 janv. 2026 jusqu'à la dernière semaine complète. Base 1991-2020, palette divergente
  accessible, légende graduée, lecture de la valeur au survol (maille 1°). Les semaines récentes sont
  marquées « provisoires ».
- **Curseur temporel et lecture automatique** (play/pause, 4 vitesses, flèches du clavier, barre d'espace).
  Les images sont préchargées pour une lecture sans saccade.
- **Courbe** synchronisée avec le curseur (cliquable) :
  - Niño-3.4 hebdomadaire ;
  - RONI (valeurs provisoires creuses) ;
  - seuils officiels (RONI > +0,5 °C / < −0,5 °C) ;
  - bandeau du statut officiel NOAA mois par mois ;
  - prévision NOAA CPC en probabilités par classe et par saison, hachurée et pointillée, avec sa date d'émission.
- **Événements GDACS** : incendies, inondations, cyclones, sécheresses. Chacun a une couleur et une forme
  distinctes. Ils sont classés selon leur **intensité physique** (vent maximal, surface brûlée, surface touchée), avec
  les mêmes seuils partout dans le monde, et non selon l'alerte GDACS, qui dépend des moyens du pays. Rendu : creux
  (modéré), plein (fort), grand avec halo blanc (extrême). Filtres par type, par intensité et par période (semaine
  ou cumul). Fiche au clic : intensité et mesure, dates, lieu, alerte GDACS en information secondaire, lien vers le
  rapport GDACS, avec la mention qu'aucune cause n'est attribuée. Sur la dernière semaine, les événements vont jusqu'à
  la date de collecte.
- **Deux fonds de carte** : terres gris foncé sous les températures ; sans les températures, océan bleu marine et
  terres claires avec côtes soulignées.
- **Zones de tendance** El Niño (déc.–févr. / juin–août), désactivées par défaut, avec motifs hachurés ou
  pointillés et la mention « tendance statistique, pas causalité ».
- **Panneaux Méthodologie et Sources/crédits** dans l'app, plus `METHODOLOGIE.md` et `SOURCES.md`.
- **Collecte** autonome (`npm run collect`), 33 tests pytest et 9 tests Vitest, build statique (`npm run build`,
  vérifié servi sous un sous-chemin comme sur GitHub Pages), workflows GitHub (collecte hebdomadaire et déploiement Pages).

## Jeu de données livré (collecte du 3 novembre 2026)

| Fichier | Contenu |
|---|---|
| `sst/` | 44 semaines (centrées du 31 déc. 2025 au 28 oct. 2026), 4,5 Mo ; dernier jour observé : 1er nov. 2026 |
| `nino.json` | 44 valeurs hebdomadaires (dernière : +3,4 °C, semaine du 28 oct.) ; RONI de NDJ 2025 à JAS 2026 (+1,69) |
| `forecast.json` | Probabilités CPC émises en octobre 2026 (SON 2026 → MJJ 2027) ; 10 bulletins mensuels (janv.–oct.) |
| `events.json` | 349 événements d'intensité forte ou extrême : 43 cyclones, 174 incendies, 120 inondations, 12 sécheresses |
| `events_moderate.json` | 7 276 événements modérés (dont 6 757 feux), chargés seulement si on les active |
| `trends.json` | 24 zones schématiques (16 en déc.–févr., 8 en juin–août) |

## Ce qui n'a pas pu être fait, ou a été écarté

- **Prévisions modèle par modèle (IRI)** : uniquement en images ; serveur de données réservé au réseau du campus.
- **Zones de tendance en données « réelles »** : l'IRI Data Library exige désormais un compte. Les zones sont donc
  tracées à la main d'après la carte NOAA (schématiques, quelques degrés d'imprécision).
- **NASA FIRMS** (foyers d'incendie) : clé requise, écarté à la demande de l'utilisateur. Les incendies viennent de GDACS.
- **Carte de prévision** : hors V1, comme prévu.
- **Trajectoires des cyclones** : V1 = un point par événement (position fournie par GDACS), pas de trace.
- **Licence GDACS** : aucune licence de réutilisation explicite. L'app cite la source et l'avertissement ;
  à clarifier avec GDACS avant un usage public large.

## Limites connues

- Résolution de la carte : 0,5° (une maille sur deux de la grille OISST à 0,25°). Suffisant à l'échelle du globe,
  pixelisé si l'on zoome fortement.
- Délai : la carte s'arrête à la dernière semaine complète disponible chez NOAA PSL (environ 2 jours de retard),
  et les 15 derniers jours restent révisables.
- Le RONI n'est publié qu'une fois par mois : la courbe RONI s'arrête à la dernière saison publiée (juil.–sept. 2026).
- Les alertes GDACS sont en partie automatiques. Leur position est un point représentatif (centroïde).
- Surfaces d'inondation : zone *touchée* estimée par satellite et par modèle, pas la surface en eau. Elle peut couvrir
  un bassin entier pour les grands événements. Les seuils des feux, des sécheresses et des inondations sont des
  choix documentés (répartition 2026), pas des normes officielles ; seuls ceux des cyclones (Saffir-Simpson) le sont.
- Les sécheresses GDACS peuvent avoir commencé bien avant 2026 (critère : actives pendant la période).
- La collecte SST complète a pris environ 30 min au premier passage, à cause de la limitation de débit du serveur
  NOAA. Les passages suivants ne téléchargent que les nouvelles semaines.

## Comment les données affichées ont été vérifiées

1. **Contre l'indice officiel de la NOAA** : la collecte recalcule, pour chaque semaine, la moyenne de nos
   anomalies sur la boîte Niño-3.4 et la compare à l'indice hebdomadaire CPC. **Résultat sur les 44 semaines
   (28 déc. 2025 → 31 oct. 2026) : écart moyen 0,037 °C, écart maximal 0,11 °C** (semaine du 21 janv. 2026),
   alors que le CPC publie ses valeurs arrondies au dixième. Ce contrôle confirme la base 1991-2020, la grille,
   le découpage des semaines et la position de la boîte (`public/data/sst/index.json`).
2. **Analyseurs testés sur de vraies réponses** des sources (fichiers `FIXTURE_*`) : les valeurs attendues ont
   été relevées à la main dans ces fichiers (par ex. Niño-3.4 = +3,4 °C la semaine du 28 oct. 2026 ;
   RONI JAS 2026 = 1,69 ; probabilités MJJ 2027 = 13/70/17 %).
3. **Contexte ENSO vérifié dans les 10 bulletins mensuels 2026 de la NOAA** : La Niña de janvier à mars,
   veille El Niño en mars, fin de La Niña en avril, veille El Niño en mai, El Niño déclaré le 11 juin 2026,
   statut maintenu jusqu'au bulletin du 8 octobre.
4. **Garde-fous** : chaque ligne de probabilités doit totaliser 98 à 102 %, une semaine SST n'est produite que
   si les 7 jours sont disponibles, et une étape en échec garde les données précédentes et le signale dans `manifest.json`.
5. **Contrôle visuel** dans le navigateur : desktop et mobile (375 px).

# Méthodologie

L'application distingue trois natures d'information. Chacune a son propre style visuel et ses propres étiquettes.

## 1. Observé

**Anomalies de température de surface (carte).** Pour chaque semaine dimanche–samedi (convention NOAA CPC, semaine
« centrée » sur le mercredi) :

1. on télécharge les 7 champs quotidiens NOAA OISST v2.1, à 0,5° (une maille sur deux de la grille à 0,25°) ;
2. on soustrait, jour par jour, la climatologie quotidienne 1991-2020 (le 29 février prend la valeur du 28) ;
3. on fait la moyenne sur 7 jours. Une maille est laissée vide si l'un des jours manque (bord de banquise) ;
4. on classe la valeur dans des classes de 0,5 °C, de −4 à +4 °C (palette ColorBrewer RdBu, lisible en cas de
   daltonisme rouge-vert), et on reprojette en Web Mercator (image PNG de 720 × 720) ;
5. on produit aussi une grille de lecture à 1° (moyenne de 2 × 2 mailles), stockée en entiers (0,1 °C), pour
   afficher la valeur sous le curseur.

Les semaines dont le dernier jour date de moins de 15 jours sont marquées **provisoires** : la NOAA peut encore les réviser.

**Indice Niño-3.4 hebdomadaire.** Valeur publiée par la NOAA CPC, sans retraitement.

**RONI.** C'est l'indice officiel avec lequel la NOAA déclare El Niño : la moyenne sur 3 mois de l'anomalie Niño-3.4,
moins la moyenne des anomalies tropicales (20°N–20°S), avec une variance ramenée à celle de l'indice classique.
**Seuil El Niño : RONI > +0,5 °C.** La ligne de seuil du graphique est rattachée à cet indice. L'indice
hebdomadaire « brut » est nettement plus élevé en 2026, pour deux raisons : il n'est pas moyenné sur 3 mois, et
il n'est pas corrigé du réchauffement de l'ensemble des tropiques. Le comparer directement au seuil serait trompeur.

**Statut officiel.** Le bandeau en haut du graphique reprend le statut du système d'alerte ENSO de la NOAA à
chaque bulletin mensuel : La Niña, veille El Niño, El Niño…

**Événements extrêmes.** Inondations, cyclones tropicaux, sécheresses et feux de forêt recensés par GDACS.
Ils sont classés selon leur **intensité physique**, avec les mêmes seuils partout dans le monde, et **pas** selon
l'alerte GDACS. Cette alerte (vert / orange / rouge) mesure le besoin probable d'aide internationale : elle intègre la
population exposée et la capacité du pays à faire face. Une catastrophe majeure dans un pays riche peut donc y rester
« verte ». Elle n'est plus qu'une information secondaire dans la fiche.

| Type | Mesure physique (source GDACS) | Forte à partir de | Extrême à partir de |
|---|---|---|---|
| Cyclone | Vent maximal soutenu | 119 km/h (catégorie 1 Saffir-Simpson) | 178 km/h (catégorie 3, « ouragan majeur ») |
| Incendie | Surface brûlée | 40 000 ha | 100 000 ha |
| Sécheresse | Surface touchée (sécheresse agricole) | 200 000 km² | 1 000 000 km² |
| Inondation | Surface de la zone touchée, estimée (polygone « Affected area » de GDACS, calculé en km²) | 10 000 km² | 100 000 km² |

- Les seuils des cyclones suivent l'échelle officielle de Saffir-Simpson. Les autres sont des valeurs rondes choisies
  d'après la répartition des événements de 2026 : GDACS ne recense déjà que de grands feux (médiane d'environ 7 500 ha),
  et la surface des inondations est très étalée (médiane d'environ 190 km² ; un cinquième au-delà de
  10 000 km², 7 % au-delà de 100 000 km²). Ces choix sont réglables dans `collect/events.py`.
- **Limite** : la surface d'une inondation est la zone *touchée* estimée par satellite et par modèle (GloFAS, DFO),
  pas la surface en eau ; pour les grands événements, elle peut couvrir un bassin entier. Elle est moins précise
  qu'une vitesse de vent. Quand GDACS ne fournit pas de polygone, l'événement est affiché « non mesuré » (contour pointillé).
- Rendu : modérée = petit symbole creux ; forte = symbole moyen plein ; extrême = grand symbole plein avec halo blanc.
  Par défaut, l'app montre les événements forts, extrêmes et non mesurés ; les modérés sont en option.
- Sur la dernière semaine, les événements sont affichés jusqu'à la date de collecte, alors que la carte des
  températures s'arrête à la dernière semaine complète publiée par la NOAA.
- Aucune sélection n'est faite selon un lien supposé avec El Niño.

## 2. Prévu

La NOAA CPC publie chaque mois, pour 9 saisons de 3 mois, la probabilité que le RONI tombe dans chacune des
9 classes d'intensité (de « ≤ −2 °C » à « ≥ +2 °C »), ainsi que les probabilités El Niño / neutre / La Niña.

Le graphique montre ces probabilités telles quelles : pour chaque saison, des rectangles hachurés et à bord
pointillé couvrent chaque classe, avec une opacité proportionnelle à la probabilité. La date d'émission et la
source sont indiquées. **Nous ne traçons pas de ligne de prévision** : la NOAA n'en publie pas, et la classe
supérieure est ouverte (≥ +2 °C), ce qui interdit de calculer une médiane sans rien inventer.

Il n'y a pas de carte de prévision en V1. Les prévisions modèle par modèle de l'IRI ne sont disponibles qu'en images.

## 3. Tendance

Les zones de tendance (désactivées par défaut) reprennent la carte « Warm Episode Relationships » de la NOAA CPC.
Elles montrent où les épisodes El Niño **passés** se sont statistiquement accompagnés de conditions plus humides,
plus sèches, plus chaudes ou plus fraîches, en décembre–février et en juin–août.

- Les contours sont **schématiques**, tracés à la main d'après la carte NOAA : à quelques degrés près.
- Une tendance n'est **ni une prévision ni une causalité** : de nombreux épisodes El Niño n'ont pas produit ces
  anomalies dans toutes les zones.

## 4. Limites de l'attribution causale

- **Aucun événement affiché n'est attribué à El Niño.** La fiche de chaque événement le rappelle.
- Un événement extrême a toujours plusieurs causes : météo du moment, autres modes de variabilité (dipôle de
  l'océan Indien, oscillation de Madden-Julian…), réchauffement climatique, vulnérabilité et aménagement du territoire.
- Établir le rôle d'El Niño dans un événement précis demande une étude d'attribution dédiée (modélisation,
  comparaison à un climat sans le facteur étudié). Superposer un événement et une anomalie océanique sur une carte
  montre une **coïncidence dans le temps**, pas un lien de cause à effet.
- Même une zone de tendance qui coïncide avec un événement ne prouve rien pour cet événement.

## 5. Vérification des données

- **Carte contre indice officiel.** Pour chaque semaine, la collecte calcule la moyenne pondérée (cos lat) de nos
  anomalies sur la boîte Niño-3.4 (5°S–5°N, 170°O–120°O) et la compare à l'indice hebdomadaire de la NOAA. Le
  résultat (écart moyen et maximal) est dans `public/data/sst/index.json` et s'affiche dans le panneau Méthodologie.
- **Analyseurs testés sur de vraies réponses** : les fichiers `collect/tests/fixtures/FIXTURE_*` sont des copies
  de réponses réelles des sources, et les valeurs attendues dans les tests ont été relevées à la main dans ces fichiers.
- **Cohérence de la prévision** : chaque ligne de probabilités doit totaliser 98 à 102 %, sinon la collecte échoue.
- **Échec d'une source** : la collecte n'écrase pas les données précédentes, consigne l'erreur dans
  `manifest.json`, et l'interface affiche « indisponible ».

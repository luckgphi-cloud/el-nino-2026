# Sources de données

Chaque source a été testée par un appel réel le 3 novembre 2026. Aucune n'exige d'inscription ni de clé API.

## 1. Températures de surface de la mer : NOAA OISST v2.1

| | |
|---|---|
| Produit | NOAA/NCEI Daily Optimum Interpolation SST v2.1 (AVHRR), 0,25°, quotidien |
| Accès | NOAA PSL, service THREDDS « NetCDF Subset » : `https://psl.noaa.gov/thredds/ncss/grid/Datasets/noaa.oisst.v2.highres/sst.day.mean.{année}.nc` |
| Climatologie | `sst.day.mean.ltm.1991-2020.nc` (même serveur) |
| Page | https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.highres.html |
| Licence | Données du gouvernement des États-Unis, domaine public. Citation demandée : Huang et al. (2021), J. Climate, doi:10.1175/JCLI-D-20-0166.1 ; Reynolds et al. (2007). |
| Fréquence | Quotidienne, délai d'environ 1 à 2 jours. Les 15 derniers jours sont préliminaires et peuvent être révisés. |
| Limites | Le serveur renvoie **429 Too Many Requests** au-delà de quelques requêtes rapprochées : la collecte est séquentielle, avec une pause de 2 s, et respecte `Retry-After`. Environ 7 Mo par semaine téléchargée à 0,5°. |
| Remarque | Les fichiers d'anomalies déjà calculées par PSL utilisent la base 1971-2000. Nous recalculons l'anomalie sur la base 1991-2020 pour rester cohérents avec les indices CPC. |

## 2. Indice Niño-3.4 hebdomadaire : NOAA CPC

| | |
|---|---|
| URL | https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for |
| Contenu | SST et anomalies hebdomadaires (semaines centrées sur le mercredi) pour Niño 1+2, 3, 3.4 et 4, base 1991-2020, OISST v2.1 |
| Licence | Domaine public (NOAA) |
| Fréquence | Hebdomadaire (lundi) |
| Limites | Format texte à colonnes fixes ; les valeurs négatives peuvent être collées à la précédente (`20.6-0.1`). |

## 3. RONI (indice officiel) et ONI : NOAA CPC

| | |
|---|---|
| URL | https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt · https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt |
| Définition | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/ : moyenne sur 3 mois de l'anomalie Niño-3.4 (ERSSTv6), moins la moyenne tropicale 20°N-20°S, base 1991-2020. **Seuils : El Niño > +0,5 °C ; La Niña < −0,5 °C.** |
| Licence | Domaine public (NOAA) |
| Fréquence | Mensuelle (avant le 5 du mois) |
| Limites | Les deux dernières valeurs peuvent changer pendant 2 mois : elles sont marquées « provisoires ». |

## 4. Prévision officielle et bulletins : NOAA CPC

| | |
|---|---|
| Probabilités par catégorie | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/probabilities/ |
| Probabilités par intensité | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/strengths/ |
| Bulletin courant | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml |
| Bulletins archivés | `https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_disc_{mois}{année}/ensodisc.html` (statut officiel mois par mois) |
| Licence | Domaine public (NOAA) |
| Fréquence | Mensuelle (2e jeudi du mois). Prochain bulletin : 12 novembre 2026. |
| Limites | Pas de fichier CSV : la collecte lit les tableaux HTML. La page « strengths » contient un ancien libellé « Issued … » en commentaire HTML, que la collecte ignore. |

**Non utilisé** : panache de modèles de l'IRI (Columbia), https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/. Les valeurs ne sont publiées que sous forme d'images SVG, et le serveur de données `ensoforecast.iri.columbia.edu/data` répond « Campus network only » (403).

## 5. Événements extrêmes : GDACS

| | |
|---|---|
| API | `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist={FL,TC,DR,WF}&fromdate=…&todate=…&alertlevel=Green;Orange;Red&pagenumber=N` |
| Types retenus | FL (inondations), TC (cyclones tropicaux), DR (sécheresses), WF (feux de forêt). Exclus : séismes, tsunamis, volcans. |
| Conditions | https://www.gdacs.org/About/termofuse.aspx (PDF de mars 2025). Données fournies « en l'état », sans garantie, et qui ne remplacent pas les alertes officielles nationales. **Aucune licence de réutilisation explicite** : l'app cite la source et reproduit l'avertissement. |
| Intensité | Lue dans `severitydata` (vent en km/h, surface brûlée en ha, surface de sécheresse en km²). Pour les inondations, qui n'ont pas de mesure dans la liste, la surface est calculée à partir du polygone « Affected area » de `https://www.gdacs.org/gdacsapi/api/polygons/getgeometry?eventtype=FL&eventid=…&episodeid=…` (un appel par inondation, environ 3 s, mis en cache dans `.cache/gdacs_fl/`). |
| Fréquence | Temps quasi réel |
| Limites | Pages de 100 résultats ; réponses lentes (jusqu'à environ 20 s par page). Les « ; » ne doivent **pas** être encodés (`%3B` → 400). Le pare-feu renvoie **403** si le User-Agent contient des caractères non ASCII. Les alertes cyclones sont automatiques (sans relecture humaine). Les sécheresses peuvent avoir commencé avant 2026. |

**Non utilisé** : NASA EONET. Sur 50 événements récents testés, 42 venaient de GDACS : la source ferait doublon. NASA FIRMS (foyers d'incendie) exige une clé et a été écarté.

## 6. Zones de tendance El Niño : NOAA CPC (tracé schématique)

| | |
|---|---|
| Page | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensocycle/elninosfc.shtml |
| Carte | https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/impacts/warm.gif (« Warm Episode Relationships », déc.–févr. et juin–août), d'après Ropelewski & Halpert (1987) et Halpert & Ropelewski (1992) |
| Licence | Domaine public (NOAA) |
| Traitement | Contours **tracés à la main** dans `collect/trends.py` d'après la carte et le texte : approximatifs à quelques degrés près. |
| Alternative écartée | IRI Data Library (`SOURCES/.IRI/.Analyses/.ENSO-Impacts/`) : données en grille, mais la connexion à un compte est désormais obligatoire. |

## 7. Fond de carte : Natural Earth

| | |
|---|---|
| URL | https://github.com/nvkelso/natural-earth-vector (ne_50m_land, ne_110m_admin_0_boundary_lines_land) |
| Licence | Domaine public |
| Traitement | Propriétés retirées, coordonnées arrondies à 0,01° (`python -m collect basemap`) |

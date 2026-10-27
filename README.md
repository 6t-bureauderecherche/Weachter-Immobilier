# Waechter Immobilier — Aide à la décision

## Explorateur des indicateurs du canton de Genève

L’application affiche les indicateurs territoriaux agrégés par parcelle de mensuration. La carte Leaflet permet de choisir la couche `TOT` ou `PRIVE`. Les parcelles sont colorées selon `Typo_SUM_majority` (classes 0 à 12) et restent cliquables à tous les niveaux de zoom. Le panneau de droite présente la classe globale, les quatre indicateurs du graphique radar, la commune, le numéro de parcelle et la surface.

Le fond de carte est OpenStreetMap. Les GeoPackages d’origine sont conservés dans `data/`; les GeoParquet utilisés par l’application sont également dans ce dossier.

Pour convertir un GeoPackage en GeoParquet :

```bash
python data/convert_gpkg_to_parquet.py --input 'data/Parcelles_classées_TOT.gpkg'
python data/convert_gpkg_to_parquet.py --input 'data/Parcelles_classées_PRIVE.gpkg'
python data/build_parcel_geojson.py
```

Le script détecte automatiquement l’unique couche du GeoPackage. Pour les fichiers qui en contiennent plusieurs, ajoutez `--layer NOM_DE_COUCHE`. Le chemin de sortie reprend par défaut le nom du fichier source avec l’extension `.parquet`.

## Préparer et lancer l’application

Depuis la racine du projet :

```bash
pip install -r requirements.txt
streamlit run app.py
```

Leaflet et les tuiles du fond OpenStreetMap sont chargés depuis Internet. Les GeoJSON compressés de la carte sont générés dans `static/` avec une simplification légère des géométries ; le GeoParquet conserve les données attributaires complètes.

## Ancienne version

La version avec les mailles de 25 m et les tuiles vectorielles est sauvegardée dans `backups/current_version/`.

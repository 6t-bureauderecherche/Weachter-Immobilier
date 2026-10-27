# Waechter Immobilier — Aide à la décision

## Explorateur des indicateurs du canton de Genève

L’application utilise le GeoParquet pour les attributs et des tuiles
vectorielles pour la carte Leaflet. Le navigateur ne demande que les tuiles
visibles lorsqu’on déplace ou zoome la carte ; un clic envoie seulement
l’identifiant de la maille à Streamlit. Le fond de carte est OpenStreetMap et
les mailles sont colorées selon `Typo_SUM`. Chaque maille visible est cliquable.

Le GeoPackage d’origine reste dans `data/`. Pour (re)générer le Parquet après
avoir installé les dépendances, lancez depuis la racine du projet :

```bash
python data/convert_gpkg_to_parquet.py
```

Le script crée `data/GridXAll_Indic_FZ26_10_26.parquet`. Il accepte aussi
`--input`, `--output` et `--layer` pour utiliser d’autres chemins ou couches.

Le jeu de données contient 397 259 mailles en EPSG:2056. Le Parquet conserve
les attributs ; les tuiles de carte sont produites une fois dans
`static/tiles/`. Aux niveaux de zoom les plus éloignés, Tippecanoe réduit le
nombre de mailles affichées pour garder les tuiles légères ; chaque maille
restant visible conserve son propre identifiant et reste sélectionnable.

Le bloc de gauche contient un texte éditable directement dans `app.py` et un
emplacement provisoire pour un logo. Pour utiliser un logo, placez son fichier
dans le projet (par exemple `assets/logo.png`) puis remplacez le bloc « Logo »
par `st.image(...)`.

## Préparer et lancer l'application

Tippecanoe est nécessaire pour construire les tuiles (sur macOS, installez-le
avec Homebrew). Depuis la racine du projet :

```bash
brew install tippecanoe
pip install -r requirements.txt
python data/build_vector_tiles.py
streamlit run app.py
```

Le script crée `static/tiles/{z}/{x}/{y}.pbf`. La configuration Streamlit
active le service de ces fichiers statiques. Pour publier l’application,
incluez le dossier `static/tiles/` dans le dépôt avec le code.

 ## Github

 Pour créer le dépôt local puis le relier à un dépôt GitHub vide :

 ```bash
git init
git add app.py README.md requirements.txt data/ static/ .streamlit/config.toml
git commit -m "Initialise l’application Streamlit des indices communaux"
git branch -M main
git remote add origin URL_DU_DEPOT_GITHUB
git push -u origin main
```

Ne pas ajouter de jeton GitHub ou de secret au dépôt. Pour un déploiement Streamlit Community Cloud, choisir le dépôt, la branche `main` et `app.py` comme fichier principal.

## Mettre à jour le projet sur Github

Toujours enregistrer ses modifications localement, puis push le projet sur Github pour éviter des problèmes de branching

```bash
git status
git add app.py README.md etc
git commit -m "Décris brièvement les modifications"
git push
```

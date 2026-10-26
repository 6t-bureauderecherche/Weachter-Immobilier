# Waechter Immobilier — Aide à la décision

## Explorateur des indicateurs du canton de Genève

L’application Streamlit affiche la couche `gridxindicateurs_fz26_10_26` du
GeoPackage `data/GridXAll_Indic_FZ26_10_26.gpkg`. La carte Leaflet utilise un
fond OpenStreetMap et colore les mailles selon `Typo_SUM`. Un clic sur une
maille affiche à droite les cinq indicateurs disponibles.

Le GeoPackage contient 397 259 mailles en EPSG:2056. Les géométries sont
reprojetées en WGS84 en mémoire et mises en cache pendant l’exécution. Le cache
est invalidé lorsque le fichier GeoPackage est modifié. Le premier démarrage
peut donc prendre un peu de temps.

Le bloc de gauche contient un texte éditable directement dans `app.py` et un
emplacement provisoire pour un logo. Pour utiliser un logo, placez son fichier
dans le projet (par exemple `assets/logo.png`) puis remplacez le bloc « Logo »
par `st.image(...)`.

## Lancer l'application
 ```bash
pip install -r requirements.txt
streamlit run app.py
 ```

 ## Github

 Pour créer le dépôt local puis le relier à un dépôt GitHub vide :

 ```bash
git init
git add app.py README.md requirements.txt data/
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

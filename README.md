# Weachter immobilier -  Aide à la décision

## Lancer l'application
 ```bash
 conda activate web-app
 streamlit run app.py
 ```

 ## Github

 Pour créer le dépôt local puis le relier à un dépôt GitHub vide :

 ```bash
git init
git add app.py scripts README.md requirements.txt .gitignore data/processed/
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

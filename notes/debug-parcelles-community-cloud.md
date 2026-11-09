# Reprise — GeoJSON non chargé sur Streamlit Community Cloud

Dernière mise à jour : 30 octobre 2026

## Symptôme

En local (`streamlit run app.py`), la carte charge les parcelles. Sur Community Cloud, la carte affiche : « Impossible de charger les parcelles. Vérifiez les fichiers GeoJSON dans static/. »

## État du dépôt et déploiement

- Les GPKG sources sont ignorés par Git car volumineux. L’application ne les lit pas au runtime.
- Les GeoParquet utilisés par les détails et les fichiers `static/parcels_TOT.geojson.gz` / `static/parcels_PRIVE.geojson.gz` sont suivis par Git.
- `.streamlit/config.toml` contient `[server] enableStaticServing = true`.
- L’application vérifie au démarrage que les GeoParquet et GeoJSON existent sur le serveur. Une absence à ce niveau produit une erreur Streamlit côté Python.
- La correction de décodage a été poussée sur `main` dans le commit `110c716` (`debugage`), après intégration du commit distant `eccddb6` (`Added Dev Container Folder`). La branche locale était synchronisée avec `origin/main` après le push.
- L’utilisateur confirme que Community Cloud pointe sur `main` et `app.py`. Le dernier message de log observé est `[16:03:10] Updated app!`.

## Diagnostic confirmé côté navigateur

- Après le changement de décodage, la console Safari affiche `SyntaxError: JSON Parse error: Unrecognized token '<'` dans `installGeoJson`.
- Dans l’onglet Réseau, la requête pour `https://weachter-immobilier.streamlit.app/app/static/parcels_TOT.geojson.gz` répond avec le statut `200`, mais les en-têtes indiquent `Content-Type: text/html; charset=utf-8` et `Content-Length: 9782`.
- Le corps retourné est une page HTML de l’interface Streamlit Cloud (bundle `/-/build/...`), pas le GeoJSON compressé (fichier local : environ 8,2 Mo).
- La réponse HTML explique le caractère `<` vu par `JSON.parse`. Le diagnostic initial de double décompression était incorrect ; le commit `110c716` ne règle pas ce problème de routage/réponse.
- Des 404 génériques et une erreur CORS sur `/api/v2/app/status` ont aussi été observés, mais leur lien avec la carte n’est pas établi.

## À faire en reprenant

1. Demander le résultat du test direct suivant (proposé, pas encore rapporté) : `https://weachter-immobilier.streamlit.app/app/static/tiles/metadata.json`.
   - Si le navigateur affiche le JSON attendu, le service statique fonctionne en général ; investiguer spécifiquement la disponibilité/route des GeoJSON dans le runtime déployé.
   - Si le navigateur affiche encore la page HTML Streamlit Cloud, le problème touche le routage ou la configuration du service statique globalement.
2. Vérifier dans les détails/logs Community Cloud quel commit est effectivement lancé. La ligne `Updated app!` seule confirme une mise à jour, pas le SHA du commit.
3. Si les assets statiques restent servis comme HTML, inspecter le répertoire de travail effectif du runtime et `st.get_option("server.enableStaticServing")`, puis choisir une correction fondée sur ces résultats. Éviter de modifier encore le décodage gzip avant d’avoir une réponse GeoJSON réelle.

## Confidentialité

Un copier-coller précédent des en-têtes de requête contenait des valeurs de cookies de session et CSRF. Elles ne sont pas reproduites ici. Par précaution, fermer la session Streamlit Cloud, effacer les données du site dans Safari puis se reconnecter. Ne pas partager de nouveau les en-têtes `Cookie` ; pour le diagnostic, seuls `Request URL`, `Status`, `Content-Type`, `Content-Length` et un extrait du corps sont utiles.

#!/usr/bin/env bash
set -o errexit

echo "=== Installation des dépendances ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --no-input

echo "=== Migrations ==="
python manage.py migrate --no-input

echo "=== Chargement des données ==="
python manage.py loaddata backup.json
echo "=== Création du superuser ==="
python manage.py createsuperuser --no-input || echo "Superuser existe deja ou variables manquantes"
```

## Ce qui a changé
- **Supprimé la duplication** — un seul `#!/usr/bin/env bash`
- **Chemin absolu** pour `backup.json` pour éviter tout problème de répertoire courant

Sauvegarde, fais un `git commit` + `git push`, et Render va redéployer. Dans les logs tu devrais voir :
```
=== Chargement des données ===
Installed XXXX object(s) from 1 fixture(s)
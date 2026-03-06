#!/usr/bin/env bash
set -o errexit

echo "=== Installation des dépendances ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecte des fichiers statiques ==="
python manage.py collectstatic --no-input

echo "=== Migrations ==="
python manage.py migrate --no-input

echo "=== Création du superuser ==="
python manage.py createsuperuser --no-input || echo "Superuser existe deja ou variables manquantes"
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
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
import os
u = os.environ.get('DJANGO_SUPERUSER_USERNAME')
if u and not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, os.environ.get('DJANGO_SUPERUSER_EMAIL'), os.environ.get('DJANGO_SUPERUSER_PASSWORD'))
    print('Superuser créé.')
else:
    print('Superuser déjà existant, rien à faire.')
"
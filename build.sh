#!/usr/bin/env bash
set -o errexit
set -o pipefail

echo "=== Installation ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecte statique ==="
python manage.py collectstatic --no-input

echo "=== Migrations ==="
python manage.py migrate --no-input

echo "=== Superuser check ==="
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@exemple.com',
        password='AdminMotDePasse123!'
    )
    print('✅ Superuser admin créé')
else:
    print('ℹ️  Superuser existe déjà')
"
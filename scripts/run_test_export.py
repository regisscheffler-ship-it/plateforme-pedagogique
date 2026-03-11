import os
import django
import sys
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plateforme.settings')
django.setup()

from django.test.client import Client
from django.contrib.auth.models import User

c = Client()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('devadmin', 'dev@example.com', 'devpass')

logged = c.login(username='devadmin', password='devpass')
print('Logged in:', logged)
resp = c.get('/archives/export/?annee=2024-2025&categorie=all')
print('Status', resp.status_code, 'Content-Type:', resp.get('Content-Type'), 'Length:', len(resp.content))
open('test_archives_internal.zip', 'wb').write(resp.content)
print('Wrote test_archives_internal.zip')

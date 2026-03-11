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
from django.core.files import File as DjangoFile
from core.models import Archive

c = Client()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('devadmin', 'dev@example.com', 'devpass')

logged = c.login(username='devadmin', password='devpass')
print('Logged in:', logged)
user = User.objects.filter(is_superuser=True).first()

# Ensure at least one Archive exists for the year to produce a ZIP
if not Archive.objects.filter(actif=True, annee_scolaire='2024-2025').exists():
    dummy_path = Path(__file__).resolve().parents[1] / 'scripts' / 'dummy_export.txt'
    dummy_path.write_bytes(b'Test archive file contents')
    with open(dummy_path, 'rb') as fh:
        af = DjangoFile(fh, name='dummy_export.txt')
        Archive.objects.create(titre='Export test', description='test fiche_contrat_id:1', categorie='evaluations', annee_scolaire='2024-2025', createur=user, fichier=af)
resp = c.get('/archives/export/?annee=2024-2025&categorie=all')
print('Status', resp.status_code, 'Content-Type:', resp.get('Content-Type'), 'Length:', len(resp.content))
open('test_archives_internal.zip', 'wb').write(resp.content)
print('Wrote test_archives_internal.zip')
if resp.status_code in (301,302) and 'Location' in resp:
    print('Redirect to', resp['Location'])

# Retry using force_login if standard login failed
if not logged:
    try:
        user = User.objects.filter(is_superuser=True).first()
        if user:
            c.force_login(user)
            resp2 = c.get('/archives/export/?annee=2024-2025&categorie=all')
            print('After force_login Status', resp2.status_code, 'Length', len(resp2.content))
            open('test_archives_internal_force.zip', 'wb').write(resp2.content)
            print('Wrote test_archives_internal_force.zip')
            if resp2.status_code in (301,302) and 'Location' in resp2:
                print('Redirect to', resp2['Location'])
    except Exception as e:
        print('Force login failed:', e)

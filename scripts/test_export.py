from django.test.client import Client
from django.contrib.auth.models import User
from django.core.management import call_command

c = Client()
# create a superuser if none exists
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('devadmin', 'dev@example.com', 'devpass')

logged = c.login(username='devadmin', password='devpass')
print('Logged in:', logged)
resp = c.get('/archives/export/?annee=2024-2025&categorie=all')
print('Status', resp.status_code, 'Content-Type:', resp['Content-Type'] if 'Content-Type' in resp else 'n/a', 'Length:', len(resp.content))
open('test_archives_internal.zip', 'wb').write(resp.content)
print('Wrote test_archives_internal.zip')

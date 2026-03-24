import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plateforme.settings')
django.setup()

from core.models import FichierAtelier
import cloudinary.api

f = FichierAtelier.objects.first()
if not f:
    print('No FichierAtelier found')
    raise SystemExit(0)
name = getattr(f.fichier, 'name', None)
url = getattr(f.fichier, 'url', None)
print('PK:', f.pk)
print('name:', name)
print('url:', url)
if name:
    pub = name.split('/')[-1]
    print('public_id candidate:', pub)
    for rt in ('image','raw'):
        try:
            res = cloudinary.api.resource(pub, resource_type=rt)
            print('resource_type', rt, 'found, bytesize=', res.get('bytes'))
        except Exception as e:
            print('resource_type', rt, 'error:', e)

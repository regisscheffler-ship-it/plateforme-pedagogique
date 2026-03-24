import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','plateforme.settings')
import django
django.setup()
from core.models import FichierAtelier

qs = FichierAtelier.objects.all().order_by('pk')
print('COUNT', qs.count())
for f in qs:
    name = getattr(f.fichier, 'name', None)
    url = getattr(f.fichier, 'url', None)
    print(f.pk, '\t', f.nom, '\t', name, '\t', url)

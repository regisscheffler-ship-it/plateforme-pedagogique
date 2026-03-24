import csv
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
from django.db.models import FileField, ImageField
from pathlib import Path
import os


def is_cloudinary_url(url):
    if not url:
        return False
    url = url.lower()
    return 'res.cloudinary.com' in url or 'cloudinary' in url


class Command(BaseCommand):
    help = 'Inspecte tous les FileField/ImageField de l\'app core et rapporte où sont stockés les fichiers (Cloudinary/local/missing).'

    def add_arguments(self, parser):
        parser.add_argument('--output', help='Chemin CSV de sortie', default='')
        parser.add_argument('--limit', type=int, default=0, help='Limiter le nombre d\'objets inspectés par champ (0 = pas de limite)')

    def handle(self, *args, **options):
        output = options['output']
        limit = options['limit']

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root:
            media_root = Path(media_root)

        app_config = apps.get_app_config('core')
        models = list(app_config.get_models())

        rows = []
        summary = {}

        for model in models:
            model_name = model.__name__
            file_fields = [f for f in model._meta.get_fields() if getattr(f, 'get_internal_type', lambda: '')() in ('FileField', 'ImageField')]
            if not file_fields:
                continue
            for field in file_fields:
                key = f"{model_name}.{field.name}"
                summary.setdefault(key, {'total': 0, 'cloudinary': 0, 'local': 0, 'missing_local': 0, 'no_reference': 0})

                qs = model.objects.all().order_by('pk')
                if limit and limit > 0:
                    qs = qs[:limit]

                for obj in qs:
                    summary[key]['total'] += 1
                    file_field = getattr(obj, field.name)
                    name = getattr(file_field, 'name', None)
                    url = None
                    is_cloud = False
                    local_exists = False

                    if name:
                        try:
                            url = file_field.url
                        except Exception:
                            url = None

                        if url and is_cloudinary_url(url):
                            is_cloud = True
                            summary[key]['cloudinary'] += 1
                        else:
                            # check local path
                            if media_root and name:
                                local_path = media_root / name
                                if local_path.exists():
                                    local_exists = True
                                    summary[key]['local'] += 1
                                else:
                                    summary[key]['missing_local'] += 1
                            else:
                                summary[key]['missing_local'] += 1
                    else:
                        summary[key]['no_reference'] += 1

                    rows.append({
                        'model': model_name,
                        'pk': getattr(obj, 'pk', ''),
                        'field': field.name,
                        'name': name or '',
                        'url': url or '',
                        'is_cloudinary': is_cloud,
                        'local_exists': local_exists,
                    })

        # Print summary
        self.stdout.write('\n=== Résumé par champ ===')
        for k, v in summary.items():
            self.stdout.write(f"{k}: total={v['total']}, cloudinary={v['cloudinary']}, local={v['local']}, missing_local={v['missing_local']}, no_reference={v['no_reference']}")

        if output:
            try:
                with open(output, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=['model', 'pk', 'field', 'name', 'url', 'is_cloudinary', 'local_exists'])
                    writer.writeheader()
                    for r in rows:
                        writer.writerow(r)
                self.stdout.write(self.style.SUCCESS(f'CSV écrit dans {output}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Echec écriture CSV: {e}'))
        else:
            # print first 50 rows as sample
            self.stdout.write('\n=== Sample (jusqu\'à 50 lignes) ===')
            for r in rows[:50]:
                self.stdout.write(f"{r['model']}[{r['pk']}].{r['field']} -> name='{r['name']}' url='{r['url']}' cloud={r['is_cloudinary']} local_exists={r['local_exists']}")

        self.stdout.write(self.style.SUCCESS('Terminé'))

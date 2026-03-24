from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File as DjangoFile
from pathlib import Path
import os

from core.models import FichierAtelier


class Command(BaseCommand):
    help = 'Re-upload local media files for ateliers to Cloudinary by re-saving FileField.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not perform uploads, only report')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of processed objects')
        parser.add_argument('--models', type=str, default='FichierAtelier', help='Comma-separated model names to process')

    def handle(self, *args, **options):
        dry = options['dry_run']
        limit = options['limit']
        model_names = [m.strip() for m in options['models'].split(',') if m.strip()]

        self.stdout.write(f"Dry run: {dry}, models: {model_names}, limit: {limit}")

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root is None:
            self.stdout.write(self.style.ERROR('MEDIA_ROOT is not set. Aborting.'))
            return
        media_root = Path(media_root)

        for model_name in model_names:
            if model_name == 'FichierAtelier':
                qs = FichierAtelier.objects.all().order_by('id')
            else:
                self.stdout.write(self.style.WARNING(f'Unknown model {model_name}, skipping'))
                continue

            if limit and limit > 0:
                qs = qs[:limit]

            total = qs.count()
            self.stdout.write(f'Processing {total} objects for {model_name}...')

            for obj in qs:
                field = getattr(obj, 'fichier', None)
                if not field:
                    continue
                name = field.name
                if not name:
                    self.stdout.write(f'#{obj.pk}: no filename recorded, skipping')
                    continue

                local_path = media_root / name
                if not local_path.exists():
                    self.stdout.write(self.style.WARNING(f'#{obj.pk}: local file not found: {local_path}'))
                    continue

                self.stdout.write(f'#{obj.pk}: will upload {local_path} -> field {name}')
                if dry:
                    continue

                try:
                    with open(local_path, 'rb') as f:
                        django_file = DjangoFile(f)
                        # save() will use DEFAULT_FILE_STORAGE (Cloudinary if configured)
                        field.save(os.path.basename(name), django_file, save=True)
                    self.stdout.write(self.style.SUCCESS(f'#{obj.pk}: uploaded'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'#{obj.pk}: upload failed: {e}'))

        self.stdout.write(self.style.SUCCESS('Done'))

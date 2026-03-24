from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File as DjangoFile
from pathlib import Path
from django.apps import apps
import os


class Command(BaseCommand):
    help = 'Re-upload local media files to configured storage (Cloudinary) by re-saving FileField/ImageField.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not perform uploads, only report')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of processed objects')
        parser.add_argument('--models', type=str, default='', help='Comma-separated model names to process (app.Model or Model for core app)')

    def handle(self, *args, **options):
        dry = options['dry_run']
        limit = options['limit']
        model_names = [m.strip() for m in options['models'].split(',') if m.strip()]

        self.stdout.write(f"Dry run: {dry}, models: {model_names or 'ALL detected models'}, limit: {limit}")

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root is None:
            self.stdout.write(self.style.ERROR('MEDIA_ROOT is not set. Aborting.'))
            return
        media_root = Path(media_root)

        # Determine target models
        if model_names:
            targets = []
            for mn in model_names:
                if '.' in mn:
                    app_label, model_label = mn.split('.', 1)
                    try:
                        model = apps.get_model(app_label, model_label)
                        targets.append(model)
                    except LookupError:
                        self.stdout.write(self.style.WARNING(f'Unknown model {mn}, skipping'))
                else:
                    try:
                        model = apps.get_model('core', mn)
                        targets.append(model)
                    except LookupError:
                        self.stdout.write(self.style.WARNING(f'Unknown model core.{mn}, skipping'))
        else:
            # scan core app for models that contain FileField/ImageField
            app_config = apps.get_app_config('core')
            models = list(app_config.get_models())
            targets = []
            for model in models:
                file_fields = [f for f in model._meta.get_fields() if getattr(f, 'get_internal_type', lambda: '')() in ('FileField', 'ImageField')]
                if file_fields:
                    targets.append(model)

        if not targets:
            self.stdout.write(self.style.WARNING('No target models found. Nothing to do.'))
            return

        for model in targets:
            model_name = f"{model._meta.app_label}.{model.__name__}"
            file_fields = [f for f in model._meta.get_fields() if getattr(f, 'get_internal_type', lambda: '')() in ('FileField', 'ImageField')]
            if not file_fields:
                self.stdout.write(self.style.WARNING(f'{model_name}: no File/Image fields found, skipping'))
                continue

            qs = model.objects.all().order_by('pk')
            if limit and limit > 0:
                qs = qs[:limit]

            total = qs.count()
            self.stdout.write(f'Processing {total} objects for {model_name} ({len(file_fields)} file fields)')

            for obj in qs:
                for field in file_fields:
                    field_name = field.name
                    file_field = getattr(obj, field_name)
                    name = getattr(file_field, 'name', None)
                    if not name:
                        continue

                    local_path = media_root / name
                    if not local_path.exists():
                        self.stdout.write(self.style.WARNING(f'#{obj.pk} {model.__name__}.{field_name}: local file not found: {local_path}'))
                        continue

                    self.stdout.write(f'#{obj.pk} {model.__name__}.{field_name}: will upload {local_path} -> field {name}')
                    if dry:
                        continue

                    try:
                        with open(local_path, 'rb') as f:
                            django_file = DjangoFile(f)
                            # Save using same basename to storage backend
                            file_field.save(os.path.basename(name), django_file, save=True)
                        self.stdout.write(self.style.SUCCESS(f'#{obj.pk} {model.__name__}.{field_name}: uploaded'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'#{obj.pk} {model.__name__}.{field_name}: upload failed: {e}'))

        self.stdout.write(self.style.SUCCESS('Done'))

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = "Crée un superuser automatiquement depuis les variables d'environnement"

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@admin.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not password:
            self.stdout.write('DJANGO_SUPERUSER_PASSWORD non défini, abandon.')
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Superuser {username} existe déjà.')
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        self.stdout.write(f'Superuser {username} créé avec succès.')

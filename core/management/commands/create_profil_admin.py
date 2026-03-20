from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import ProfilUtilisateur

class Command(BaseCommand):
    help = 'Crée un ProfilUtilisateur professeur pour admin'

    def handle(self, *args, **kwargs):
        try:
            user = User.objects.get(username='admin')
            profil, created = ProfilUtilisateur.objects.get_or_create(
                user=user,
                defaults={
                    'type_utilisateur': 'professeur',
                    'compte_approuve': True,
                }
            )
            if created:
                self.stdout.write('✅ ProfilUtilisateur créé pour admin')
            else:
                self.stdout.write('ℹ️ ProfilUtilisateur existait déjà')
                profil.type_utilisateur = 'professeur'
                profil.compte_approuve = True
                profil.save()
                self.stdout.write('✅ ProfilUtilisateur mis à jour')
        except User.DoesNotExist:
            self.stdout.write('❌ User admin introuvable')

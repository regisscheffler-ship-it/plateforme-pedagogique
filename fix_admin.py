from django.contrib.auth.models import User
from core.models import ProfilUtilisateur
user = User.objects.get(username='admin')
profil, created = ProfilUtilisateur.objects.get_or_create(
    user=user,
    defaults={'type_utilisateur': 'professeur', 'compte_approuve': True}
)
profil.type_utilisateur = 'professeur'
profil.compte_approuve = True
profil.save()
print('OK - Type:', profil.type_utilisateur)

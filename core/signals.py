from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def enregistrer_connexion(sender, request, user, **kwargs):
    """Enregistre une entrée ConnexionEleve à chaque login d'un élève approuvé."""
    try:
        from core.models import ConnexionEleve, ProfilUtilisateur
        profil = ProfilUtilisateur.objects.filter(
            user=user, type_utilisateur='eleve', compte_approuve=True
        ).first()
        if profil:
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR')
            ) or None
            ConnexionEleve.objects.create(user=user, adresse_ip=ip)
    except Exception:
        pass

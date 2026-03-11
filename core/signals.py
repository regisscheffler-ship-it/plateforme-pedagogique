from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import ProfilUtilisateur


@receiver(post_save, sender=ProfilUtilisateur)
@receiver(post_delete, sender=ProfilUtilisateur)
def clear_stats_cache_on_profile_change(sender, instance, **kwargs):
    """Invalidate statistics cache when a profil utilisateur changes.

    Strategy: try to delete a couple of well-known keys, fallback to a full
    cache.clear() if deletion fails. This keeps the change minimal and safe.
    """
    try:
        cache.delete('stats_overview')
        cache.delete('stats_bacpro')
    except Exception:
        try:
            cache.clear()
        except Exception:
            pass
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

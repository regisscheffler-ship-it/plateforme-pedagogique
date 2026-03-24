from django.shortcuts import redirect, get_object_or_404
from django.http import Http404
from django.conf import settings

from .models import FichierAtelier


def download_fichier_atelier_signed(request, pk):
    """Redirige vers une URL Cloudinary signée pour le fichier d'atelier.

    Si Cloudinary n'est pas activé, redirige vers l'URL fournie par le storage.
    La génération d'URL signée est faite à la demande pour éviter d'exposer
    des URLs publiques si les ressources sont restreintes côté Cloudinary.
    """
    fa = get_object_or_404(FichierAtelier, pk=pk)
    if not fa.fichier:
        raise Http404("Fichier introuvable")

    # Si Cloudinary est activé, génère une URL signée (resource_type 'raw' pour les PDF)
    if getattr(settings, 'USE_CLOUDINARY', False):
        try:
            from cloudinary.utils import cloudinary_url
            public_id = fa.fichier.name
            url, _ = cloudinary_url(public_id, resource_type='raw', sign_url=True)
            return redirect(url)
        except Exception:
            # En cas d'erreur, fallback sur l'URL fournie par le champ FileField
            pass

    # Fallback : rediriger vers l'URL du storage (peut être locale)
    return redirect(fa.fichier.url)
